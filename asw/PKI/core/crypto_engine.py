import logging
from typing import Optional

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, ec, padding
from cryptography.hazmat.primitives.asymmetric.ec import SECP384R1
from cryptography.hazmat.bindings.openssl.binding import Binding

from .allowed_algorithms import AllowedSigAlg, RSA_PSS_SHA256, ECDSA_SHA256
from .drbg import NISTDRBG

audit_log = logging.getLogger("pki.crypto_engine")

_EC_CURVES = {
    "P-384": SECP384R1(),
}

_openssl = Binding()


class CryptoEngine:
    def __init__(self, drbg: NISTDRBG, cfg: dict = None):
        self._drbg = drbg
        cfg = cfg or {}
        crypto_cfg = cfg.get("crypto", {})
        self._rsa_bits = int(crypto_cfg.get("rsa_key_size", 4096))
        self._ec_curve = crypto_cfg.get("ec_curve", "P-384")

    def _seed_openssl(self, n: int = 64) -> None:
        """Подмешать HW энтропию (NISTDRBG <- HardwareTRNG) в OpenSSL RAND пул."""
        data = self._drbg.generate(n)
        _openssl.lib.RAND_add(data, len(data), float(len(data)))

    # -- key generation -------------------------------------------------------

    def generate_rsa_keypair(self, bits: int = None):
        self._seed_openssl()
        key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=bits or self._rsa_bits,
        )
        audit_log.info("generate_rsa_keypair bits=%d", bits or self._rsa_bits)
        return key, key.public_key()

    def generate_ec_keypair(self, curve: str = None):
        self._seed_openssl()
        curve_obj = _EC_CURVES.get(curve or self._ec_curve)
        if curve_obj is None:
            raise ValueError(f"Unsupported curve: {curve or self._ec_curve}")
        key = ec.generate_private_key(curve_obj)
        audit_log.info("generate_ec_keypair curve=%s", curve or self._ec_curve)
        return key, key.public_key()

    # -- certificate ----------------------------------------------------------

    def build_certificate(self, builder: x509.CertificateBuilder, key):
        return builder.sign(key, hashes.SHA256())

    def verify_certificate(self, cert: x509.Certificate) -> bool:
        try:
            pub = cert.public_key()
            params = cert.signature_algorithm_parameters
            if isinstance(pub, ec.EllipticCurvePublicKey):
                pub.verify(cert.signature, cert.tbs_certificate_bytes, params)
            else:
                pub.verify(cert.signature, cert.tbs_certificate_bytes, params, cert.signature_hash_algorithm)
            return True
        except Exception:
            return False

    def get_fingerprint(self, cert: x509.Certificate) -> str:
        digest = cert.fingerprint(hashes.SHA256())
        return digest.hex()

    # -- signing --------------------------------------------------------------

    def sign_data(self, key, data: bytes, alg: Optional[AllowedSigAlg] = None) -> bytes:
        if alg is None:
            alg = ECDSA_SHA256 if isinstance(key, ec.EllipticCurvePrivateKey) else RSA_PSS_SHA256
        sig = key.sign(data, *alg.sign_args)
        audit_log.info("sign_data algo=%s data_len=%d", alg.name, len(data))
        return sig
