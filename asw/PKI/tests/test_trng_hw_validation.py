#!/usr/bin/env python3
import sys
import os
import time
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

RESULTS = {}

def test_1_enumerate():
    print("\n=== TEST 1: hid.enumerate ===")
    try:
        import hid
        devs = hid.enumerate(0x0483, 0x5750)
        RESULTS["enumerate"] = {"found": len(devs), "devices": []}
        for d in devs:
            info = {
                "manufacturer": d.get("manufacturer_string", ""),
                "product": d.get("product_string", ""),
                "path": d.get("path", b"").decode() if isinstance(d.get("path"), bytes) else str(d.get("path", "")),
                "interface": d.get("interface_number", -1),
            }
            RESULTS["enumerate"]["devices"].append(info)
            print(f"  VID:PID = 0x0483:0x5750")
            print(f"  Product: {info['product']}")
            print(f"  Path: {info['path']}")
        if devs:
            print(f"  PASS: {len(devs)} device(s)")
            return True
        else:
            print("  FAIL: no devices")
            return False
    except Exception as e:
        RESULTS["enumerate"] = {"error": str(e)}
        print(f"  FAIL: {e}")
        return False

def test_2_hid_read():
    print("\n=== TEST 2: hid.read ===")
    try:
        import hid
        dev = hid.device()
        dev.open(0x0483, 0x5750)
        dev.set_nonblocking(0)
        raw = dev.read(64, 2000)
        dev.close()
        if raw:
            data = bytes(raw)
            RESULTS["hid_read"] = {"length": len(data), "hex_preview": data[:16].hex()}
            print(f"  Got {len(data)} bytes")
            print(f"  Preview: {data[:16].hex()}")
            print("  PASS")
            return data
        else:
            RESULTS["hid_read"] = {"error": "empty read"}
            print("  FAIL: empty read (timeout?)")
            return None
    except Exception as e:
        RESULTS["hid_read"] = {"error": str(e)}
        print(f"  FAIL: {e}")
        return None

def test_3_raw_hidraw():
    print("\n=== TEST 3: raw /dev/hidraw0 ===")
    hidraw = "/dev/hidraw0"
    if not os.path.exists(hidraw):
        RESULTS["raw_hidraw"] = {"error": "not found"}
        print(f"  SKIP: {hidraw} not found")
        return None
    try:
        fd = os.open(hidraw, os.O_RDONLY | os.O_NONBLOCK)
        time.sleep(0.1)
        try:
            data = os.read(fd, 64)
        except BlockingIOError:
            os.close(fd)
            fd = os.open(hidraw, os.O_RDONLY)
            data = os.read(fd, 64)
        os.close(fd)
        RESULTS["raw_hidraw"] = {"length": len(data), "hex_preview": data[:16].hex()}
        print(f"  Got {len(data)} bytes")
        print(f"  Preview: {data[:16].hex()}")
        print("  PASS")
        return data
    except Exception as e:
        RESULTS["raw_hidraw"] = {"error": str(e)}
        print(f"  FAIL: {e}")
        return None

def test_4_health_check():
    print("\n=== TEST 4: health_check on HW data ===")
    try:
        import hid
        dev = hid.device()
        dev.open(0x0483, 0x5750)
        dev.set_nonblocking(0)
        buf = bytearray()
        reads = 0
        while len(buf) < 8192 and reads < 200:
            chunk = dev.read(64, 2000)
            if chunk:
                buf.extend(bytes(chunk)[1:])
            reads += 1
        dev.close()
        sample = bytes(buf[:8192])
        print(f"  Collected {len(sample)} bytes in {reads} reads")

        ones = sum(bin(b).count("1") for b in sample)
        ratio = ones / (len(sample) * 8)
        counts = [0] * 256
        for b in sample:
            counts[b] += 1
        expected = len(sample) / 256.0
        chi2 = sum((c - expected) ** 2 / expected for c in counts)

        passed = (0.40 <= ratio <= 0.60) and (chi2 <= 310.0)
        RESULTS["health_check"] = {
            "sample_bytes": len(sample),
            "bit_ratio": round(ratio, 4),
            "chi_square": round(chi2, 2),
            "pass": passed,
        }
        print(f"  Bit ratio: {ratio:.4f} (0.40-0.60)")
        print(f"  Chi-square: {chi2:.2f} (<=310.0)")
        print(f"  {'PASS' if passed else 'FAIL'}")
        return passed
    except Exception as e:
        RESULTS["health_check"] = {"error": str(e)}
        print(f"  FAIL: {e}")
        return False

def test_5_speed():
    print("\n=== TEST 5: speed benchmark ===")
    try:
        import hid
        dev = hid.device()
        dev.open(0x0483, 0x5750)
        dev.set_nonblocking(0)
        total_bytes = 0
        iterations = 10
        target_per_iter = 1024
        t0 = time.time()
        for _ in range(iterations):
            got = 0
            while got < target_per_iter:
                chunk = dev.read(64, 2000)
                if chunk:
                    got += len(chunk)
            total_bytes += got
        elapsed = time.time() - t0
        dev.close()
        bps = total_bytes / elapsed if elapsed > 0 else 0
        RESULTS["speed_hw"] = {
            "total_bytes": total_bytes,
            "elapsed_sec": round(elapsed, 3),
            "bytes_per_sec": round(bps, 1),
        }
        print(f"  {total_bytes} bytes in {elapsed:.3f}s = {bps:.1f} B/s")

        from core.trng import SoftwareTRNG
        sw = SoftwareTRNG()
        t0 = time.time()
        for _ in range(iterations):
            sw.get_entropy(target_per_iter)
        elapsed_sw = time.time() - t0
        bps_sw = (iterations * target_per_iter) / elapsed_sw if elapsed_sw > 0 else 0
        RESULTS["speed_sw"] = {
            "total_bytes": iterations * target_per_iter,
            "elapsed_sec": round(elapsed_sw, 3),
            "bytes_per_sec": round(bps_sw, 1),
        }
        print(f"  SW: {iterations * target_per_iter} bytes in {elapsed_sw:.3f}s = {bps_sw:.1f} B/s")

        reseed_ok = bps >= 32
        RESULTS["drbg_reseed_feasible"] = reseed_ok
        print(f"  DRBG reseed (32B/1000gen): {'OK' if reseed_ok else 'TOO SLOW'} ({bps:.0f} B/s)")
        print(f"  PASS")
        return True
    except Exception as e:
        RESULTS["speed_hw"] = {"error": str(e)}
        print(f"  FAIL: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("TRNG HID Validation — PKI-007.4")
    print("=" * 50)

    r1 = test_1_enumerate()
    r2 = test_2_hid_read() if r1 else None
    r3 = test_3_raw_hidraw()
    r4 = test_4_health_check() if r1 else False
    r5 = test_5_speed() if r1 else False

    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    checks = [
        ("enumerate", r1),
        ("hid_read", r2 is not None),
        ("raw_hidraw", r3 is not None),
        ("health_check", r4),
        ("speed", r5),
    ]
    for name, ok in checks:
        print(f"  {'PASS' if ok else 'FAIL/SKIP':10s} {name}")

    print(f"\nJSON results:")
    print(json.dumps(RESULTS, indent=2, default=str))
