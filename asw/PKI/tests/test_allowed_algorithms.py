import pytest
from cryptography.hazmat.primitives.asymmetric import padding, ec
from cryptography.hazmat.primitives import hashes

from core.allowed_algorithms import (
    AllowedSigAlg, AllowedAead,
    RSA_PSS_SHA256, RSA_PSS_SHA384, ECDSA_SHA256, ECDSA_SHA384, AES_256_GCM,
)
from core.trng import HardwareTRNG
from core.drbg import NISTDRBG
from core.crypto_engine import CryptoEngine


@pytest.fixture
def sw_cfg():
    return {
        "trng": {"mode": "software"},
        "drbg": {"algorithm": "hmac-sha256", "reseed_interval": 1000, "personalization": ""},
        "crypto": {"rsa_key_size": 2048, "ec_curve": "P-384", "aes_key_size": 256},
    }


@pytest.fixture
def crypto(sw_cfg):
    trng = HardwareTRNG(sw_cfg)
    drbg = NISTDRBG(trng, sw_cfg)
    drbg.instantiate()
    return CryptoEngine(drbg, sw_cfg)


class TestAllowedSigAlgParse:

    def test_parse_rsa_pss_sha256(self):
        alg = AllowedSigAlg.parse("RSA-PSS-SHA256")
        assert alg.name == "RSA-PSS-SHA256"
        assert alg.is_rsa is True
        assert alg.is_ec is False

    def test_parse_ecdsa_sha256(self):
        alg = AllowedSigAlg.parse("ECDSA-SHA256")
        assert alg.name == "ECDSA-SHA256"
        assert alg.is_ec is True
        assert alg.is_rsa is False

    def test_rejects_forbidden_pkcs1v15(self):
        with pytest.raises(ValueError, match="Forbidden"):
            AllowedSigAlg.parse("RSA-PKCS1v15-SHA256")

    def test_rejects_forbidden_sha1(self):
        with pytest.raises(ValueError, match="Forbidden"):
            AllowedSigAlg.parse("RSA-PSS-SHA1")

    def test_rejects_unknown(self):
        with pytest.raises(ValueError, match="Unknown"):
            AllowedSigAlg.parse("CHACHA20-POLY1305")

    def test_prebuilt_constants_are_frozen(self):
        with pytest.raises(AttributeError):
            RSA_PSS_SHA256.name = "hacked"


class TestAllowedAeadParse:

    def test_parse_aes_256_gcm(self):
        alg = AllowedAead.parse("AES-256-GCM")
        assert alg.name == "AES-256-GCM"

    def test_rejects_unknown_aead(self):
        with pytest.raises(ValueError, match="Unknown AEAD"):
            AllowedAead.parse("AES-128-CBC")


class TestSignDataWithAllowedSigAlg:

    def test_rsa_explicit_alg(self, crypto):
        priv, pub = crypto.generate_rsa_keypair(bits=2048)
        sig = crypto.sign_data(priv, b"explicit alg", alg=RSA_PSS_SHA256)
        pss = padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.AUTO)
        pub.verify(sig, b"explicit alg", pss, hashes.SHA256())

    def test_ec_explicit_alg(self, crypto):
        priv, pub = crypto.generate_ec_keypair()
        sig = crypto.sign_data(priv, b"explicit ec", alg=ECDSA_SHA384)
        pub.verify(sig, b"explicit ec", ec.ECDSA(hashes.SHA384()))

    def test_rsa_default_alg_is_pss(self, crypto):
        priv, pub = crypto.generate_rsa_keypair(bits=2048)
        sig = crypto.sign_data(priv, b"default alg")
        pss = padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.AUTO)
        pub.verify(sig, b"default alg", pss, hashes.SHA256())

    def test_ec_default_alg_is_ecdsa_sha256(self, crypto):
        priv, pub = crypto.generate_ec_keypair()
        sig = crypto.sign_data(priv, b"default ec")
        pub.verify(sig, b"default ec", ec.ECDSA(hashes.SHA256()))

    def test_backward_compat_no_alg_param(self, crypto):
        priv, pub = crypto.generate_rsa_keypair(bits=2048)
        sig = crypto.sign_data(priv, b"compat")
        assert isinstance(sig, bytes)
        assert len(sig) > 0
