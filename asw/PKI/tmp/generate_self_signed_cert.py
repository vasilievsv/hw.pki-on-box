from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from datetime import datetime, timezone, timedelta

def generate_self_signed_cert():
    # Генерация приватного ключа
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    
    # Создание самоподписанного сертификата
    subject = issuer = x509.Name([
        x509.NameAttribute(x509.NameOID.COUNTRY_NAME, "RU"),
        x509.NameAttribute(x509.NameOID.COMMON_NAME, "example.com"),
    ])
    
    certificate = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(              issuer
    ).public_key(               private_key.public_key()
    ).serial_number(            x509.random_serial_number()
    ).not_valid_before(         datetime.now(timezone.utc)  
    ).not_valid_after(          datetime.now(timezone.utc) + timedelta(days=365)
    ).add_extension(            x509.SubjectAlternativeName([x509.DNSName("example.com")]),        critical=False,
    ).sign(                     private_key, hashes.SHA256())
    
    return private_key, certificate

def save_keys_and_certificate(private_key, certificate):
    """
    Сохранение ключей и сертификата
    """
    # Сохранение приватного ключа (СЕКРЕТНО!)
    with open("firmware_signing_key.pem", "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.BestAvailableEncryption(b'strong_password')
        ))
    
    # Сохранение сертификата с публичным ключом
    with open("firmware_signing_cert.pem", "wb") as f:
        f.write(certificate.public_bytes(serialization.Encoding.PEM))
    
    # Сохранение публичного ключа отдельно (для MCU)
    with open("firmware_public_key.pem", "wb") as f:
        f.write(private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ))

asymmetric_keys = generate_self_signed_cert()
save_keys_and_certificate(asymmetric_keys[0], asymmetric_keys[1])
