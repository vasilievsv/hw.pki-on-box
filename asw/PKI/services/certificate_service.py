class CertificateService:
    """Сервис выпуска сертификатов"""
    def __init__(self, crypto_engine: CryptoEngine, ca_service: CertificateAuthorityService):
        self.crypto = crypto_engine
        self.ca_service = ca_service
        
    def issue_server_certificate(self, common_name: str, san_dns: list, ca_id: str):
        # Выпуск серверного сертификата
        server_key = self.crypto.generate_rsa_keypair(2048)
        cert = self._build_server_certificate(common_name, server_key, ca_id)
        return server_key, cert
        
    def issue_client_certificate(self, user_id: str, ca_id: str):
        # Выпуск клиентского сертификата
        pass