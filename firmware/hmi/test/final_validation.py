#!/usr/bin/env python3
"""final_validation.py — standalone contract tests via /dev/hidraw0.
No dependencies (no hid, no pytest). Python 3.6+.
SESSION_52: HID descriptor fix + G10 report_id fix validation.
"""
import os
import sys
import struct
import math
import time
from collections import Counter

DEVICE = "/dev/hidraw0"
REPORT_SIZE = 64
N_REPORTS = 100
N_STRESS = 1000

passed = 0
failed = 0
xfail = 0
results = []

def report(name, ok, msg="", is_xfail=False):
    global passed, failed, xfail
    if ok:
        passed += 1
        results.append(("PASS", name, msg))
    elif is_xfail:
        xfail += 1
        results.append(("XFAIL", name, msg))
    else:
        failed += 1
        results.append(("FAIL", name, msg))

def read_reports(fd, n):
    reports = []
    for _ in range(n):
        data = os.read(fd, REPORT_SIZE)
        if len(data) != REPORT_SIZE:
            return reports
        reports.append(data)
    return reports

def main():
    if not os.path.exists(DEVICE):
        print("ERROR: {} not found".format(DEVICE))
        sys.exit(1)

    fd = os.open(DEVICE, os.O_RDONLY)

    try:
        print("=== FINAL VALIDATION: SESSION_52 ===")
        print("Device: {}".format(DEVICE))
        print("Reading {} reports...".format(N_REPORTS))
        reports = read_reports(fd, N_REPORTS)
        report("G1_device_responds", len(reports) == N_REPORTS,
               "{}/{}".format(len(reports), N_REPORTS))

        report("G2_report_size", all(len(r) == REPORT_SIZE for r in reports),
               "all {} bytes".format(REPORT_SIZE))

        byte0_vals = set(r[0] for r in reports)
        report("G10_no_report_id_bias", len(byte0_vals) > 1,
               "unique byte[0]: {}".format(len(byte0_vals)))

        report("G3_no_all_zeros", all(r != b"\x00" * REPORT_SIZE for r in reports))
        report("G3_no_all_ones", all(r != b"\xff" * REPORT_SIZE for r in reports))

        dup_found = False
        for i in range(len(reports) - 1):
            if reports[i] == reports[i + 1]:
                dup_found = True
                break
        report("G6_tsr2_no_consecutive_dup", not dup_found)

        intra_dup = False
        for ri, r in enumerate(reports):
            words = [struct.unpack_from("<I", r, j)[0] for j in range(0, REPORT_SIZE - 3, 4)]
            for i in range(len(words) - 1):
                if words[i] == words[i + 1]:
                    intra_dup = True
                    break
            if intra_dup:
                break
        report("G6_tsr2_no_intra_dup_uint32", not intra_dup)

        all_bytes = b"".join(reports)
        unique_bytes = len(set(all_bytes))
        report("G7_byte_distribution", unique_bytes >= 240,
               "{}/256 unique".format(unique_bytes))

        n = len(all_bytes)
        freq = Counter(all_bytes)
        entropy = -sum((c / n) * math.log2(c / n) for c in freq.values())
        report("G7_shannon_entropy", entropy >= 7.0,
               "{:.3f} bits/byte".format(entropy))

        expected = n / 256.0
        chi2 = sum((freq.get(i, 0) - expected) ** 2 / expected for i in range(256))
        report("G7_chi_squared", chi2 < 350,
               "chi2={:.1f} (limit 350)".format(chi2))

        ones = sum(bin(b).count("1") for b in all_bytes)
        ratio = ones / (n * 8)
        report("G7_bit_ratio", 0.45 <= ratio <= 0.55,
               "{:.4f}".format(ratio))

        max_run = 1
        cur_run = 1
        for i in range(1, len(all_bytes)):
            if all_bytes[i] == all_bytes[i - 1]:
                cur_run += 1
                if cur_run > max_run:
                    max_run = cur_run
            else:
                cur_run = 1
        report("G7_no_long_runs", max_run <= 32,
               "max_run={}".format(max_run))

        print("\n--- Streaming rate ---")
        t0 = time.monotonic()
        rate_reports = read_reports(fd, N_REPORTS)
        elapsed = time.monotonic() - t0
        rate = len(rate_reports) / elapsed if elapsed > 0 else 0
        throughput = (len(rate_reports) * REPORT_SIZE) / elapsed / 1024 if elapsed > 0 else 0
        report("G8_streaming_rate", rate >= 50,
               "{:.0f} reports/sec".format(rate))
        report("G8_throughput", throughput >= 3.0,
               "{:.1f} KB/s".format(throughput))

        print("\n--- Stress test ({} reads) ---".format(N_STRESS))
        t0 = time.monotonic()
        stress_ok = True
        for i in range(N_STRESS):
            data = os.read(fd, REPORT_SIZE)
            if len(data) != REPORT_SIZE:
                stress_ok = False
                break
        stress_elapsed = time.monotonic() - t0
        stress_rate = N_STRESS / stress_elapsed if stress_elapsed > 0 else 0
        stress_kb = (N_STRESS * REPORT_SIZE) / stress_elapsed / 1024 if stress_elapsed > 0 else 0
        report("G9_stress_1000_reads", stress_ok,
               "{:.0f} reports/sec, {:.1f} KB/s, {:.1f}s".format(
                   stress_rate, stress_kb, stress_elapsed))

    finally:
        os.close(fd)

    print("\n=== RESULTS ===")
    for status, name, msg in results:
        line = "  {} {}".format(status, name)
        if msg:
            line += " : {}".format(msg)
        print(line)

    total = passed + failed + xfail
    print("\n{}/{} passed, {} failed, {} xfail".format(passed, total, failed, xfail))

    if failed > 0:
        sys.exit(1)
    print("\nALL PASSED")

if __name__ == "__main__":
    main()
