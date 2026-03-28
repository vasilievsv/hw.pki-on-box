import pytest


@pytest.fixture(scope="module")
def api_client(cfg, services):
    from api.rest_api import PKIRestAPI
    trng, db, ca_svc, crl_svc, cert_svc, ocsp_svc = services
    api = PKIRestAPI(ca_svc, cert_svc, crl_svc, ocsp_svc, db)
    api.app.config["TESTING"] = True
    with api.app.test_client() as c:
        yield c


@pytest.fixture(scope="module")
def root_ca_id(api_client):
    resp = api_client.post("/api/v1/ca/root", json={"name": "API Test Root CA", "validity_years": 1})
    assert resp.status_code == 201
    return resp.get_json()["ca_id"]


def test_create_root_ca(api_client):
    resp = api_client.post("/api/v1/ca/root", json={"name": "API Root 2", "validity_years": 1})
    assert resp.status_code == 201
    data = resp.get_json()
    assert "ca_id" in data
    assert "cert_pem" in data
    assert "BEGIN CERTIFICATE" in data["cert_pem"]


def test_list_ca(api_client, root_ca_id):
    resp = api_client.get("/api/v1/ca")
    assert resp.status_code == 200
    assert len(resp.get_json()) >= 1


def test_issue_server_cert(api_client, root_ca_id):
    resp = api_client.post("/api/v1/certs/server", json={
        "common_name": "api.example.com",
        "san_dns": ["api.example.com"],
        "ca_id": root_ca_id,
    })
    assert resp.status_code == 201
    data = resp.get_json()
    assert "cert_pem" in data and "key_pem" in data
    assert "BEGIN CERTIFICATE" in data["cert_pem"]
    assert "BEGIN" in data["key_pem"]


def test_issue_client_cert(api_client, root_ca_id):
    resp = api_client.post("/api/v1/certs/client", json={"user_id": "api-user-001", "ca_id": root_ca_id})
    assert resp.status_code == 201


def test_revoke_and_ocsp(api_client, root_ca_id):
    resp = api_client.post("/api/v1/certs/server", json={
        "common_name": "revoke-api.example.com",
        "san_dns": ["revoke-api.example.com"],
        "ca_id": root_ca_id,
    })
    assert resp.status_code == 201
    serial = resp.get_json()["serial"]
    resp = api_client.post("/api/v1/crl/revoke", json={"serial": serial, "ca_id": root_ca_id})
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "revoked"
    resp = api_client.get(f"/api/v1/ocsp/{serial}")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "revoked"


def test_get_crl(api_client, root_ca_id):
    resp = api_client.get(f"/api/v1/crl/{root_ca_id}")
    assert resp.status_code == 200
    assert b"BEGIN X509 CRL" in resp.data
