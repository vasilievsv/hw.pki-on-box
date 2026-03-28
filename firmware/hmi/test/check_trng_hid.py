#!/usr/bin/env python3
"""check_trng_hid.py — smoke test WeAct G474CEU TRNG HID streamer (TASK-3,5)"""
import sys
import hid

VID, PID    = 0x0483, 0x5750
REPORT_SIZE = 64
N_REPORTS   = 10

def find_device():
    devs = hid.enumerate(VID, PID)
    return next((d for d in devs if d['usage_page'] == 0xFF00), None)

def test_enumeration():
    d = find_device()
    if not d:
        print(f"[FAIL] enumeration: {VID:04X}:{PID:04X} not found")
        return False
    print(f"[PASS] enumeration: {d['manufacturer_string']} | {d['product_string']}")
    return True

def test_reports():
    d = find_device()
    if not d:
        print("[SKIP] reports: device not found")
        return False, []
    dev = hid.device()
    dev.open_path(d['path'])
    dev.set_nonblocking(0)
    reports = []
    try:
        for i in range(N_REPORTS):
            r = dev.read(REPORT_SIZE, timeout_ms=1000)
            if len(r) != REPORT_SIZE:
                print(f"[FAIL] reports: short report #{i}: {len(r)} bytes")
                return False, []
            reports.append(bytes(r))
    finally:
        dev.close()
    print(f"[PASS] reports: {N_REPORTS} x {REPORT_SIZE} bytes received")
    return True, reports

def test_entropy(reports):
    all_bytes = b''.join(reports)
    unique = len(set(all_bytes))
    if unique <= 200:
        print(f"[FAIL] entropy: only {unique}/256 unique byte values")
        return False
    print(f"[PASS] entropy: {unique}/256 unique byte values")
    return True

def test_no_repeats(reports):
    for i in range(len(reports) - 1):
        if reports[i] == reports[i+1]:
            print(f"[FAIL] no_repeats: report #{i} == report #{i+1}")
            return False
    print(f"[PASS] no_repeats: all {N_REPORTS} reports differ")
    return True

if __name__ == '__main__':
    ok = True
    ok &= test_enumeration()
    passed, reports = test_reports()
    ok &= passed
    if reports:
        ok &= test_entropy(reports)
        ok &= test_no_repeats(reports)
    print(f"\n{'[PASS] TASK-3,5 TRNG HID OK' if ok else '[FAIL] TASK-3,5 FAILED'}")
    sys.exit(0 if ok else 1)
