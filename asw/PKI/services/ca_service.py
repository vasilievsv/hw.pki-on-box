import datetime
from typing import Optional, Dict
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes

from core.crypto_engine import CryptoEngine
from core.key_storage import KeyStorage
from storage.database import PKIDatabase


class CertificateAuthorityService:
    def __init__(self, crypto: CryptoEngine, storage: KeyStorage, db: PKIDatabase, cfg: dict = None):
        self.crypto = crypto
        self.storage = storage
        self._db = db
        cfg = cfg or {}
        self._ca_key_password = cfg.get("storage", {}).get("ca_key_password", "pki-ca-key")
        self._certs: Dict[str, x509.Certificate] = {}
        for row in self._db.list_ca_certs():
            cert = self._db.load_ca_cert(row["id"])
            if cert:
                self._certs[row["id"]] = cert

    def _ca_id(self, name: str) -> str:
        return f"ca_{name.lower().replace(' ', '_')}"

    def _build_ca_cert(
        self,
        subject_name: str,
        public_key,
        signing_key,
        issuer_name: x509.Name,
        validity_years: int,
        path_length: Optional[int],
    ) -> x509.Certificate:
        now = datetime.datetime.now(datetime.timezone.utc)
        subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, subject_name)])
        builder = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer_name)
            .public_key(public_key)
            .serial_number(x509.random_serial_number())
            .not_valid_before(now)
            .not_valid_after(now + datetime.timedelta(days=365 * validity_years))
            .add_extension(x509.BasicConstraints(ca=True, path_length=path_length), critical=True)
            .add_extension(x509.SubjectKeyIdentifier.from_public_key(public_key), critical=False)
            .add_extension(
                x509.KeyUsage(
                    digital_signature=True, key_cert_sign=True, crl_sign=True,
                    content_commitment=False, key_encipherment=False,
                    data_encipherment=False, key_agreement=False,
                    encipher_only=False, decipher_only=False,
                ),
                critical=True,
            )
        )
        return self.crypto.build_certificate(builder, signing_key)

    def create_root_ca(self, name: str, validity_years: int = 20) -> x509.Certificate:
        private_key, public_key = self.crypto.generate_rsa_keypair(4096)
        subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, name)])
        cert = self._build_ca_cert(name, public_key, private_key, subject, validity_years, path_length=None)
        ca_id = self._ca_id(name)
        self.storage.store_key(ca_id, private_key, self._ca_key_password)
        self._certs[ca_id] = cert
        self._db.store_ca_cert(ca_id, name, cert)
        return cert

    def create_intermediate_ca(self, name: str, parent_ca_id: str, validity_years: int = 10) -> x509.Certificate:
        parent_cert = self._certs[parent_ca_id]
        parent_key = self.storage.load_key(parent_ca_id, self._ca_key_password)
        private_key, public_key = self.crypto.generate_rsa_keypair(4096)
        cert = self._build_ca_cert(
            name, public_key, parent_key,
            parent_cert.subject, validity_years, path_length=0,
        )
        ca_id = self._ca_id(name)
        self.storage.store_key(ca_id, private_key, self._ca_key_password)
        self._certs[ca_id] = cert
        self._db.store_ca_cert(ca_id, name, cert)
        return cert

    def get_ca_cert(self, ca_id: str) -> x509.Certificate:
        return self._certs[ca_id]

    def sign_csr(self, csr: x509.CertificateSigningRequest, ca_id: str) -> x509.Certificate:
        ca_cert = self._certs[ca_id]
        ca_key = self.storage.load_key(ca_id, self._ca_key_password)
        now = datetime.datetime.now(datetime.timezone.utc)
        builder = (
            x509.CertificateBuilder()
            .subject_name(csr.subject)
            .issuer_name(ca_cert.subject)
            .public_key(csr.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now)
            .not_valid_after(now + datetime.timedelta(days=365 * 2))
        )
        for ext in csr.extensions:
            builder = builder.add_extension(ext.value, critical=ext.critical)
        return self.crypto.build_certificate(builder, ca_key)
