from .config import load_config
from .trng import HardwareTRNG, SoftwareTRNG, TRNGDeviceError
from .drbg import NISTDRBG
from .crypto_engine import CryptoEngine
from .key_storage import KeyStorage
from .self_tests import run_kat, CryptoSelfTestError


def build_core(cfg: dict = None):
    """
    Фабрика Core-цепочки: HardwareTRNG → NISTDRBG → CryptoEngine → KeyStorage.

    Returns:
        (trng, drbg, crypto, storage)
    """
    if cfg is None:
        cfg = load_config()

    run_kat()

    trng = HardwareTRNG(cfg)
    drbg = NISTDRBG(trng, cfg)
    drbg.instantiate(
        personalization=cfg.get("drbg", {}).get("personalization", "").encode()
    )
    crypto = CryptoEngine(drbg, cfg)
    storage = KeyStorage(cfg)

    return trng, drbg, crypto, storage


__all__ = [
    "build_core",
    "load_config",
    "HardwareTRNG",
    "SoftwareTRNG",
    "TRNGDeviceError",
    "NISTDRBG",
    "CryptoEngine",
    "KeyStorage",
    "run_kat",
    "CryptoSelfTestError",
]
