# main.py
# src/main.py - обновленная версия
from security.security_manager import SecurityManager, SecurityDomain

class PKIBox:
    def __init__(self, config_path=None):
        self.security = SecurityManager()
        # ... остальная инициализация
    
    def start(self):
        # Инициализация безопасности
        self.security.initialize_security()
        
        # Запуск в правильном домене безопасности
        self.security.switch_security_domain(SecurityDomain.PKI_CORE)
        
        # Остальная логика запуска...
        super().start()


# class EducationalPKI:
#     """Главный класс учебного PKI"""
    
#     def __init__(self, config: dict):
#         self.config = config
        
#         # Инициализация слоев снизу вверх
#         self.trng = HardwareTRNG(config['trng_source'])
#         self.drbg = NISTDRBG(self.trng)
#         self.drbg.instantiate()
        
#         self.crypto_engine = CryptoEngine(self.drbg)
#         self.key_storage = KeyStorage(self.crypto_engine)
        
#         self.ca_service = CertificateAuthorityService(self.crypto_engine, self.key_storage)
#         self.crl_service = CRLService()
#         self.ocsp_service = OCSPResponder(self.crl_service)
#         self.cert_service = CertificateService(self.crypto_engine, self.ca_service)
        
#         self.rest_api = PKIRestAPI(self.ca_service, self.cert_service)
        
#     def run(self):
#         """Запуск PKI системы"""
#         print("Educational PKI System Started")
#         self.rest_api.app.run(host='0.0.0.0', port=5000)

# Использование
if __name__ == "__main__":
    
    # """Запуск учебного PKI"""
    # from core.crypto import CryptoEngine
    # from services.ca_service import CertificateAuthorityService
    # from api.rest_api import PKIAPI
    
    # # Инициализация
    # crypto = CryptoEngine()
    # ca_service = CertificateAuthorityService(crypto)
    # api = PKIAPI(ca_service)
    
    # # Запуск
    # print("🚀 Educational PKI запущен!")
    # api.run()
    
    # config = {
    #     'trng_source': '/dev/urandom',  # или ваш источник
    #     'key_storage_path': './keys',
    #     'database_url': 'sqlite:///pki.db'
    # }
    
    # pki = EducationalPKI(config)
    # pki.run()

    print("🚀 Educational PKI запущен!")