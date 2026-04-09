import json
import pytest

from core import build_core
from storage.database import PKIDatabase
from storage.file_storage import CertificateFileStorage
from services.ca_service import CertificateAuthorityService
from services.certificate_service import CertificateService
from services.crl_service import CRLService
from services.ocsp_service import OCSPResponder
from api.rest_api import PKIRestAPI


@pytest.fixture(scope="module")
def flow_cfg(tmp_path_factory):
    base = tmp_path_factory.mktemp("flow")
    return {
        "trng": {"mode": "software"},
        "drbg": {"algorithm": "hmac-sha256", "reseed_interval": 1000, "personalization": ""},
        "crypto": {"rsa_key_size": 2048, "ec_curve": "P-384", "aes_key_size": 256},
        "storage": {
            "path": str(base / "keys"),
            "backend": "file",
            "db_path": str(base / "pki.db"),
            "certs_path": str(base / "certs"),
            "ca_key_password": "test-flow-key",
        },
    }


@pytest.fixture(scope="module")
def flow_services(flow_cfg):
    trng, drbg, crypto, key_storage = build_core(flow_cfg)
    storage_cfg = flow_cfg["storage"]
    db = PKIDatabase(storage_cfg["db_path"])
    file_storage = CertificateFileStorage(storage_cfg["certs_path"])
    ca_svc = CertificateAuthorityService(crypto, key_storage, db, flow_cfg)
    crl_svc = CRLService(crypto, key_storage, ca_svc, db, flow_cfg)
    cert_svc = CertificateService(crypto, key_storage, ca_svc, db, file_storage)
    ocsp_svc = OCSPResponder(crl_svc, crypto, flow_cfg)
    return ca_svc, cert_svc, crl_svc, ocsp_svc, db


@pytest.fixture(scope="module")
def flow_client(flow_cfg, flow_services):
    ca_svc, cert_svc, crl_svc, ocsp_svc, db = flow_services
    api = PKIRestAPI(ca_svc, cert_svc, crl_svc, ocsp_svc, db)
    api.app.config["TESTING"] = True
    with api.app.test_client() as c:
        yield c


@pytest.fixture(scope="module")
def flow_root_ca(flow_services):
    ca_svc, *_ = flow_services
    cert = ca_svc.create_root_ca("Flow-Test-CA", validity_years=1)
    ca_id = ca_svc._ca_id("Flow-Test-CA")
    return cert, ca_id


class TestRequestFlowPreconditions:

    def test_health_endpoint_available(self, flow_client):
        r = flow_client.get("/api/v1/health")
        assert r.status_code == 200
        data = json.loads(r.data)
        assert data["status"] == "ok"

    def test_api_rejects_unknown_endpoint(self, flow_client):
        r = flow_client.get("/api/v1/nonexistent")
        assert r.status_code == 404


class TestRequestFlowPostconditions:

    def test_create_root_ca_via_api(self, flow_client):
        r = flow_client.post("/api/v1/ca/root", json={"name": "API-Root-CA", "validity_years": 1})
        assert r.status_code == 201
        data = json.loads(r.data)
        assert "ca_id" in data
        assert "cert_pem" in data
        assert "BEGIN CERTIFICATE" in data["cert_pem"]

    def test_list_ca_via_api(self, flow_client):
        r = flow_client.get("/api/v1/ca")
        assert r.status_code == 200
        data = json.loads(r.data)
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_issue_server_cert_via_api(self, flow_client, flow_root_ca):
        _, ca_id = flow_root_ca
        r = flow_client.post("/api/v1/certs/server", json={
            "common_name": "test.local",
            "san_dns": ["test.local", "*.test.local"],
            "ca_id": ca_id,
        })
        assert r.status_code == 201
        data = json.loads(r.data)
        assert "serial" in data
        assert "cert_pem" in data
        assert "key_pem" in data

    def test_issue_client_cert_via_api(self, flow_client, flow_root_ca):
        _, ca_id = flow_root_ca
        r = flow_client.post("/api/v1/certs/client", json={
            "user_id": "test-user-001",
            "ca_id": ca_id,
        })
        assert r.status_code == 201
        data = json.loads(r.data)
        assert "serial" in data

    def test_list_certs_via_api(self, flow_client):
        r = flow_client.get("/api/v1/certs")
        assert r.status_code == 200
        data = json.loads(r.data)
        assert isinstance(data, list)
        assert len(data) >= 1


class TestRequestFlowErrorHandling:

    def test_create_ca_missing_name_returns_400(self, flow_client):
        r = flow_client.post("/api/v1/ca/root", json={})
        assert r.status_code == 400
        data = json.loads(r.data)
        assert "error" in data

    def test_issue_cert_missing_fields_returns_400(self, flow_client):
        r = flow_client.post("/api/v1/certs/server", json={"common_name": "x"})
        assert r.status_code in (400, 500)

    def test_get_nonexistent_ca_returns_404(self, flow_client):
        r = flow_client.get("/api/v1/ca/nonexistent-ca-id/cert")
        assert r.status_code in (404, 500)

    def test_error_response_is_json(self, flow_client):
        r = flow_client.post("/api/v1/ca/root", json={})
        assert r.status_code == 400
        data = json.loads(r.data)
        assert "error" in data
        assert "Traceback" not in data["error"]


class TestRequestFlowInvariants:

    def test_response_no_stack_trace(self, flow_client):
        r = flow_client.post("/api/v1/ca/root", json={})
        body = r.data.decode()
        assert "Traceback" not in body
        assert "File \"" not in body

    def test_revoke_and_crl_flow(self, flow_client, flow_root_ca):
        _, ca_id = flow_root_ca
        r = flow_client.post("/api/v1/certs/server", json={
            "common_name": "revoke-test.local",
            "san_dns": ["revoke-test.local"],
            "ca_id": ca_id,
        })
        assert r.status_code == 201
        serial = json.loads(r.data)["serial"]

        r = flow_client.post("/api/v1/crl/revoke", json={
            "serial": serial,
            "reason": "key_compromise",
        })
        assert r.status_code == 200
        data = json.loads(r.data)
        assert data["status"] == "revoked"

        r = flow_client.get(f"/api/v1/crl/{ca_id}")
        assert r.status_code == 200
        assert b"BEGIN X509 CRL" in r.data
