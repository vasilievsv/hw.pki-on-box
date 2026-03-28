import os
import json
import struct
from pathlib import Path

from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class KeyStorage:
    def __init__(self, cfg: dict = None):
        cfg = cfg or {}
        storage_cfg = cfg.get("storage", {})
        self._path = Path(storage_cfg.get("path", "asw/PKI/storage/keys"))
        self._path.mkdir(parents=True, exist_ok=True)

        kdf_cfg = cfg.get("kdf", {})
        self._kdf_iterations = int(kdf_cfg.get("iterations", 260000))
        self._kdf_salt_len = int(kdf_cfg.get("salt_len", 32))

    # ── internal ─────────────────────────────────────────────────────────────

    def _derive_key(self, password: bytes, salt: bytes) -> bytes:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=self._kdf_iterations,
        )
        return kdf.derive(password)

    def _key_path(self, key_id: str) -> Path:
        return self._path / f"{key_id}.enc"

    # ── public API ───────────────────────────────────────────────────────────

    def store_key(self, key_id: str, private_key, password: str) -> None:
        pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        salt = os.urandom(self._kdf_salt_len)
        nonce = os.urandom(12)
        aes_key = self._derive_key(password.encode(), salt)
        ciphertext = AESGCM(aes_key).encrypt(nonce, pem, None)

        # layout: [4B salt_len][salt][12B nonce][ciphertext]
        with open(self._key_path(key_id), "wb") as f:
            f.write(struct.pack(">I", len(salt)) + salt + nonce + ciphertext)

    def load_key(self, key_id: str, password: str):
        with open(self._key_path(key_id), "rb") as f:
            data = f.read()

        salt_len = struct.unpack(">I", data[:4])[0]
        salt = data[4 : 4 + salt_len]
        nonce = data[4 + salt_len : 4 + salt_len + 12]
        ciphertext = data[4 + salt_len + 12 :]

        aes_key = self._derive_key(password.encode(), salt)
        pem = AESGCM(aes_key).decrypt(nonce, ciphertext, None)
        return serialization.load_pem_private_key(pem, password=None)

    def delete_key(self, key_id: str) -> None:
        p = self._key_path(key_id)
        if p.exists():
            p.unlink()

    def list_keys(self) -> list:
        return [p.stem for p in self._path.glob("*.enc")]
