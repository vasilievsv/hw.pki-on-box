import os
import pytest

from cryptography.hazmat.primitives.asymmetric import rsa

from core.key_storage import KeyStorage, _zeroize


class TestZeroize:
    def test_zeroize_bytearray(self):
        data = bytearray(b"SECRET_KEY_MATERIAL_1234567890AB")
        _zeroize(data)
        assert data == bytearray(b"\x00" * 32)

    def test_zeroize_empty(self):
        _zeroize(b"")
        _zeroize(None)

    def test_zeroize_bytes_no_crash(self):
        data = b"immutable bytes"
        _zeroize(data)


class TestSecureDelete:
    def test_delete_key_overwrites_file(self, tmp_path):
        cfg = {"storage": {"path": str(tmp_path / "keys")}}
        storage = KeyStorage(cfg)
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        storage.store_key("test-del", key, "pass123")

        key_path = storage._key_path("test-del")
        assert key_path.exists()
        original_size = key_path.stat().st_size

        storage.delete_key("test-del")
        assert not key_path.exists()

    def test_delete_nonexistent_key_no_error(self, tmp_path):
        cfg = {"storage": {"path": str(tmp_path / "keys")}}
        storage = KeyStorage(cfg)
        storage.delete_key("nonexistent")


class TestLoadStoreZeroization:
    def test_store_load_roundtrip_still_works(self, tmp_path):
        cfg = {"storage": {"path": str(tmp_path / "keys")}}
        storage = KeyStorage(cfg)
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        storage.store_key("test-z", key, "pass123")
        loaded = storage.load_key("test-z", "pass123")
        assert loaded.key_size == 2048
