import pytest
from cryptography.hazmat.primitives.asymmetric import padding, ec as ec_module
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.ec import ECDSA

from core import build_core


@pytest.fixture(scope="module")
def core(cfg):
    return build_core(cfg)


def test_trng_health_check(core):
    trng, *_ = core
    result = trng.health_check()
    assert result is True


def test_drbg_generates_unique_bytes(core):
    _, drbg, *_ = core
    a = drbg.generate(32)
    b = drbg.generate(32)
    assert len(a) == 32
    assert a != b


def test_rsa_keypair_sign_verify(core):
    _, _, crypto, _ = core
    key, pub = crypto.generate_rsa_keypair(bits=2048)
    data = b"test payload"
    sig = crypto.sign_data(key, data)
    pss = padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.AUTO)
    pub.verify(sig, data, pss, hashes.SHA256())


def test_ec_keypair_sign_verify(core):
    _, _, crypto, _ = core
    key, pub = crypto.generate_ec_keypair()
    data = b"ec test"
    sig = crypto.sign_data(key, data)
    pub.verify(sig, data, ECDSA(hashes.SHA256()))


def test_key_storage_roundtrip(core, tmp_path):
    _, _, crypto, storage = core
    key, _ = crypto.generate_rsa_keypair(bits=2048)
    storage.store_key("test_key_rt", key, "password123")
    loaded = storage.load_key("test_key_rt", "password123")
    assert loaded.private_numbers() == key.private_numbers()
