
### Общая архитектура учебного PKI
```
┌─────────────────────────────────────────────────┐
│                 Управляющий слой                │
├─────────────────────────────────────────────────┤
│          Службы PKI (REST API / CLI)            │
├─────────────────────────────────────────────────┤
│     Движок криптографии (Crypto Engine)         │
├─────────────────────────────────────────────────┤
│  TRNG → DRBG → Хранилище ключей (HSM эмуляция)  │
└─────────────────────────────────────────────────┘
```

####  Модульная структура проекта
```
├── PKI/
│
├── main.py                 # Точка входа
├── requirements.txt        # Зависимости
├── core/
│   ├── __init__.py
│   ├── trng.py              # Ваш TRNG
│   ├── drbg.py              # Ваш DRBG (NIST-совместимый)
│   ├── crypto_engine.py     # Движок криптографии
│   └── key_storage.py       # Хранилище ключей
├── services/
│   ├── __init__.py
│   ├── ca_service.py        # Управление ЦС
│   ├── certificate_service.py # Выпуск сертификатов
│   ├── crl_service.py       # Списки отозванных
│   └── ocsp_service.py      # Online статус
├── models/
│   ├── __init__.py
│   ├── certificate.py       # Модели данных
│   ├── key_pair.py
│   └── request.py
├── api/
│   ├── __init__.py
│   ├── rest_api.py          # REST интерфейс
│   └── cli.py              # Командная строка
└── storage/
│    ├── __init__.py
│    ├── database.py          # SQLite/PostgreSQL
│    └── file_storage.py      # Файловое хранилище
└── utils/                 # Утилиты
    ├── config.py
    └── helpers.py
```

#### Сценарий 1: Полный цикл выпуска сертификата
```
def learning_scenario_1():
    """Создание корневого ЦС -> промежуточного ЦС -> серверного сертификата"""
    pki = EducationalPKI(config)
    
    # 1. Создание корневого ЦС
    root_ca = pki.ca_service.create_root_ca("MyRootCA", 10)
    
    # 2. Создание промежуточного ЦС
    intermediate_ca = pki.ca_service.create_intermediate_ca("root_ca_MyRootCA", "MyIntermediateCA")
    
    # 3. Выпуск серверного сертификата
    server_key, server_cert = pki.cert_service.issue_server_certificate(
        "myserver.example.com", 
        ["myserver.example.com", "www.example.com"],
        "intermediate_ca_MyIntermediateCA"
    )
```

#### Сценарий 2: Отзыв и проверка сертификатов
```
def learning_scenario_2():
    """Отзыв сертификата и проверка через OCSP/CRL"""
    pki = EducationalPKI(config)
    
    # Отзыв сертификата
    pki.crl_service.revoke_certificate("123456789", "key_compromise")
    
    # Генерация CRL
    crl = pki.crl_service.generate_crl("root_ca_MyRootCA")
    
    # Проверка через OCSP
    status = pki.ocsp_service.check_certificate_status("123456789")
    print(f"Certificate status: {status}")
```

#### Мониторинг и логирование
```
class PKIMonitor:
    """Мониторинг работы PKI системы"""
    
    def log_certificate_issued(self, serial_number: str, common_name: str):
        # Логирование выпуска сертификата
        pass
        
    def log_certificate_revoked(self, serial_number: str, reason: str):
        # Логирование отзыва сертификата
        pass
        
    def get_system_stats(self):
        # Статистика системы
        return {
            'total_cas': len(self.ca_service.cas),
            'total_certificates_issued': self.cert_service.issued_count,
            'total_revoked': len(self.crl_service.revoked_certificates)
        }
```

### Технологический стек Python для PKI
#### Криптография
```
# Основные библиотеки
from cryptography import x509                                           # X.509 сертификаты
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, ec, padding
from cryptography.hazmat.primitives.kdf.hkdf import HKDF                # KDF
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
import hashlib                                                          # Хеш-функции
import hmac                                                             # HMAC
```

#### Сеть и API
```
# Веб-интерфейс и API
from flask import Flask, jsonify, request                   # REST API
import requests                                             # HTTP клиент
from http.server import HTTPServer, BaseHTTPRequestHandler  # Low-level HTTP

# Сокеты для OCSP/SCEP
import socket
import ssl
```

#### Базы данных и хранение
```
# Хранение данных
import sqlite3                                  # Встроенная БД
import pickle                                   # Сериализация
import json                                     # Конфиги
from pathlib import Path                        # Работа с файлами
```

#### Утилиты
```
# Вспомогательные библиотеки
import argparse                                 # Парсинг аргументов
import logging                                  # Логирование
import asyncio                                  # Асинхронность
from typing import Dict, List, Optional         # Типизация
```

#### Итоговая структура файлов

```
хранения выпущенных сертификатов

/pki_data/                                              # Отдельная директория данных
├── root_ca/                                            # Root CA данные
│    ├── active/
│    │   ├── master_root_ca_key.pem                     # Зашифрованный приватный ключ
│    │   └── master_root_ca_cert.pem                    # Публичный сертификат
│    ├── backup/
│    │   ├── master_root_ca_key_20241201_143022.backup
│    │   └── master_root_ca_cert_20241201_143022.pem
│    ├── ceremony_records/
│    │   └── ceremony_FIRST_ROOT_CA_2024_report.json
│    ├── metadata/
│    │   └── root_ca_metadata.json
│    └── export/
│        └── master_root_ca_public.pem                  # Для распространения
│
│
└── intermediates/                     # Intermediate CA данные
    ├── security_ca/                   # Intermediate CA для безопасности
    │   ├── ca/                        # Данные самого CA
    │   │   ├── private/
    │   │   │   └── security_ca.key.pem
    │   │   ├── security_ca.crt.pem
    │   │   └── security_ca_chain.pem
    │   └── issued/                    # ВЫПУЩЕННЫЕ СЕРТИФИКАТЫ
    │       ├── database/              # Учет и метаданные
    │       │   ├── index.txt          # Главная база (OpenSSL-формат)
    │       │   ├── index.txt.attr
    │       │   ├── serial             # Текущий серийный номер
    │       │   └── serial.old
    │       ├── certs/                 # Хранилище сертификатов
    │       │   ├── by_serial/
    │       │   │   ├── 1000.pem       # Сертификат
    │       │   │   ├── 1000.meta.json # Метаданные
    │       │   │   ├── 1001.pem
    │       │   │   └── 1001.meta.json
    │       │   └── by_cn/             # Альтернативная индексация
    │       │       ├── server1.company.com -> ../by_serial/1000.pem
    │       │       └── server2.company.com -> ../by_serial/1001.pem
    │       ├── csr/                    # Архив CSR
    │       │   ├── 1000.csr.pem
    │       │   └── 1001.csr.pem
    │       ├── private/                # Приватные ключи (если выпускаете)
    │       │   ├── 1000.key.pem
    │       │   └── 1001.key.pem
    │       └── crl/                    # Списки отзыва
    │           ├── security_ca.crl
    │           └── crl_number
    │                                   # Другой Intermediate CA
    ├── web_services_ca               
    ├── web_services_ca
    └── web_services_ca
```

```
# Разные схемы подписи:
- RSASSA-PKCS1-v1_5 vs RSASSA-PSS
- ECDSA с разными хэшами
- Ed25519/Ed448 для современных систем

# Техники отзыва:
- CRL (Certificate Revocation Lists)
- OCSP (Online Certificate Status Protocol)
- OCSP Stapling
- CRLite, Let's Encrypt CRL Sets
```