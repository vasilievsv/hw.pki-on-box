import pytest
from cryptography.hazmat.primitives.asymmetric import rsa, ec, padding
from cryptography.hazmat.primitives import hashes, serialization

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


class TestCryptoEnginePreconditions:

    def test_rejects_unsupported_ec_curve(self, crypto):
        with pytest.raises(ValueError, match="Unsupported curve"):
            crypto.generate_ec_keypair(curve="P-521")

    def test_rejects_generate_without_drbg(self, sw_cfg):
        trng = HardwareTRNG(sw_cfg)
        drbg = NISTDRBG(trng, sw_cfg)
        engine = CryptoEngine(drbg, sw_cfg)
        with pytest.raises(RuntimeError, match="not initialized"):
            engine.generate_rsa_keypair()

    def test_accepts_rsa_2048(self, crypto):
        priv, pub = crypto.generate_rsa_keypair(bits=2048)
        assert priv.key_size == 2048

    def test_accepts_rsa_4096(self, crypto):
        priv, pub = crypto.generate_rsa_keypair(bits=4096)
        assert priv.key_size == 4096

    def test_accepts_ec_p384(self, crypto):
        priv, pub = crypto.generate_ec_keypair(curve="P-384")
        assert priv.curve.name == "secp384r1"


class TestCryptoEnginePostconditions:

    def test_rsa_keypair_returns_private_and_public(self, crypto):
        priv, pub = crypto.generate_rsa_keypair()
        assert isinstance(priv, rsa.RSAPrivateKey)
        assert isinstance(pub, rsa.RSAPublicKey)

    def test_ec_keypair_returns_private_and_public(self, crypto):
        priv, pub = crypto.generate_ec_keypair()
        assert isinstance(priv, ec.EllipticCurvePrivateKey)
        assert isinstance(pub, ec.EllipticCurvePublicKey)

    def test_rsa_sign_verify_roundtrip(self, crypto):
        priv, pub = crypto.generate_rsa_keypair(bits=2048)
        data = b"contract test data"
        sig = crypto.sign_data(priv, data)
        pub.verify(sig, data, padding.PKCS1v15(), hashes.SHA256())

    def test_ec_sign_verify_roundtrip(self, crypto):
        priv, pub = crypto.generate_ec_keypair()
        data = b"contract test data"
        sig = crypto.sign_data(priv, data)
        pub.verify(sig, data, ec.ECDSA(hashes.SHA256()))

    def test_sign_different_data_different_signatures(self, crypto):
        priv, _ = crypto.generate_rsa_keypair(bits=2048)
        s1 = crypto.sign_data(priv, b"data_a")
        s2 = crypto.sign_data(priv, b"data_b")
        assert s1 != s2


class TestCryptoEngineInvariants:

    def test_private_key_not_in_public_serialization(self, crypto):
        priv, pub = crypto.generate_rsa_keypair(bits=2048)
        pub_pem = pub.public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
        assert b"PRIVATE" not in pub_pem

    def test_uses_sha256_not_sha1(self, crypto):
        priv, pub = crypto.generate_rsa_keypair(bits=2048)
        data = b"invariant check"
        sig = crypto.sign_data(priv, data)
        pub.verify(sig, data, padding.PKCS1v15(), hashes.SHA256())
        with pytest.raises(Exception):
            pub.verify(sig, data, padding.PKCS1v15(), hashes.SHA1())

    def test_openssl_seeded_from_drbg(self, crypto):
        assert crypto._drbg.initialized is True
        crypto._seed_openssl(64)
