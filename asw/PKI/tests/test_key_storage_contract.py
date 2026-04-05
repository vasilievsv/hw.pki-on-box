import struct
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from core.trng import HardwareTRNG
from core.drbg import NISTDRBG
from core.crypto_engine import CryptoEngine
from core.key_storage import KeyStorage


@pytest.fixture
def sw_cfg(tmp_path):
    return {
        "trng": {"mode": "software"},
        "drbg": {"algorithm": "hmac-sha256", "reseed_interval": 1000, "personalization": ""},
        "crypto": {"rsa_key_size": 2048, "ec_curve": "P-384", "aes_key_size": 256},
        "storage": {"path": str(tmp_path / "keys")},
    }


@pytest.fixture
def storage(sw_cfg):
    return KeyStorage(sw_cfg)


@pytest.fixture
def crypto(sw_cfg):
    trng = HardwareTRNG(sw_cfg)
    drbg = NISTDRBG(trng, sw_cfg)
    drbg.instantiate()
    return CryptoEngine(drbg, sw_cfg)


@pytest.fixture
def rsa_key(crypto):
    priv, pub = crypto.generate_rsa_keypair(bits=2048)
    return priv


PASSWORD = "test-contract-password"


class TestKeyStoragePreconditions:

    def test_rejects_load_nonexistent_key(self, storage):
        with pytest.raises(FileNotFoundError):
            storage.load_key("nonexistent", PASSWORD)

    def test_rejects_wrong_password(self, storage, rsa_key):
        storage.store_key("k1", rsa_key, PASSWORD)
        with pytest.raises(Exception):
            storage.load_key("k1", "wrong-password")

    def test_rejects_delete_nonexistent_silently(self, storage):
        storage.delete_key("ghost")


class TestKeyStoragePostconditions:

    def test_store_load_roundtrip(self, storage, rsa_key):
        storage.store_key("rt1", rsa_key, PASSWORD)
        loaded = storage.load_key("rt1", PASSWORD)
        assert loaded.key_size == rsa_key.key_size
        assert loaded.private_numbers() == rsa_key.private_numbers()

    def test_store_creates_encrypted_file(self, storage, rsa_key):
        storage.store_key("enc1", rsa_key, PASSWORD)
        raw = storage._key_path("enc1").read_bytes()
        assert b"PRIVATE" not in raw

    def test_delete_removes_file(self, storage, rsa_key):
        storage.store_key("del1", rsa_key, PASSWORD)
        assert storage._key_path("del1").exists()
        storage.delete_key("del1")
        assert not storage._key_path("del1").exists()

    def test_list_keys_returns_ids(self, storage, rsa_key):
        storage.store_key("list_a", rsa_key, PASSWORD)
        storage.store_key("list_b", rsa_key, PASSWORD)
        keys = storage.list_keys()
        assert "list_a" in keys
        assert "list_b" in keys


class TestKeyStorageInvariants:

    def test_file_layout_salt_nonce_ciphertext(self, storage, rsa_key):
        storage.store_key("layout1", rsa_key, PASSWORD)
        raw = storage._key_path("layout1").read_bytes()
        salt_len = struct.unpack(">I", raw[:4])[0]
        assert salt_len == 32
        nonce = raw[4 + salt_len : 4 + salt_len + 12]
        assert len(nonce) == 12
        ciphertext = raw[4 + salt_len + 12 :]
        assert len(ciphertext) > 0

    def test_never_stores_plaintext_pem(self, storage, rsa_key):
        storage.store_key("plain1", rsa_key, PASSWORD)
        raw = storage._key_path("plain1").read_bytes()
        assert b"BEGIN" not in raw
        assert b"PRIVATE" not in raw

    def test_key_ids_unique(self, storage, rsa_key):
        storage.store_key("u1", rsa_key, PASSWORD)
        storage.store_key("u2", rsa_key, PASSWORD)
        keys = storage.list_keys()
        assert len(keys) == len(set(keys))

    def test_different_stores_produce_different_ciphertext(self, storage, rsa_key):
        storage.store_key("diff1", rsa_key, PASSWORD)
        storage.store_key("diff2", rsa_key, PASSWORD)
        r1 = storage._key_path("diff1").read_bytes()
        r2 = storage._key_path("diff2").read_bytes()
        assert r1 != r2
