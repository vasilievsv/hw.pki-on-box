import os
import sys
import time
import hashlib


class TRNGDeviceError(Exception):
    pass


class SoftwareTRNG:
    def __init__(self, cfg: dict = None):
        hc = (cfg or {}).get("health_check", {})
        self._bit_ratio_min = hc.get("bit_ratio_min", 0.40)
        self._bit_ratio_max = hc.get("bit_ratio_max", 0.60)
        self._chi_square_max = hc.get("chi_square_max", 310.0)

    def get_entropy(self, n: int) -> bytes:
        buf = bytearray()
        while len(buf) < n:
            sources = [
                os.urandom(n),
                hashlib.sha256(str(int(time.time() * 1e9)).encode()).digest(),
                hashlib.sha256((str(os.getpid()) + str(os.getppid())).encode()).digest(),
            ]
            combined = b"".join(sources)
            buf.extend(hashlib.sha512(combined).digest())
        return bytes(buf[:n])

    def health_check(self, data: bytes = None) -> bool:
        sample = data if data is not None else self.get_entropy(2048)
        if len(sample) < 8:
            return False
        ones = sum(bin(b).count("1") for b in sample)
        ratio = ones / (len(sample) * 8)
        if not (self._bit_ratio_min <= ratio <= self._bit_ratio_max):
            return False
        if len(sample) >= 512:
            counts = [0] * 256
            for b in sample:
                counts[b] += 1
            expected = len(sample) / 256.0
            chi2 = sum((c - expected) ** 2 / expected for c in counts)
            if chi2 > self._chi_square_max:
                return False
        return True


class HardwareTRNG:
    def __init__(self, cfg: dict = None):
        cfg = cfg or {}
        trng_cfg = cfg.get("trng", {})
        self._mode = trng_cfg.get("mode", "auto")
        self._vid = int(trng_cfg.get("hid_vid", "0x0483"), 16)
        self._pid = int(trng_cfg.get("hid_pid", "0x5750"), 16)
        self._sw = SoftwareTRNG(cfg)

        if self._mode == "hardware" and not self.is_hardware_available():
            raise TRNGDeviceError(
                f"Hardware TRNG not found (VID={self._vid:#06x} PID={self._pid:#06x})"
            )

    def is_hardware_available(self) -> bool:
        try:
            if sys.platform == "win32":
                import hid
                devs = hid.enumerate(self._vid, self._pid)
                return len(devs) > 0
            else:
                import hid
                devs = hid.enumerate(self._vid, self._pid)
                return len(devs) > 0
        except Exception:
            return False

    def get_entropy(self, n: int) -> bytes:
        if self._mode == "software":
            return self._sw.get_entropy(n)

        if self._mode == "auto" and not self.is_hardware_available():
            return self._sw.get_entropy(n)

        return self._read_hid(n)

    def _read_hid(self, n: int) -> bytes:
        import hid
        dev = hid.device()
        dev.open(self._vid, self._pid)
        try:
            dev.set_nonblocking(1)
            buf = bytearray()
            while len(buf) < n:
                chunk = dev.read(64)
                if not chunk:
                    continue
                # Windows prepends report_id (0x00), Linux does not
                data = bytes(chunk[1:] if sys.platform == "win32" else chunk)
                buf.extend(data)
            return bytes(buf[:n])
        finally:
            dev.close()

    def health_check(self, data: bytes = None) -> bool:
        return self._sw.health_check(data)
