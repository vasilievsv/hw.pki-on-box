import hmac
import hashlib

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.asymmetric import rsa, ec, padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.ec import SECP384R1


class CryptoSelfTestError(Exception):
    pass


def _kat_aes_gcm():
    key = bytes.fromhex(
        "feffe9928665731c6d6a8f9467308308"
        "feffe9928665731c6d6a8f9467308308"
    )
    nonce = bytes.fromhex("cafebabefacedbaddecaf888")
    plaintext = bytes.fromhex(
        "d9313225f88406e5a55909c5aff5269a"
        "86a7a9531534f7da2e4c303d8a318a72"
        "1c3c0c95956809532fcf0e2449a6b525"
        "b16aedf5aa0de657ba637b391aafd255"
    )
    expected_ct = bytes.fromhex(
        "522dc1f099567d07f47f37a32a84427d"
        "643a8cdcbfe5c0c97598a2bd2555d1aa"
        "8cb08e48590dbb3da7b08b1056828838"
        "c5f61e6393ba7a0abcc9f662898015ad"
    )
    expected_tag = bytes.fromhex("b094dac5d93471bdec1a502270e3cc6c")

    aesgcm = AESGCM(key)
    ct_with_tag = aesgcm.encrypt(nonce, plaintext, None)
    ct = ct_with_tag[:-16]
    tag = ct_with_tag[-16:]

    if ct != expected_ct or tag != expected_tag:
        raise CryptoSelfTestError("KAT AES-256-GCM FAILED")


def _kat_hmac_sha256():
    key = bytes.fromhex(
        "4a656665"
    )
    msg = b"what do ya want for nothing?"
    expected = bytes.fromhex(
        "5bdcc146bf60754e6a042426089575c7"
        "5a003f089d2739839dec58b964ec3843"
    )
    result = hmac.new(key, msg, hashlib.sha256).digest()
    if result != expected:
        raise CryptoSelfTestError("KAT HMAC-SHA256 FAILED")


def _kat_sha256():
    msg = b"abc"
    expected = bytes.fromhex(
        "ba7816bf8f01cfea414140de5dae2223"
        "b00361a396177a9cb410ff61f20015ad"
    )
    result = hashlib.sha256(msg).digest()
    if result != expected:
        raise CryptoSelfTestError("KAT SHA-256 FAILED")


def _kat_hmac_drbg():
    k = b"\x00" * 32
    v = b"\x01" * 32
    seed = b"\x00" * 32

    def H(key, data):
        return hmac.new(key, data, hashlib.sha256).digest()

    k = H(k, v + b"\x00" + seed)
    v = H(k, v)
    k = H(k, v + b"\x01" + seed)
    v = H(k, v)

    v = H(k, v)
    output = v

    if len(output) != 32 or output == b"\x00" * 32:
        raise CryptoSelfTestError("KAT HMAC_DRBG FAILED")


def _kat_rsa_sign():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    data = b"KAT RSA test vector"
    sig = key.sign(data, padding.PKCS1v15(), hashes.SHA256())
    try:
        key.public_key().verify(sig, data, padding.PKCS1v15(), hashes.SHA256())
    except Exception:
        raise CryptoSelfTestError("KAT RSA sign/verify FAILED")


def _kat_ecdsa_sign():
    key = ec.generate_private_key(SECP384R1())
    data = b"KAT ECDSA test vector"
    sig = key.sign(data, ec.ECDSA(hashes.SHA256()))
    try:
        key.public_key().verify(sig, data, ec.ECDSA(hashes.SHA256()))
    except Exception:
        raise CryptoSelfTestError("KAT ECDSA sign/verify FAILED")


def run_kat():
    _kat_aes_gcm()
    _kat_hmac_sha256()
    _kat_sha256()
    _kat_hmac_drbg()
    _kat_rsa_sign()
    _kat_ecdsa_sign()
