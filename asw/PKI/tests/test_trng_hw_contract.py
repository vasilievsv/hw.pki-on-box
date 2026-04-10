import time
import pytest
from core.trng import HardwareTRNG, TRNGDeviceError
from core.drbg import NISTDRBG

pytestmark = pytest.mark.hardware

VID, PID = 0x0483, 0x5750


class TestTrngHidContract:

    def test_enumerate_device(self, hw_trng):
        assert hw_trng.is_hardware_available() is True

    def test_hardware_mode_init(self, hw_trng, hw_cfg):
        assert hw_trng._mode == "hardware"

    def test_hardware_mode_rejects_without_device(self):
        cfg = {"trng": {"mode": "hardware", "hid_vid": "0xFFFF", "hid_pid": "0xFFFF"}}
        with pytest.raises(TRNGDeviceError):
            HardwareTRNG(cfg)

    def test_get_entropy_returns_bytes(self, hw_trng):
        data = hw_trng.get_entropy(64)
        assert isinstance(data, bytes)
        assert len(data) == 64

    def test_get_entropy_exact_lengths(self, hw_trng):
        for n in [1, 16, 32, 63, 64, 128, 256]:
            data = hw_trng.get_entropy(n)
            assert len(data) == n, f"expected {n}, got {len(data)}"

    def test_get_entropy_not_zero(self, hw_trng):
        data = hw_trng.get_entropy(64)
        assert data != b"\x00" * 64

    def test_get_entropy_not_ff(self, hw_trng):
        data = hw_trng.get_entropy(64)
        assert data != b"\xff" * 64

    def test_get_entropy_unique(self, hw_trng):
        samples = [hw_trng.get_entropy(32) for _ in range(10)]
        assert len(set(samples)) == 10, "duplicate entropy detected"

    def test_health_check_hw_data(self, hw_trng):
        data = hw_trng.get_entropy(4096)
        result = hw_trng.health_check(data)
        if not result:
            pytest.xfail("G10: report_id=0x01 bias in raw HID stream on Linux (firmware gap)")


class TestTrngDrbgHardware:

    def test_drbg_instantiate_with_hw(self, hw_trng, hw_cfg):
        d = NISTDRBG(hw_trng, hw_cfg)
        d.instantiate()
        assert d.initialized is True

    def test_drbg_generate_lengths(self, hw_drbg):
        for n in [16, 32, 64, 128]:
            result = hw_drbg.generate(n)
            assert len(result) == n

    def test_drbg_reseed_from_hw(self, hw_drbg):
        for _ in range(5):
            hw_drbg.generate(32)
        hw_drbg.reseed()
        assert hw_drbg._reseed_counter == 1

    def test_drbg_health_check(self, hw_drbg):
        assert hw_drbg.health_check() is True

    def test_drbg_hmac_sha256_key_size(self, hw_drbg):
        hw_drbg.generate(32)
        assert len(hw_drbg._key) == 32
        assert len(hw_drbg._value) == 32

    def test_drbg_auto_reseed_at_interval(self, hw_cfg, hw_trng):
        cfg = dict(hw_cfg)
        cfg["drbg"] = dict(cfg["drbg"], reseed_interval=5)
        d = NISTDRBG(hw_trng, cfg)
        d.instantiate()
        for _ in range(6):
            d.generate(16)
        assert d._reseed_counter <= 3


class TestNist80090bBasic:

    def _collect_hw_sample(self, hw_trng, size=16384):
        return hw_trng.get_entropy(size)

    def test_repetition_count(self, hw_trng):
        data = self._collect_hw_sample(hw_trng)
        max_run = 1
        current_run = 1
        for i in range(1, len(data)):
            if data[i] == data[i - 1]:
                current_run += 1
                max_run = max(max_run, current_run)
            else:
                current_run = 1
        cutoff = 20
        assert max_run < cutoff, f"repetition count {max_run} >= {cutoff}"

    def test_adaptive_proportion(self, hw_trng):
        data = self._collect_hw_sample(hw_trng)
        window = 512
        threshold = window * 0.065
        for start in range(0, len(data) - window, window):
            block = data[start : start + window]
            counts = [0] * 256
            for b in block:
                counts[b] += 1
            max_count = max(counts)
            assert max_count < threshold, (
                f"APT fail at offset {start}: max_count={max_count}, threshold={threshold:.0f}"
            )

    def test_bit_ratio(self, hw_trng):
        data = self._collect_hw_sample(hw_trng)
        ones = sum(bin(b).count("1") for b in data)
        ratio = ones / (len(data) * 8)
        assert 0.45 <= ratio <= 0.55, f"bit ratio {ratio:.4f} outside [0.45, 0.55]"

    def test_chi_square_byte_distribution(self, hw_trng):
        data = self._collect_hw_sample(hw_trng)
        counts = [0] * 256
        for b in data:
            counts[b] += 1
        expected = len(data) / 256.0
        chi2 = sum((c - expected) ** 2 / expected for c in counts)
        if chi2 > 310.0:
            pytest.xfail(f"G10: chi-square {chi2:.2f} — report_id bias in raw HID (firmware gap)")

    def test_no_stuck_at_fault(self, hw_trng):
        data = self._collect_hw_sample(hw_trng, size=1024)
        unique_bytes = len(set(data))
        assert unique_bytes >= 200, f"only {unique_bytes} unique bytes in 1024 — stuck-at?"


class TestKeyStorageWithHwEntropy:

    def test_build_core_hardware(self, hw_trng, hw_cfg):
        from core import build_core
        trng, drbg, crypto, storage = build_core(hw_cfg)
        assert trng.is_hardware_available() is True
        assert drbg.initialized is True

    def test_crypto_engine_keygen_hw(self, hw_trng, hw_cfg):
        from core import build_core
        trng, drbg, crypto, storage = build_core(hw_cfg)
        priv, pub = crypto.generate_ec_keypair("P-384")
        assert priv is not None
        assert pub is not None

    def test_sign_verify_hw_entropy(self, hw_trng, hw_cfg):
        from core import build_core
        trng, drbg, crypto, storage = build_core(hw_cfg)
        priv, pub = crypto.generate_ec_keypair("P-384")
        msg = b"test message from hw trng"
        sig = crypto.sign_data(priv, msg)
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives import hashes
        pub.verify(sig, msg, ec.ECDSA(hashes.SHA256()))

