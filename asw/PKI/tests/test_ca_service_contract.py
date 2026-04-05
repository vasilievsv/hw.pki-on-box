import pytest
from cryptography import x509
from cryptography.x509.oid import NameOID

from core import build_core
from storage.database import PKIDatabase
from services.ca_service import CertificateAuthorityService


@pytest.fixture
def pki(tmp_path):
    cfg = {
        "trng": {"mode": "software"},
        "drbg": {"algorithm": "hmac-sha256", "reseed_interval": 1000, "personalization": ""},
        "crypto": {"rsa_key_size": 4096, "ec_curve": "P-384", "aes_key_size": 256},
        "storage": {
            "path": str(tmp_path / "keys"),
            "db_path": str(tmp_path / "pki.db"),
            "ca_key_password": "test-pw",
        },
    }
    trng, drbg, crypto, key_storage = build_core(cfg)
    db = PKIDatabase(cfg["storage"]["db_path"])
    ca_svc = CertificateAuthorityService(crypto, key_storage, db, cfg)
    return ca_svc, db, key_storage


class TestCAServicePreconditions:

    def test_rejects_intermediate_without_parent(self, pki):
        ca_svc, _, _ = pki
        with pytest.raises(KeyError):
            ca_svc.create_intermediate_ca("Sub CA", parent_ca_id="nonexistent")

    def test_rejects_load_key_wrong_ca(self, pki):
        ca_svc, _, storage = pki
        with pytest.raises(FileNotFoundError):
            storage.load_key("ghost_ca", "test-pw")


class TestCAServicePostconditions:

    def test_create_root_ca_returns_certificate(self, pki):
        ca_svc, _, _ = pki
        cert = ca_svc.create_root_ca("Test Root CA", validity_years=1)
        assert isinstance(cert, x509.Certificate)
        cn = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
        assert cn == "Test Root CA"

    def test_root_ca_is_self_signed(self, pki):
        ca_svc, _, _ = pki
        cert = ca_svc.create_root_ca("Self Sign Root", validity_years=1)
        assert cert.issuer == cert.subject

    def test_root_ca_key_stored(self, pki):
        ca_svc, _, storage = pki
        ca_svc.create_root_ca("Stored Root", validity_years=1)
        ca_id = ca_svc._ca_id("Stored Root")
        key = storage.load_key(ca_id, "test-pw")
        assert key is not None

    def test_root_ca_saved_to_db(self, pki):
        ca_svc, db, _ = pki
        ca_svc.create_root_ca("DB Root", validity_years=1)
        rows = db.list_ca_certs()
        assert any(r["name"] == "DB Root" for r in rows)

    def test_create_intermediate_signed_by_parent(self, pki):
        ca_svc, _, _ = pki
        ca_svc.create_root_ca("Parent CA", validity_years=5)
        parent_id = ca_svc._ca_id("Parent CA")
        inter = ca_svc.create_intermediate_ca("Child CA", parent_id, validity_years=2)
        parent_cert = ca_svc.get_ca_cert(parent_id)
        assert inter.issuer == parent_cert.subject

    def test_get_ca_cert_returns_cert(self, pki):
        ca_svc, _, _ = pki
        ca_svc.create_root_ca("Get Test", validity_years=1)
        cert = ca_svc.get_ca_cert(ca_svc._ca_id("Get Test"))
        assert isinstance(cert, x509.Certificate)


class TestCAServiceInvariants:

    def test_root_ca_has_basic_constraints_ca_true(self, pki):
        ca_svc, _, _ = pki
        cert = ca_svc.create_root_ca("BC Root", validity_years=1)
        bc = cert.extensions.get_extension_for_class(x509.BasicConstraints)
        assert bc.value.ca is True

    def test_root_ca_has_key_usage_cert_sign(self, pki):
        ca_svc, _, _ = pki
        cert = ca_svc.create_root_ca("KU Root", validity_years=1)
        ku = cert.extensions.get_extension_for_class(x509.KeyUsage)
        assert ku.value.key_cert_sign is True
        assert ku.value.crl_sign is True

    def test_intermediate_path_length_zero(self, pki):
        ca_svc, _, _ = pki
        ca_svc.create_root_ca("Path Root", validity_years=5)
        parent_id = ca_svc._ca_id("Path Root")
        inter = ca_svc.create_intermediate_ca("Path Inter", parent_id, validity_years=2)
        bc = inter.extensions.get_extension_for_class(x509.BasicConstraints)
        assert bc.value.path_length == 0
