import datetime
from enum import Enum
from cryptography import x509
from cryptography.x509 import ocsp
from cryptography.hazmat.primitives import hashes

from core.crypto_engine import CryptoEngine
from services.crl_service import CRLService


class OCSPStatus(Enum):
    GOOD = "good"
    REVOKED = "revoked"
    UNKNOWN = "unknown"


class OCSPResponder:
    def __init__(self, crl_service: CRLService, crypto: CryptoEngine, cfg: dict = None):
        self.crl_service = crl_service
        self.crypto = crypto
        cfg = cfg or {}
        self._ca_key_password = cfg.get("storage", {}).get("ca_key_password", "pki-ca-key")

    def check_certificate_status(self, serial_number: int) -> OCSPStatus:
        if self.crl_service.is_revoked(serial_number):
            return OCSPStatus.REVOKED
        if serial_number > 0:
            return OCSPStatus.GOOD
        return OCSPStatus.UNKNOWN

    def build_ocsp_response(
        self,
        serial_number: int,
        ca_id: str,
        issuer_cert: x509.Certificate,
        responder_cert: x509.Certificate,
    ) -> ocsp.OCSPResponse:
        status = self.check_certificate_status(serial_number)
        ca_key = self.crl_service.storage.load_key(ca_id, self._ca_key_password)
        now = datetime.datetime.now(datetime.timezone.utc)

        builder = ocsp.OCSPResponseBuilder()

        if status == OCSPStatus.REVOKED:
            reason = self.crl_service._revoked[serial_number]
            builder = builder.add_response(
                cert=None,
                issuer=issuer_cert,
                algorithm=hashes.SHA256(),
                cert_status=ocsp.OCSPCertStatus.REVOKED,
                this_update=now,
                next_update=now + datetime.timedelta(hours=1),
                revocation_time=now,
                revocation_reason=reason,
            ).responder_id(ocsp.OCSPResponderEncoding.HASH, responder_cert)
        else:
            builder = builder.add_response(
                cert=None,
                issuer=issuer_cert,
                algorithm=hashes.SHA256(),
                cert_status=ocsp.OCSPCertStatus.GOOD,
                this_update=now,
                next_update=now + datetime.timedelta(hours=1),
                revocation_time=None,
                revocation_reason=None,
            ).responder_id(ocsp.OCSPResponderEncoding.HASH, responder_cert)

        return builder.sign(ca_key, hashes.SHA256())
