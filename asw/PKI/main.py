import sys

from core import build_core, load_config
from storage.database import PKIDatabase
from storage.file_storage import CertificateFileStorage
from services.ca_service import CertificateAuthorityService
from services.certificate_service import CertificateService
from services.crl_service import CRLService
from services.ocsp_service import OCSPResponder


def build_services(cfg):
    trng, drbg, crypto, key_storage = build_core(cfg)
    storage_cfg = cfg.get("storage", {})
    db = PKIDatabase(storage_cfg.get("db_path", "asw/PKI/storage/pki.db"))
    file_storage = CertificateFileStorage(storage_cfg.get("certs_path", "asw/PKI/storage/certs"))
    ca_svc = CertificateAuthorityService(crypto, key_storage, db, cfg)
    crl_svc = CRLService(crypto, key_storage, ca_svc, db, cfg)
    cert_svc = CertificateService(crypto, key_storage, ca_svc, db, file_storage)
    ocsp_svc = OCSPResponder(crl_svc, crypto, cfg)
    return trng, db, ca_svc, crl_svc, cert_svc, ocsp_svc


def main():
    cfg = load_config()
    trng, drbg, crypto, key_storage = build_core(cfg)

    storage_cfg = cfg.get("storage", {})
    db = PKIDatabase(storage_cfg.get("db_path", "asw/PKI/storage/pki.db"))
    file_storage = CertificateFileStorage(storage_cfg.get("certs_path", "asw/PKI/storage/certs"))

    ca_svc = CertificateAuthorityService(crypto, key_storage, db, cfg)
    crl_svc = CRLService(crypto, key_storage, ca_svc, db, cfg)
    cert_svc = CertificateService(crypto, key_storage, ca_svc, db, file_storage)
    ocsp_svc = OCSPResponder(crl_svc, crypto, cfg)

    print("🚀 PKI-on-Box запущен")
    print(f"   TRNG mode : {cfg['trng']['mode']}")
    print(f"   Storage   : {storage_cfg.get('path', 'asw/PKI/storage')}")

    health = trng.health_check()
    if not health.get("passed", False):
        print(f"❌ TRNG health check failed: {health}", file=sys.stderr)
        sys.exit(1)
    print("   TRNG      : ✅ health check passed")

    keys = key_storage.list_keys()
    print(f"   Keys      : {len(keys)} stored")

    ca_certs = db.list_ca_certs()
    print(f"   CA certs  : {len(ca_certs)} in DB")


if __name__ == "__main__":
    main()
