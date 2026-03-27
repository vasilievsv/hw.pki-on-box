# api/rest_api.py
from flask import Flask, jsonify, request

class PKIRestAPI:
    """REST API для управления PKI"""
    def __init__(self, ca_service: CertificateAuthorityService, 
                 cert_service: CertificateService):
        self.app = Flask(__name__)
        self.ca_service = ca_service
        self.cert_service = cert_service
        self._setup_routes()
        
    def _setup_routes(self):
        @self.app.route('/api/v1/ca/root', methods=['POST'])
        def create_root_ca():
            data = request.json
            cert = self.ca_service.create_root_ca(
                data['name'], 
                data.get('validity_years', 10)
            )
            return jsonify({'certificate': cert.public_bytes(...)})
            
        @self.app.route('/api/v1/certificates/server', methods=['POST'])
        def issue_server_cert():
            data = request.json
            key, cert = self.cert_service.issue_server_certificate(
                data['common_name'],
                data['san_dns'],
                data['ca_id']
            )
            return jsonify({
                'private_key': key.private_bytes(...),
                'certificate': cert.public_bytes(...)
            })