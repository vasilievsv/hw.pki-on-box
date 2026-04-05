import pytest
from cryptography import x509
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID

from core import build_core
from storage.database import PKIDatabase
from storage.file_storage import CertificateFileStorage
from services.ca_service import CertificateAuthorityService
from services.certificate_service import CertificateService


@pytest.fixture
def pki(tmp_path):
    cfg = {
        "trng": {"mode": "software"},
        "drbg": {"algorithm": "hmac-sha256", "reseed_interval": 1000, "personalization": ""},
        "crypto": {"rsa_key_size": 2048, "ec_curve": "P-384", "aes_key_size": 256},
        "storage": {
            "path": str(tmp_path / "keys"),
            "db_path": str(tmp_path / "pki.db"),
            "certs_path": str(tmp_path / "certs"),
            "ca_key_password": "test-pw",
        },
    }
    trng, drbg, crypto, key_storage = build_core(cfg)
    db = PKIDatabase(cfg["storage"]["db_path"])
    file_storage = CertificateFileStorage(cfg["storage"]["certs_path"])
    ca_svc = CertificateAuthorityService(crypto, key_storage, db, cfg)
    cert_svc = CertificateService(crypto, key_storage, ca_svc, db, file_storage)
    ca_svc.create_root_ca("Test CA", validity_years=5)
    ca_id = ca_svc._ca_id("Test CA")
    return cert_svc, ca_svc, db, file_storage, ca_id


class TestCertificateServicePreconditions:

    def test_rejects_nonexistent_ca(self, pki):
        cert_svc, _, _, _, _ = pki
        with pytest.raises(KeyError):
            cert_svc.issue_server_certificate("srv.test", ["srv.test"], ca_id="fake_ca")


class TestCertificateServicePostconditions:

    def test_issue_server_cert_returns_cert(self, pki):
        cert_svc, _, _, _, ca_id = pki
        _, cert = cert_svc.issue_server_certificate("srv.example.com", ["srv.example.com"], ca_id)
        assert isinstance(cert, x509.Certificate)
        cn = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
        assert cn == "srv.example.com"

    def test_server_cert_signed_by_ca(self, pki):
        cert_svc, ca_svc, _, _, ca_id = pki
        _, cert = cert_svc.issue_server_certificate("signed.test", ["signed.test"], ca_id)
        ca_cert = ca_svc.get_ca_cert(ca_id)
        assert cert.issuer == ca_cert.subject

    def test_server_cert_saved_to_db(self, pki):
        cert_svc, _, db, _, ca_id = pki
        _, cert = cert_svc.issue_server_certificate("db.test", ["db.test"], ca_id)
        loaded = db.load_certificate(cert.serial_number)
        assert loaded is not None

    def test_server_cert_saved_to_file(self, pki):
        cert_svc, _, _, fs, ca_id = pki
        _, cert = cert_svc.issue_server_certificate("file.test", ["file.test"], ca_id)
        loaded = fs.load_cert(cert.serial_number)
        assert loaded is not None

    def test_issue_client_cert(self, pki):
        cert_svc, _, _, _, ca_id = pki
        _, cert = cert_svc.issue_client_certificate("user@test", ca_id)
        assert isinstance(cert, x509.Certificate)
        eku = cert.extensions.get_extension_for_class(x509.ExtendedKeyUsage)
        assert ExtendedKeyUsageOID.CLIENT_AUTH in eku.value

    def test_issue_firmware_cert(self, pki):
        cert_svc, _, _, _, ca_id = pki
        _, cert = cert_svc.issue_firmware_certificate("device-001", ca_id)
        assert isinstance(cert, x509.Certificate)
        eku = cert.extensions.get_extension_for_class(x509.ExtendedKeyUsage)
        assert ExtendedKeyUsageOID.CODE_SIGNING in eku.value

    def test_two_certs_different_serials(self, pki):
        cert_svc, _, _, _, ca_id = pki
        _, c1 = cert_svc.issue_server_certificate("a.test", ["a.test"], ca_id)
        _, c2 = cert_svc.issue_server_certificate("b.test", ["b.test"], ca_id)
        assert c1.serial_number != c2.serial_number


class TestCertificateServiceInvariants:

    def test_server_cert_not_ca(self, pki):
        cert_svc, _, _, _, ca_id = pki
        _, cert = cert_svc.issue_server_certificate("leaf.test", ["leaf.test"], ca_id)
        bc = cert.extensions.get_extension_for_class(x509.BasicConstraints)
        assert bc.value.ca is False

    def test_server_cert_has_server_auth_eku(self, pki):
        cert_svc, _, _, _, ca_id = pki
        _, cert = cert_svc.issue_server_certificate("eku.test", ["eku.test"], ca_id)
        eku = cert.extensions.get_extension_for_class(x509.ExtendedKeyUsage)
        assert ExtendedKeyUsageOID.SERVER_AUTH in eku.value
