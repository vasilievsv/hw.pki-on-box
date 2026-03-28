# api/rest_api.py
from flask import Flask, jsonify, request
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption
from cryptography import x509

from services.ca_service import CertificateAuthorityService
from services.certificate_service import CertificateService
from services.crl_service import CRLService
from services.ocsp_service import OCSPResponder
from storage.database import PKIDatabase


def _cert_pem(cert: x509.Certificate) -> str:
    return cert.public_bytes(Encoding.PEM).decode()


def _key_pem(key) -> str:
    return key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()).decode()


class PKIRestAPI:
    def __init__(
        self,
        ca_service: CertificateAuthorityService,
        cert_service: CertificateService,
        crl_service: CRLService,
        ocsp_service: OCSPResponder,
        db: PKIDatabase,
    ):
        self.app = Flask(__name__)
        self.ca_svc = ca_service
        self.cert_svc = cert_service
        self.crl_svc = crl_service
        self.ocsp_svc = ocsp_service
        self.db = db
        self._setup_routes()

    def _setup_routes(self):
        app = self.app

        # --- CA ---

        @app.route("/api/v1/ca/root", methods=["POST"])
        def create_root_ca():
            data = request.get_json() or {}
            try:
                cert = self.ca_svc.create_root_ca(
                    data["name"], data.get("validity_years", 20)
                )
                ca_id = self.ca_svc._ca_id(data["name"])
                return jsonify({"ca_id": ca_id, "cert_pem": _cert_pem(cert)}), 201
            except KeyError as e:
                return jsonify({"error": f"missing field: {e}"}), 400
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @app.route("/api/v1/ca/intermediate", methods=["POST"])
        def create_intermediate_ca():
            data = request.get_json() or {}
            try:
                cert = self.ca_svc.create_intermediate_ca(
                    data["name"], data["parent_ca_id"], data.get("validity_years", 10)
                )
                ca_id = self.ca_svc._ca_id(data["name"])
                return jsonify({"ca_id": ca_id, "cert_pem": _cert_pem(cert)}), 201
            except KeyError as e:
                return jsonify({"error": f"missing field: {e}"}), 400
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @app.route("/api/v1/ca", methods=["GET"])
        def list_ca():
            return jsonify(self.db.list_ca_certs())

        @app.route("/api/v1/ca/<ca_id>/cert", methods=["GET"])
        def get_ca_cert(ca_id):
            try:
                cert = self.ca_svc.get_ca_cert(ca_id)
                return jsonify({"ca_id": ca_id, "cert_pem": _cert_pem(cert)})
            except KeyError:
                return jsonify({"error": "CA not found"}), 404
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        # --- Certificates ---

        @app.route("/api/v1/certs/server", methods=["POST"])
        def issue_server():
            data = request.get_json() or {}
            try:
                key, cert = self.cert_svc.issue_server_certificate(
                    data["common_name"], data.get("san_dns", []), data["ca_id"]
                )
                return jsonify({
                    "serial": format(cert.serial_number, "x"),
                    "cert_pem": _cert_pem(cert),
                    "key_pem": _key_pem(key),
                }), 201
            except KeyError as e:
                return jsonify({"error": f"missing field: {e}"}), 400
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @app.route("/api/v1/certs/client", methods=["POST"])
        def issue_client():
            data = request.get_json() or {}
            try:
                key, cert = self.cert_svc.issue_client_certificate(
                    data["user_id"], data["ca_id"]
                )
                return jsonify({
                    "serial": format(cert.serial_number, "x"),
                    "cert_pem": _cert_pem(cert),
                    "key_pem": _key_pem(key),
                }), 201
            except KeyError as e:
                return jsonify({"error": f"missing field: {e}"}), 400
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @app.route("/api/v1/certs/firmware", methods=["POST"])
        def issue_firmware():
            data = request.get_json() or {}
            try:
                key, cert = self.cert_svc.issue_firmware_certificate(
                    data["device_id"], data["ca_id"]
                )
                return jsonify({
                    "serial": format(cert.serial_number, "x"),
                    "cert_pem": _cert_pem(cert),
                    "key_pem": _key_pem(key),
                }), 201
            except KeyError as e:
                return jsonify({"error": f"missing field: {e}"}), 400
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @app.route("/api/v1/certs", methods=["GET"])
        def list_certs():
            with self.db._connect() as conn:
                rows = conn.execute(
                    "SELECT serial, common_name, ca_id, issued_at, status FROM certificates"
                ).fetchall()
            return jsonify([dict(r) for r in rows])

        # --- CRL / OCSP ---

        @app.route("/api/v1/crl/revoke", methods=["POST"])
        def revoke():
            data = request.get_json() or {}
            try:
                serial_hex = data["serial"]
                serial_int = int(serial_hex, 16)
                reason_name = data.get("reason", "unspecified")
                reason = x509.ReasonFlags[reason_name]
                self.crl_svc.revoke_certificate(serial_int, reason)
                return jsonify({"status": "revoked", "serial": serial_hex})
            except KeyError as e:
                return jsonify({"error": f"missing or invalid field: {e}"}), 400
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @app.route("/api/v1/crl/<ca_id>", methods=["GET"])
        def get_crl(ca_id):
            try:
                crl = self.crl_svc.generate_crl(ca_id)
                pem = crl.public_bytes(Encoding.PEM).decode()
                return app.response_class(pem, mimetype="application/x-pem-file")
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @app.route("/api/v1/ocsp/<serial>", methods=["GET"])
        def ocsp_status(serial):
            try:
                serial_int = int(serial, 16)
                status = self.ocsp_svc.check_certificate_status(serial_int)
                return jsonify({"serial": serial, "status": status.value})
            except Exception as e:
                return jsonify({"error": str(e)}), 500
