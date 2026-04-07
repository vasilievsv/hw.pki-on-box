import datetime
from cryptography import x509
from cryptography.hazmat.primitives import hashes

from core.crypto_engine import CryptoEngine
from core.key_storage import KeyStorage
from storage.database import PKIDatabase


class CRLService:
    def __init__(self, crypto: CryptoEngine, storage: KeyStorage, ca_service, db: PKIDatabase, cfg: dict = None):
        self.crypto = crypto
        self.storage = storage
        self._ca_service = ca_service
        self._db = db
        cfg = cfg or {}
        self._ca_key_password = cfg.get("storage", {}).get("ca_key_password", "pki-ca-key")
        self._ca_certs = {}  # type: dict

    def register_ca_cert(self, ca_id: str, cert: x509.Certificate) -> None:
        self._ca_certs[ca_id] = cert

    def revoke_certificate(self, serial_number: int, reason: x509.ReasonFlags) -> None:
        self._db.revoke_certificate(serial_number, reason)

    def is_revoked(self, serial_number: int) -> bool:
        return self._db.is_revoked(serial_number)

    def generate_crl(self, ca_id: str) -> x509.CertificateRevocationList:
        ca_cert = self._ca_certs.get(ca_id) or self._ca_service.get_ca_cert(ca_id)
        ca_key = self.storage.load_key(ca_id, self._ca_key_password)
        now = datetime.datetime.now(datetime.timezone.utc)
        builder = (
            x509.CertificateRevocationListBuilder()
            .issuer_name(ca_cert.subject)
            .last_update(now)
            .next_update(now + datetime.timedelta(days=1))
        )
        for serial, reason in self._db.get_revoked(ca_id).items():
            revoked = (
                x509.RevokedCertificateBuilder()
                .serial_number(serial)
                .revocation_date(now)
                .add_extension(x509.CRLReason(reason), critical=False)
                .build()
            )
            builder = builder.add_revoked_certificate(revoked)
        return builder.sign(ca_key, hashes.SHA256())
