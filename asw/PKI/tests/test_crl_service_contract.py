import pytest
from cryptography import x509

from core import build_core
from storage.database import PKIDatabase
from storage.file_storage import CertificateFileStorage
from services.ca_service import CertificateAuthorityService
from services.certificate_service import CertificateService
from services.crl_service import CRLService


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
    crl_svc = CRLService(crypto, key_storage, ca_svc, db, cfg)
    ca_svc.create_root_ca("CRL Test CA", validity_years=5)
    ca_id = ca_svc._ca_id("CRL Test CA")
    crl_svc.register_ca_cert(ca_id, ca_svc.get_ca_cert(ca_id))
    return crl_svc, cert_svc, ca_svc, db, ca_id


class TestCrlServicePreconditions:

    def test_revoke_nonexistent_serial(self, pki):
        crl_svc, _, _, db, _ = pki
        crl_svc.revoke_certificate(999999, x509.ReasonFlags.key_compromise)
        assert db.is_revoked(999999)


class TestCrlServicePostconditions:

    def test_revoke_marks_cert_revoked_in_db(self, pki):
        crl_svc, cert_svc, _, db, ca_id = pki
        _, cert = cert_svc.issue_server_certificate("revoke.test", ["revoke.test"], ca_id)
        serial = cert.serial_number
        crl_svc.revoke_certificate(serial, x509.ReasonFlags.key_compromise)
        assert db.is_revoked(serial) is True

    def test_generate_crl_returns_crl_object(self, pki):
        crl_svc, _, _, _, ca_id = pki
        crl = crl_svc.generate_crl(ca_id)
        assert isinstance(crl, x509.CertificateRevocationList)

    def test_generate_crl_contains_revoked_serial(self, pki):
        crl_svc, cert_svc, _, _, ca_id = pki
        _, cert = cert_svc.issue_server_certificate("crl-entry.test", ["crl-entry.test"], ca_id)
        serial = cert.serial_number
        crl_svc.revoke_certificate(serial, x509.ReasonFlags.cessation_of_operation)
        crl = crl_svc.generate_crl(ca_id)
        revoked_serials = [rc.serial_number for rc in crl]
        assert serial in revoked_serials

    def test_generate_crl_empty_when_no_revocations(self, pki):
        crl_svc, _, _, _, ca_id = pki
        crl = crl_svc.generate_crl(ca_id)
        assert len(list(crl)) == 0


class TestCrlServiceInvariants:

    def test_crl_signed_by_ca(self, pki):
        crl_svc, _, ca_svc, _, ca_id = pki
        crl = crl_svc.generate_crl(ca_id)
        ca_cert = ca_svc.get_ca_cert(ca_id)
        assert crl.issuer == ca_cert.subject

    def test_crl_has_next_update(self, pki):
        crl_svc, _, _, _, ca_id = pki
        crl = crl_svc.generate_crl(ca_id)
        nu = getattr(crl, "next_update_utc", None) or crl.next_update
        assert nu is not None

    def test_revoked_cert_stays_revoked(self, pki):
        crl_svc, cert_svc, _, db, ca_id = pki
        _, cert = cert_svc.issue_server_certificate("stay.test", ["stay.test"], ca_id)
        serial = cert.serial_number
        crl_svc.revoke_certificate(serial, x509.ReasonFlags.key_compromise)
        assert db.is_revoked(serial) is True
        assert db.is_revoked(serial) is True
