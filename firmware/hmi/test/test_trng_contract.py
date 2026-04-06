#!/usr/bin/env python3
"""test_trng_contract.py — host-side pytest: postconditions из trng_hid.contract.yaml.

Тесты привязаны к фазам контракта:
  - fill_report: Report ID, размер, entropy, TSR-2
  - main_loop: streaming rate, USB reconnect
  - trng_init + startup_test: косвенно (если устройство отвечает — init OK)

Запуск:
  pytest test_trng_contract.py -v
  pytest test_trng_contract.py -v -k "not slow"
  pytest test_trng_contract.py -v --device-required  (skip если нет устройства)
"""
import pytest
import struct
import math
import time
from collections import Counter

try:
    import hid
    HID_AVAILABLE = True
except ImportError:
    HID_AVAILABLE = False

VID, PID = 0x0483, 0x5750
REPORT_SIZE = 64
USAGE_PAGE_VENDOR = 0xFF00


def find_device():
    if not HID_AVAILABLE:
        return None
    devs = hid.enumerate(VID, PID)
    return next((d for d in devs if d["usage_page"] == USAGE_PAGE_VENDOR), None)


def read_reports(n=10, timeout_ms=1000):
    info = find_device()
    if not info:
        pytest.skip("TRNG device not connected")
    dev = hid.device()
    dev.open_path(info["path"])
    dev.set_nonblocking(0)
    reports = []
    try:
        for _ in range(n):
            r = dev.read(REPORT_SIZE, timeout_ms=timeout_ms)
            reports.append(bytes(r))
    finally:
        dev.close()
    return reports


@pytest.fixture(scope="module")
def device_info():
    info = find_device()
    if not info:
        pytest.skip("TRNG device not connected")
    return info


@pytest.fixture(scope="module")
def reports():
    return read_reports(n=100)


# ═══════════════════════════════════════════════════════════════
# Phase: trng_init + startup_test (косвенные)
# ═══════════════════════════════════════════════════════════════

class TestTrngInit:
    """contract phase: trng_init — postcondition: RNG инициализирован."""

    def test_device_enumerated(self, device_info):
        """Если USB enumerated → trng_init + USBD_Init прошли."""
        assert device_info is not None
        assert device_info["vendor_id"] == VID
        assert device_info["product_id"] == PID

    def test_device_responds(self, reports):
        """Если reports приходят → startup_test пройден (иначе Error_Handler → hang)."""
        assert len(reports) > 0
        assert all(len(r) == REPORT_SIZE for r in reports)


# ═══════════════════════════════════════════════════════════════
# Phase: fill_report — postconditions
# ═══════════════════════════════════════════════════════════════

class TestFillReport:
    """contract phase: fill_report"""

    def test_report_size(self, reports):
        """postcondition: report = 64 bytes."""
        for i, r in enumerate(reports):
            assert len(r) == REPORT_SIZE, f"report #{i}: {len(r)} != {REPORT_SIZE}"

    def test_report_id(self, reports):
        """postcondition: report[0] == 0x01 (HID Report ID).
        GAP G10: текущий firmware НЕ ставит Report ID."""
        for i, r in enumerate(reports):
            assert r[0] == 0x01, f"report #{i}: report[0]={r[0]:#04x}, expected 0x01 (G10)"

    def test_no_all_zeros(self, reports):
        """invariant: ни один report не должен быть полностью нулевым."""
        for i, r in enumerate(reports):
            assert r != b"\x00" * REPORT_SIZE, f"report #{i}: all zeros"

    def test_no_all_ones(self, reports):
        """invariant: ни один report не должен быть 0xFF."""
        for i, r in enumerate(reports):
            assert r != b"\xff" * REPORT_SIZE, f"report #{i}: all 0xFF"

    def test_tsr2_no_consecutive_duplicates(self, reports):
        """postcondition TSR-2: consecutive reports must differ.
        GAP G6: текущий firmware НЕ проверяет повторы."""
        for i in range(len(reports) - 1):
            assert reports[i] != reports[i + 1], (
                f"TSR-2 fail: report #{i} == report #{i+1} (G6)"
            )

    def test_tsr2_no_duplicate_uint32(self, reports):
        """TSR-2 granular: consecutive uint32 values within report must differ."""
        for ri, r in enumerate(reports):
            payload = r[1:] if r[0] == 0x01 else r
            words = [struct.unpack_from("<I", payload, j)[0] for j in range(0, len(payload) - 3, 4)]
            for i in range(len(words) - 1):
                assert words[i] != words[i + 1], (
                    f"TSR-2 intra-report fail: report #{ri} word[{i}]=word[{i+1}]={words[i]:#010x}"
                )


# ═══════════════════════════════════════════════════════════════
# Phase: fill_report — entropy quality
# ═══════════════════════════════════════════════════════════════

class TestEntropy:
    """Entropy quality checks (NIST 800-90B inspired, simplified)."""

    def test_byte_distribution(self, reports):
        """Все 256 значений байт должны встречаться в 100 reports (6400 bytes)."""
        all_bytes = b"".join(reports)
        unique = len(set(all_bytes))
        assert unique >= 240, f"only {unique}/256 unique bytes — low entropy"

    def test_shannon_entropy(self, reports):
        """Shannon entropy >= 7.0 bits/byte (max = 8.0)."""
        all_bytes = b"".join(reports)
        n = len(all_bytes)
        freq = Counter(all_bytes)
        entropy = -sum((c / n) * math.log2(c / n) for c in freq.values())
        assert entropy >= 7.0, f"Shannon entropy = {entropy:.2f}, expected >= 7.0"

    def test_chi_squared(self, reports):
        """Chi-squared test: byte distribution не слишком далека от uniform."""
        all_bytes = b"".join(reports)
        n = len(all_bytes)
        expected = n / 256.0
        freq = Counter(all_bytes)
        chi2 = sum((freq.get(i, 0) - expected) ** 2 / expected for i in range(256))
        assert chi2 < 350, f"chi2 = {chi2:.1f}, expected < 350 (p < 0.01 threshold ~310)"

    def test_no_long_runs(self, reports):
        """Нет run > 32 одинаковых байт подряд."""
        all_bytes = b"".join(reports)
        max_run = 1
        cur_run = 1
        for i in range(1, len(all_bytes)):
            if all_bytes[i] == all_bytes[i - 1]:
                cur_run += 1
                max_run = max(max_run, cur_run)
            else:
                cur_run = 1
        assert max_run <= 32, f"longest run = {max_run} bytes"


# ═══════════════════════════════════════════════════════════════
# Phase: main_loop — streaming + rate
# ═══════════════════════════════════════════════════════════════

class TestMainLoop:
    """contract phase: main_loop"""

    @pytest.mark.slow
    def test_streaming_rate(self):
        """postcondition: reports приходят стабильно (>= 50 reports/sec)."""
        info = find_device()
        if not info:
            pytest.skip("device not connected")
        dev = hid.device()
        dev.open_path(info["path"])
        dev.set_nonblocking(0)
        n = 100
        t0 = time.monotonic()
        try:
            for _ in range(n):
                dev.read(REPORT_SIZE, timeout_ms=500)
        finally:
            dev.close()
        elapsed = time.monotonic() - t0
        rate = n / elapsed
        assert rate >= 50, f"streaming rate = {rate:.1f} reports/sec, expected >= 50"

    @pytest.mark.slow
    def test_no_timeout_in_burst(self):
        """invariant: 1000 consecutive reads без timeout."""
        info = find_device()
        if not info:
            pytest.skip("device not connected")
        dev = hid.device()
        dev.open_path(info["path"])
        dev.set_nonblocking(0)
        try:
            for i in range(1000):
                r = dev.read(REPORT_SIZE, timeout_ms=1000)
                assert len(r) == REPORT_SIZE, f"timeout/short at read #{i}"
        finally:
            dev.close()
