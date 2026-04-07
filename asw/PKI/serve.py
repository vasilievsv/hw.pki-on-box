#!/usr/bin/env python
import os
import sys
from core import build_core, load_config
from storage.database import PKIDatabase
from storage.file_storage import CertificateFileStorage
from services.ca_service import CertificateAuthorityService
from services.certificate_service import CertificateService
from services.crl_service import CRLService
from services.ocsp_service import OCSPResponder
from api.rest_api import PKIRestAPI


def build_services(cfg: dict):
    trng, drbg, crypto, key_storage = build_core(cfg)
    storage_cfg = cfg.get("storage", {})
    base_path = storage_cfg.get("base_path", storage_cfg.get("path", "asw/PKI/storage"))
    db_name = storage_cfg.get("db_name", "pki.db")
    db_path = storage_cfg.get("db_path", os.path.join(base_path, db_name))
    certs_dir = storage_cfg.get("certs_path", os.path.join(base_path, storage_cfg.get("certs_dir", "certs")))
    db = PKIDatabase(db_path)
    file_storage = CertificateFileStorage(certs_dir)
    ca_svc = CertificateAuthorityService(crypto, key_storage, db, cfg)
    crl_svc = CRLService(crypto, key_storage, ca_svc, db, cfg)
    cert_svc = CertificateService(crypto, key_storage, ca_svc, db, file_storage)
    ocsp_svc = OCSPResponder(crl_svc, crypto, cfg)
    return trng, db, ca_svc, crl_svc, cert_svc, ocsp_svc


def create_app(cfg=None):
    cfg = cfg or load_config()
    _, db, ca_svc, crl_svc, cert_svc, ocsp_svc = build_services(cfg)
    api = PKIRestAPI(ca_svc, cert_svc, crl_svc, ocsp_svc, db)
    return api.app


if __name__ == "__main__":
    cfg = load_config()
    trng, db, ca_svc, crl_svc, cert_svc, ocsp_svc = build_services(cfg)

    health_ok = trng.health_check()
    if not health_ok:
        print("TRNG health check failed", file=sys.stderr)
        sys.exit(1)

    api = PKIRestAPI(ca_svc, cert_svc, crl_svc, ocsp_svc, db)
    host = cfg.get("api", {}).get("host", "0.0.0.0")
    port = cfg.get("api", {}).get("port", 5000)
    print(f"🚀 PKI REST API → http://{host}:{port}")
    api.app.run(host=host, port=port)
