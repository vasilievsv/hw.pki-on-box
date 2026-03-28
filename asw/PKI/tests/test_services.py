import pytest
from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import ec


def test_create_root_ca(root_ca):
    cert, ca_id = root_ca
    cn = cert.subject.get_attributes_for_oid(x509.oid.NameOID.COMMON_NAME)[0].value
    assert cn == "Test Root CA"
    bc = cert.extensions.get_extension_for_class(x509.BasicConstraints)
    assert bc.value.ca is True


def test_create_intermediate_ca(services, root_ca):
    _, db, ca_svc, *_ = services
    _, root_ca_id = root_ca
    cert = ca_svc.create_intermediate_ca("Test Intermediate CA", root_ca_id, validity_years=1)
    root_cert = ca_svc.get_ca_cert(root_ca_id)
    assert cert.issuer == root_cert.subject


def test_issue_server_cert(services, root_ca):
    _, db, ca_svc, crl_svc, cert_svc, _ = services
    _, ca_id = root_ca
    key, cert = cert_svc.issue_server_certificate(
        "test.example.com", ["test.example.com", "www.test.example.com"], ca_id
    )
    eku = cert.extensions.get_extension_for_class(x509.ExtendedKeyUsage)
    assert x509.oid.ExtendedKeyUsageOID.SERVER_AUTH in eku.value
    san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
    assert "test.example.com" in san.value.get_values_for_type(x509.DNSName)


def test_issue_client_cert(services, root_ca):
    _, db, ca_svc, crl_svc, cert_svc, _ = services
    _, ca_id = root_ca
    key, cert = cert_svc.issue_client_certificate("user-001", ca_id)
    assert isinstance(key, ec.EllipticCurvePrivateKey)
    eku = cert.extensions.get_extension_for_class(x509.ExtendedKeyUsage)
    assert x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH in eku.value


def test_issue_firmware_cert(services, root_ca):
    _, db, ca_svc, crl_svc, cert_svc, _ = services
    _, ca_id = root_ca
    key, cert = cert_svc.issue_firmware_certificate("device-001", ca_id)
    eku = cert.extensions.get_extension_for_class(x509.ExtendedKeyUsage)
    assert x509.oid.ExtendedKeyUsageOID.CODE_SIGNING in eku.value


def test_revoke_and_crl(services, root_ca):
    _, db, ca_svc, crl_svc, cert_svc, _ = services
    _, ca_id = root_ca
    _, cert = cert_svc.issue_server_certificate(
        "revoke.example.com", ["revoke.example.com"], ca_id
    )
    serial = cert.serial_number
    crl_svc.register_ca_cert(ca_id, ca_svc.get_ca_cert(ca_id))
    crl_svc.revoke_certificate(serial, x509.ReasonFlags.key_compromise)
    assert crl_svc.is_revoked(serial)
    crl = crl_svc.generate_crl(ca_id)
    serials_in_crl = [r.serial_number for r in crl]
    assert serial in serials_in_crl


def test_ocsp_good(services, root_ca):
    _, db, ca_svc, crl_svc, cert_svc, ocsp_svc = services
    _, ca_id = root_ca
    _, cert = cert_svc.issue_server_certificate(
        "ocsp-good.example.com", ["ocsp-good.example.com"], ca_id
    )
    from services.ocsp_service import OCSPStatus
    status = ocsp_svc.check_certificate_status(cert.serial_number)
    assert status == OCSPStatus.GOOD


def test_ocsp_revoked(services, root_ca):
    _, db, ca_svc, crl_svc, cert_svc, ocsp_svc = services
    _, ca_id = root_ca
    _, cert = cert_svc.issue_server_certificate(
        "ocsp-revoked.example.com", ["ocsp-revoked.example.com"], ca_id
    )
    crl_svc.revoke_certificate(cert.serial_number, x509.ReasonFlags.unspecified)
    from services.ocsp_service import OCSPStatus
    status = ocsp_svc.check_certificate_status(cert.serial_number)
    assert status == OCSPStatus.REVOKED


def test_db_persistence(cfg):
    from storage.database import PKIDatabase
    from core import build_core
    from services.ca_service import CertificateAuthorityService
    _, _, crypto, key_storage = build_core(cfg)
    db = PKIDatabase(cfg["storage"]["db_path"])
    ca_svc = CertificateAuthorityService(crypto, key_storage, db, cfg)
    cert = ca_svc.create_root_ca("Persist CA", validity_years=1)
    ca_id = ca_svc._ca_id("Persist CA")
    db2 = PKIDatabase(cfg["storage"]["db_path"])
    loaded = db2.load_ca_cert(ca_id)
    assert loaded is not None
    assert loaded.serial_number == cert.serial_number


def test_file_storage(services, root_ca):
    _, db, ca_svc, crl_svc, cert_svc, _ = services
    _, ca_id = root_ca
    _, cert = cert_svc.issue_server_certificate("fs.example.com", ["fs.example.com"], ca_id)
    loaded = cert_svc._file_storage.load_cert(cert.serial_number)
    assert loaded is not None
    assert loaded.serial_number == cert.serial_number
    by_label = cert_svc._file_storage.load_cert_by_label("fs.example.com")
    assert by_label is not None
