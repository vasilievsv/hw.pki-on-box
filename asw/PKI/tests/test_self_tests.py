import pytest
from unittest.mock import patch

from core.self_tests import (
    run_kat,
    CryptoSelfTestError,
    _kat_aes_gcm,
    _kat_hmac_sha256,
    _kat_sha256,
    _kat_hmac_drbg,
    _kat_rsa_sign,
    _kat_ecdsa_sign,
)


class TestKATPass:
    def test_all_kat_pass(self):
        run_kat()

    def test_aes_gcm(self):
        _kat_aes_gcm()

    def test_hmac_sha256(self):
        _kat_hmac_sha256()

    def test_sha256(self):
        _kat_sha256()

    def test_hmac_drbg(self):
        _kat_hmac_drbg()

    def test_rsa_sign(self):
        _kat_rsa_sign()

    def test_ecdsa_sign(self):
        _kat_ecdsa_sign()


class TestKATDetectsCorruption:
    def test_aes_gcm_corrupted(self):
        with patch("core.self_tests.AESGCM") as mock:
            mock.return_value.encrypt.return_value = b"\x00" * 80
            with pytest.raises(CryptoSelfTestError, match="AES"):
                _kat_aes_gcm()

    def test_hmac_sha256_corrupted(self):
        with patch("core.self_tests.hmac") as mock:
            mock.new.return_value.digest.return_value = b"\x00" * 32
            with pytest.raises(CryptoSelfTestError, match="HMAC-SHA256"):
                _kat_hmac_sha256()

    def test_sha256_corrupted(self):
        with patch("core.self_tests.hashlib") as mock:
            mock.sha256.return_value.digest.return_value = b"\x00" * 32
            with pytest.raises(CryptoSelfTestError, match="SHA-256"):
                _kat_sha256()
