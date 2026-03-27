# storage/root_ca_storage.py
import os
import json
import shutil
from cryptography.hazmat.primitives import serialization
from datetime import datetime

class RootCAFileSystemStorage:
    """Хранение Master Root CA в файловой системе"""
    
    def __init__(self, base_path: str = "./master_root_ca"):
        self.base_path = base_path
        self._create_storage_structure()
    
    def _create_storage_structure(self):
        """Создание структуры директорий для хранения Root CA"""
        directories = [
            self.base_path,
            f"{self.base_path}/active",
            f"{self.base_path}/backup",
            f"{self.base_path}/ceremony_records",
            f"{self.base_path}/metadata",
            f"{self.base_path}/export"  # Для безопасного экспорта
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
        
        print(f"📁 Структура хранения создана: {self.base_path}")
    
    def store_master_root_ca(self, private_key, certificate, ceremony_id: str):
        """Безопасное сохранение Master Root CA"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 1. Сохраняем приватный ключ (максимальная защита)
        key_path = f"{self.base_path}/active/master_root_ca_key.pem"
        with open(key_path, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,  # Более совместимый формат
                encryption_algorithm=serialization.BestAvailableEncryption(b"root_ca_password_123")  # В реальности использовать сильный пароль
            ))
        
        # 2. Сохраняем сертификат (публичная часть)
        cert_path = f"{self.base_path}/active/master_root_ca_cert.pem"
        with open(cert_path, "wb") as f:
            f.write(certificate.public_bytes(serialization.Encoding.PEM))
        
        # 3. Создаем резервные копии
        self._create_backups(private_key, certificate, timestamp)
        
        # 4. Сохраняем метаданные
        self._save_metadata(private_key, certificate, ceremony_id, timestamp)
        
        print(f"✅ Master Root CA сохранен в: {self.base_path}/active/")
    
    def _create_backups(self, private_key, certificate, timestamp: str):
        """Создание резервных копий"""
        # Резервная копия ключа (зашифрованная)
        backup_key_path = f"{self.base_path}/backup/master_root_ca_key_{timestamp}.backup"
        with open(backup_key_path, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.BestAvailableEncryption(b"backup_password_456")
            ))
        
        # Резервная копия сертификата
        backup_cert_path = f"{self.base_path}/backup/master_root_ca_cert_{timestamp}.pem"
        with open(backup_cert_path, "wb") as f:
            f.write(certificate.public_bytes(serialization.Encoding.PEM))
        
        print(f"✅ Резервные копии созданы: {self.base_path}/backup/")
    
    def _save_metadata(self, private_key, certificate, ceremony_id: str, timestamp: str):
        """Сохранение метаданных Root CA"""
        metadata = {
            'root_ca_info': {
                'ceremony_id': ceremony_id,
                'creation_date': timestamp,
                'subject': str(certificate.subject),
                'issuer': str(certificate.issuer),
                'serial_number': str(certificate.serial_number),
                'public_key_algorithm': certificate.signature_algorithm_oid._name,
                'key_size': private_key.key_size,
                'validity_period': {
                    'not_before': certificate.not_valid_before.isoformat(),
                    'not_after': certificate.not_valid_after.isoformat()
                }
            },
            'storage_info': {
                'key_location': f"{self.base_path}/active/master_root_ca_key.pem",
                'certificate_location': f"{self.base_path}/active/master_root_ca_cert.pem",
                'backup_count': len([f for f in os.listdir(f"{self.base_path}/backup") if f.endswith('.backup')])
            },
            'security_notes': [
                "Приватный ключ зашифрован с использованием AES-256",
                "Резервные копии хранятся отдельно",
                "Доступ к ключу должен быть строго ограничен"
            ]
        }
        
        metadata_path = f"{self.base_path}/metadata/root_ca_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    def load_master_root_ca(self, password: bytes):
        """Загрузка Master Root CA из хранилища"""
        try:
            # Загружаем приватный ключ
            key_path = f"{self.base_path}/active/master_root_ca_key.pem"
            with open(key_path, "rb") as f:
                private_key = serialization.load_pem_private_key(
                    f.read(),
                    password=password
                )
            
            # Загружаем сертификат
            cert_path = f"{self.base_path}/active/master_root_ca_cert.pem"
            with open(cert_path, "rb") as f:
                certificate = serialization.load_pem_x509_certificate(f.read())
            
            print("✅ Master Root CA успешно загружен")
            return private_key, certificate
            
        except Exception as e:
            print(f"❌ Ошибка загрузки Master Root CA: {e}")
            return None, None
    
    def export_public_certificate(self, export_format: str = "PEM"):
        """Экспорт публичного сертификата для распространения"""
        cert_path = f"{self.base_path}/active/master_root_ca_cert.pem"
        export_path = f"{self.base_path}/export/master_root_ca_public.{export_format.lower()}"
        
        shutil.copy2(cert_path, export_path)
        print(f"✅ Публичный сертификат экспортирован: {export_path}")
        
        return export_path
    
    def get_storage_status(self):
        """Получение статуса хранилища"""
        status = {
            'storage_path': self.base_path,
            'key_exists': os.path.exists(f"{self.base_path}/active/master_root_ca_key.pem"),
            'certificate_exists': os.path.exists(f"{self.base_path}/active/master_root_ca_cert.pem"),
            'backup_count': len([f for f in os.listdir(f"{self.base_path}/backup") if f.endswith(('.backup', '.pem'))]),
            'total_size': self._get_directory_size(self.base_path)
        }
        return status
    
    def _get_directory_size(self, path):
        """Вычисление размера директории"""
        total = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                total += os.path.getsize(fp)
        return total