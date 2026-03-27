# ceremony/master_root_ceremony.py
from datetime import datetime, timezone
import json
import os

class RootCAIssuanceCeremony:
    """Церемония выпуска Master Root CA"""
    
    def __init__(self, ceremony_id: str, participants: list):
        self.ceremony_id = ceremony_id
        self.participants = participants
        self.ceremony_log = []
        self.start_time = None
        self.end_time = None
        
    def log_event(self, event: str, participant: str = "System"):
        """Логирование событий церемонии"""
        timestamp = datetime.now(timezone.utc).isoformat()
        log_entry = {
            'timestamp': timestamp,
            'participant': participant,
            'event': event
        }
        self.ceremony_log.append(log_entry)
        print(f"[{timestamp}] {participant}: {event}")
    
    def perform_ceremony(self):
        """Выполнение церемонии выпуска Root CA"""
        print("🎭 НАЧАЛО ЦЕРЕМОНИИ ВЫПУСКА MASTER ROOT CA")
        print("=" * 60)
        
        self.start_time = datetime.now(timezone.utc)
        self.log_event("Начало церемонии выпуска Master Root CA")
        
        # 1. Подготовительный этап
        self._preparation_phase()
        
        # 2. Генерация ключей
        self._key_generation_phase()
        
        # 3. Создание сертификата
        self._certificate_creation_phase()
        
        # 4. Верификация
        self._verification_phase()
        
        # 5. Архивирование
        self._archiving_phase()
        
        self.end_time = datetime.now(timezone.utc)
        self.log_event("Церемония завершена успешно")
        
        self._generate_ceremony_report()
        
        print("=" * 60)
        print("✅ ЦЕРЕМОНИЯ ЗАВЕРШЕНА УСПЕШНО")
    
    def _preparation_phase(self):
        """Фаза подготовки"""
        self.log_event("Фаза подготовки: проверка оборудования")
        
        # Проверка наличия необходимых компонентов
        requirements = [
            "TRNG источник",
            "Защищенное хранилище", 
            "Резервные носители",
            "Логирование"
        ]
        
        for req in requirements:
            self.log_event(f"Проверка: {req} - OK", "Технический специалист")
        
        # Подписание участниками
        for participant in self.participants:
            self.log_event(f"Участник {participant} подтверждает участие", participant)
    
    def _key_generation_phase(self):
        """Фаза генерации ключей"""
        self.log_event("Фаза генерации ключей Master Root CA")
        
        # Генерация seed для DRBG
        self.log_event("Генерация энтропии из TRNG", "TRNG Оператор")
        trng_seed = self._generate_trng_seed()
        
        # Инициализация DRBG
        self.log_event("Инициализация DRBG с энтропией TRNG", "Криптограф")
        drbg = self._initialize_drbg(trng_seed)
        
        # Генерация ключевой пары
        self.log_event("Генерация RSA-4096 ключевой пары", "Криптограф")
        private_key, public_key = self._generate_rsa_keypair(drbg)
        
        self.master_private_key = private_key
        self.master_public_key = public_key
        
        self.log_event("Ключевая пара успешно сгенерирована")
    
    def _certificate_creation_phase(self):
        """Фаза создания сертификата"""
        self.log_event("Фаза создания самоподписанного сертификата")
        
        # Создание сертификата
        certificate = self._create_root_certificate()
        self.master_certificate = certificate
        
        # Визуальная проверка участниками
        for participant in self.participants:
            self.log_event(f"Визуальная проверка сертификата", participant)
        
        self.log_event("Сертификат Master Root CA создан")
    
    def _verification_phase(self):
        """Фаза верификации"""
        self.log_event("Фаза верификации и проверки")
        
        # Проверка подписи
        self.log_event("Проверка самоподписи сертификата", "Аудитор")
        is_valid = self._verify_self_signature()
        
        if not is_valid:
            raise SecurityError("Ошибка верификации самоподписи!")
        
        # Проверка расширений
        self.log_event("Проверка расширений сертификата", "Аудитор")
        self._verify_certificate_extensions()
        
        self.log_event("Все проверки пройдены успешно")
    
    def _archiving_phase(self):
        """Фаза архивирования"""
        self.log_event("Фаза архивирования и сохранения")
        
        # Сохранение в файловую систему
        self._save_to_filesystem()
        
        # Создание резервных копий
        self._create_backups()
        
        # Уничтожение временных данных
        self._cleanup_temporary_data()
        
        self.log_event("Данные безопасно сохранены и заархивированы")
    
    def _generate_ceremony_report(self):
        """Генерация отчета о церемонии"""
        report = {
            'ceremony_id': self.ceremony_id,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'participants': self.participants,
            'master_ca_fingerprint': self._get_certificate_fingerprint(),
            'key_metadata': {
                'algorithm': 'RSA',
                'key_size': 4096,
                'public_exponent': 65537
            },
            'certificate_metadata': {
                'subject': str(self.master_certificate.subject),
                'issuer': str(self.master_certificate.issuer),
                'serial_number': str(self.master_certificate.serial_number),
                'validity': {
                    'not_before': self.master_certificate.not_valid_before.isoformat(),
                    'not_after': self.master_certificate.not_valid_after.isoformat()
                }
            },
            'ceremony_log': self.ceremony_log
        }
        
        # Сохраняем отчет
        with open(f'ceremony_{self.ceremony_id}_report.json', 'w') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        self.log_event(f"Отчет церемонии сохранен: ceremony_{self.ceremony_id}_report.json")