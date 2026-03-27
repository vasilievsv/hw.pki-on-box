class CertificateAuthorityService:
    """Сервис управления корневым и промежуточными ЦС"""
    def __init__(self, crypto_engine: CryptoEngine, key_storage: KeyStorage):
        self.crypto = crypto_engine
        self.storage = key_storage
        self.cas = {}
        
    def create_root_ca(self, name: str, validity_years: int = 10):
        # Создание корневого ЦС
        private_key = self.crypto.generate_rsa_keypair(4096)
        ca_cert = self._build_ca_certificate(name, private_key, validity_years)
        
        ca_id = f"root_ca_{name}"
        self.storage.store_private_key(ca_id, private_key)
        self.cas[ca_id] = ca_cert
        
        return ca_cert
        
    def create_intermediate_ca(self, parent_ca_id: str, name: str):
        # Создание промежуточного ЦС
        pass