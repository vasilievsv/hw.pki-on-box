import os
import pytest

from core import build_core
from core.trng import HardwareTRNG, TRNGDeviceError
from core.drbg import NISTDRBG
from storage.database import PKIDatabase
from storage.file_storage import CertificateFileStorage
from services.ca_service import CertificateAuthorityService
from services.certificate_service import CertificateService
from services.crl_service import CRLService
from services.ocsp_service import OCSPResponder
from api.rest_api import PKIRestAPI


def pytest_configure(config):
    config.addinivalue_line("markers", "hardware: requires real STM32 TRNG via USB HID")


@pytest.fixture(scope="session")
def cfg(tmp_path_factory):
    base = tmp_path_factory.mktemp("pki")
    os.environ["PKI_TRNG_MODE"] = "software"
    return {
        "trng": {"mode": "software"},
        "drbg": {"algorithm": "hmac-sha256", "reseed_interval": 1000, "personalization": ""},
        "crypto": {"rsa_key_size": 2048, "ec_curve": "P-384", "aes_key_size": 256},
        "storage": {
            "path": str(base / "keys"),
            "backend": "file",
            "db_path": str(base / "pki.db"),
            "certs_path": str(base / "certs"),
            "ca_key_password": "test-ca-key",
        },
    }


@pytest.fixture(scope="session")
def hw_cfg(tmp_path_factory):
    base = tmp_path_factory.mktemp("pki_hw")
    return {
        "trng": {"mode": "hardware", "hid_vid": "0x0483", "hid_pid": "0x5750"},
        "drbg": {"algorithm": "hmac-sha256", "reseed_interval": 1000, "personalization": ""},
        "crypto": {"rsa_key_size": 2048, "ec_curve": "P-384", "aes_key_size": 256},
        "storage": {
            "path": str(base / "keys"),
            "backend": "file",
            "db_path": str(base / "pki.db"),
            "certs_path": str(base / "certs"),
            "ca_key_password": "test-hw-key",
        },
    }


@pytest.fixture(scope="session")
def hw_trng(hw_cfg):
    return HardwareTRNG(hw_cfg)


@pytest.fixture(scope="session")
def hw_drbg(hw_trng, hw_cfg):
    d = NISTDRBG(hw_trng, hw_cfg)
    d.instantiate()
    return d


@pytest.fixture(scope="session")
def services(cfg):
    trng, drbg, crypto, key_storage = build_core(cfg)
    storage_cfg = cfg["storage"]
    db = PKIDatabase(storage_cfg["db_path"])
    file_storage = CertificateFileStorage(storage_cfg["certs_path"])
    ca_svc = CertificateAuthorityService(crypto, key_storage, db, cfg)
    crl_svc = CRLService(crypto, key_storage, ca_svc, db, cfg)
    cert_svc = CertificateService(crypto, key_storage, ca_svc, db, file_storage)
    ocsp_svc = OCSPResponder(crl_svc, crypto, cfg)
    return trng, db, ca_svc, crl_svc, cert_svc, ocsp_svc


@pytest.fixture(scope="session")
def root_ca(services):
    _, db, ca_svc, *_ = services
    cert = ca_svc.create_root_ca("Test Root CA", validity_years=1)
    return cert, ca_svc._ca_id("Test Root CA")


@pytest.fixture
def client(cfg, services):
    trng, db, ca_svc, crl_svc, cert_svc, ocsp_svc = services
    api = PKIRestAPI(ca_svc, cert_svc, crl_svc, ocsp_svc, db)
    api.app.config["TESTING"] = True
    with api.app.test_client() as c:
        yield c
