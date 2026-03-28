import datetime
from cryptography import x509
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
from cryptography.hazmat.primitives import hashes

from core.crypto_engine import CryptoEngine
from core.key_storage import KeyStorage
from services.ca_service import CertificateAuthorityService
from storage.database import PKIDatabase
from storage.file_storage import CertificateFileStorage


class CertificateService:
    def __init__(
        self,
        crypto: CryptoEngine,
        storage: KeyStorage,
        ca_service: CertificateAuthorityService,
        db: PKIDatabase,
        file_storage: CertificateFileStorage,
    ):
        self.crypto = crypto
        self.storage = storage
        self.ca_service = ca_service
        self._db = db
        self._file_storage = file_storage

    def _base_builder(self, common_name: str, public_key, ca_id: str, validity_days: int) -> x509.CertificateBuilder:
        ca_cert = self.ca_service.get_ca_cert(ca_id)
        now = datetime.datetime.now(datetime.timezone.utc)
        return (
            x509.CertificateBuilder()
            .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)]))
            .issuer_name(ca_cert.subject)
            .public_key(public_key)
            .serial_number(x509.random_serial_number())
            .not_valid_before(now)
            .not_valid_after(now + datetime.timedelta(days=validity_days))
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(x509.SubjectKeyIdentifier.from_public_key(public_key), critical=False)
        )

    def issue_server_certificate(self, common_name: str, san_dns: list[str], ca_id: str):
        private_key, public_key = self.crypto.generate_rsa_keypair(2048)
        builder = (
            self._base_builder(common_name, public_key, ca_id, validity_days=365)
            .add_extension(
                x509.SubjectAlternativeName([x509.DNSName(d) for d in san_dns]),
                critical=False,
            )
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True, key_encipherment=True, content_commitment=False,
                    data_encipherment=False, key_agreement=False, key_cert_sign=False,
                    crl_sign=False, encipher_only=False, decipher_only=False,
                ),
                critical=True,
            )
            .add_extension(
                x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]),
                critical=False,
            )
        )
        cert = self.ca_service.sign_csr(
            x509.CertificateSigningRequestBuilder()
            .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)]))
            .sign(private_key, hashes.SHA256()),
            ca_id,
        )
        # rebuild with full extensions via direct sign
        ca_key = self.ca_service.storage.load_key(ca_id, self.ca_service._ca_key_password)
        cert = self.crypto.build_certificate(builder, ca_key)
        self._db.store_certificate(cert, ca_id)
        self._file_storage.store_cert(cert, label=common_name)
        return private_key, cert

    def issue_client_certificate(self, user_id: str, ca_id: str):
        private_key, public_key = self.crypto.generate_ec_keypair("P-384")
        builder = (
            self._base_builder(user_id, public_key, ca_id, validity_days=365)
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True, content_commitment=True, key_encipherment=False,
                    data_encipherment=False, key_agreement=False, key_cert_sign=False,
                    crl_sign=False, encipher_only=False, decipher_only=False,
                ),
                critical=True,
            )
            .add_extension(
                x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CLIENT_AUTH]),
                critical=False,
            )
        )
        ca_key = self.ca_service.storage.load_key(ca_id, self.ca_service._ca_key_password)
        cert = self.crypto.build_certificate(builder, ca_key)
        self._db.store_certificate(cert, ca_id)
        self._file_storage.store_cert(cert, label=user_id)
        return private_key, cert

    def issue_firmware_certificate(self, device_id: str, ca_id: str):
        private_key, public_key = self.crypto.generate_rsa_keypair(2048)
        builder = (
            self._base_builder(device_id, public_key, ca_id, validity_days=365 * 5)
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True, content_commitment=True, key_encipherment=False,
                    data_encipherment=False, key_agreement=False, key_cert_sign=False,
                    crl_sign=False, encipher_only=False, decipher_only=False,
                ),
                critical=True,
            )
            .add_extension(
                x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CODE_SIGNING]),
                critical=False,
            )
        )
        ca_key = self.ca_service.storage.load_key(ca_id, self.ca_service._ca_key_password)
        cert = self.crypto.build_certificate(builder, ca_key)
        self._db.store_certificate(cert, ca_id)
        self._file_storage.store_cert(cert, label=device_id)
        return private_key, cert
