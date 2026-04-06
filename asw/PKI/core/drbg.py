import hmac
import hashlib

from .trng import HardwareTRNG


class NISTDRBG:
    """HMAC_DRBG по NIST SP 800-90A"""

    def __init__(self, trng: HardwareTRNG, cfg: dict = None):
        self._trng = trng
        self._reseed_interval = (cfg or {}).get("drbg", {}).get("reseed_interval", 1000)
        self._key = None
        self._value = None
        self._reseed_counter = 0
        self.initialized = False

    # ── internal HMAC-SHA256 update ──────────────────────────────────────────

    def _update(self, provided: bytes = b"") -> None:
        def H(k, v):
            return hmac.new(k, v, hashlib.sha256).digest()

        self._key = H(self._key, self._value + b"\x00" + provided)
        self._value = H(self._key, self._value)
        if provided:
            self._key = H(self._key, self._value + b"\x01" + provided)
            self._value = H(self._key, self._value)

    # ── public API ───────────────────────────────────────────────────────────

    def instantiate(self, personalization: bytes = b"") -> None:
        entropy = self._trng.get_entropy(32)
        seed = entropy + personalization
        self._key = b"\x00" * 32
        self._value = b"\x01" * 32
        self._update(seed)
        self._reseed_counter = 1
        self.initialized = True

    def reseed(self, additional: bytes = b"") -> None:
        entropy = self._trng.get_entropy(32)
        self._update(entropy + additional)
        self._reseed_counter = 1

    def generate(self, n: int, additional: bytes = b"") -> bytes:
        if not self.initialized:
            raise RuntimeError("DRBG not initialized — call instantiate() first")

        if self._reseed_counter >= self._reseed_interval:
            self.reseed(additional)
            additional = b""

        if additional:
            self._update(additional)

        result = b""
        while len(result) < n:
            self._value = hmac.new(self._key, self._value, hashlib.sha256).digest()
            result += self._value

        self._update(additional)
        self._reseed_counter += 1
        return result[:n]

    def health_check(self, data: bytes = None) -> bool:
        sample = data if data is not None else self.generate(2048)
        if len(sample) < 8:
            return False

        ones = sum(bin(b).count("1") for b in sample)
        ratio = ones / (len(sample) * 8)
        if not (0.40 <= ratio <= 0.60):
            return False

        counts = [0] * 256
        for b in sample:
            counts[b] += 1
        expected = len(sample) / 256.0
        chi2 = sum((c - expected) ** 2 / expected for c in counts)
        return chi2 <= 310.0
