import pytest
from core.trng import HardwareTRNG, SoftwareTRNG, TRNGDeviceError
from core.drbg import NISTDRBG


@pytest.fixture
def sw_cfg():
    return {
        "trng": {"mode": "software"},
        "drbg": {"algorithm": "hmac-sha256", "reseed_interval": 1000, "personalization": ""},
    }


@pytest.fixture
def trng(sw_cfg):
    return HardwareTRNG(sw_cfg)


@pytest.fixture
def drbg(trng, sw_cfg):
    d = NISTDRBG(trng, sw_cfg)
    d.instantiate()
    return d


class TestTrngDrbgPreconditions:

    def test_rejects_hardware_mode_no_device(self):
        cfg = {"trng": {"mode": "hardware"}}
        with pytest.raises(TRNGDeviceError, match="Hardware TRNG not found"):
            HardwareTRNG(cfg)

    def test_rejects_generate_before_instantiate(self, trng, sw_cfg):
        d = NISTDRBG(trng, sw_cfg)
        with pytest.raises(RuntimeError, match="not initialized"):
            d.generate(32)


class TestTrngDrbgPostconditions:

    def test_generate_correct_length(self, drbg):
        for length in [16, 32, 64, 128]:
            result = drbg.generate(length)
            assert len(result) == length

    def test_reseed_resets_counter(self, drbg):
        for _ in range(5):
            drbg.generate(32)
        assert drbg._reseed_counter > 1
        drbg.reseed()
        assert drbg._reseed_counter == 1


class TestTrngDrbgInvariants:

    def test_drbg_uses_hmac_sha256(self, drbg):
        sample = drbg.generate(32)
        assert len(sample) == 32
        assert drbg._key is not None and len(drbg._key) == 32
        assert drbg._value is not None and len(drbg._value) == 32

    def test_reseed_interval_bounded(self, drbg):
        assert drbg._reseed_interval <= 2**48

    def test_software_fallback_works_without_hardware(self, trng, drbg):
        assert trng.is_hardware_available() is False
        result = drbg.generate(32)
        assert result is not None and len(result) == 32

    def test_trng_entropy_health_check(self, trng):
        assert trng.health_check() is True

    def test_drbg_health_check(self, drbg):
        assert drbg.health_check() is True
