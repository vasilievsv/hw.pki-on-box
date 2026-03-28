import datetime
from cryptography import x509
from cryptography.hazmat.primitives import hashes

from core.crypto_engine import CryptoEngine
from core.key_storage import KeyStorage


class CRLService:
    def __init__(self, crypto: CryptoEngine, storage: KeyStorage, cfg: dict = None):
        self.crypto = crypto
        self.storage = storage
        cfg = cfg or {}
        self._ca_key_password = cfg.get("storage", {}).get("ca_key_password", "pki-ca-key")
        self._revoked: dict[int, x509.ReasonFlags] = {}
        self._ca_certs: dict[str, x509.Certificate] = {}

    def register_ca_cert(self, ca_id: str, cert: x509.Certificate) -> None:
        self._ca_certs[ca_id] = cert

    def revoke_certificate(self, serial_number: int, reason: x509.ReasonFlags) -> None:
        self._revoked[serial_number] = reason

    def is_revoked(self, serial_number: int) -> bool:
        return serial_number in self._revoked

    def generate_crl(self, ca_id: str) -> x509.CertificateRevocationList:
        ca_cert = self._ca_certs[ca_id]
        ca_key = self.storage.load_key(ca_id, self._ca_key_password)
        now = datetime.datetime.now(datetime.timezone.utc)
        builder = (
            x509.CertificateRevocationListBuilder()
            .issuer_name(ca_cert.subject)
            .last_update(now)
            .next_update(now + datetime.timedelta(days=1))
        )
        for serial, reason in self._revoked.items():
            revoked = (
                x509.RevokedCertificateBuilder()
                .serial_number(serial)
                .revocation_date(now)
                .add_extension(x509.CRLReason(reason), critical=False)
                .build()
            )
            builder = builder.add_revoked_certificate(revoked)
        return builder.sign(ca_key, hashes.SHA256())
