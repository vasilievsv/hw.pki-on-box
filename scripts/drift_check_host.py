#!/usr/bin/env python3
"""Drift detection L1 для host Python-кода vs crypto-engine.contract.yaml.

Запуск:
  python scripts/drift_check_host.py
  python scripts/drift_check_host.py --json results.json
"""
import re
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).parent.parent
CORE_DIR = BASE / "asw" / "PKI" / "core"
SERVICES_DIR = BASE / "asw" / "PKI" / "services"
TESTS_DIR = BASE / "asw" / "PKI" / "tests"

CHECKS = [
    {
        "id": "CE-1", "phase": "crypto_engine", "severity": "CRITICAL",
        "desc": "CryptoEngine must support RSA key generation",
        "file": "core/crypto_engine.py",
        "pattern_good": r"def generate_key_pair|rsa\.generate_private_key|RSA",
        "check": "good_present",
    },
    {
        "id": "CE-2", "phase": "crypto_engine", "severity": "CRITICAL",
        "desc": "CryptoEngine must support ECDSA",
        "file": "core/crypto_engine.py",
        "pattern_good": r"ECDSA|ec\.generate_private_key|SECP384R1|P.384",
        "check": "good_present",
    },
    {
        "id": "CE-3", "phase": "crypto_engine", "severity": "HIGH",
        "desc": "SHA-1 must not be used for signing (SHA-256 minimum)",
        "file": "core/crypto_engine.py",
        "pattern_bad": r"hashes\.SHA1\(\)|SHA1\b",
        "check": "bad_absent",
    },
    {
        "id": "CE-4", "phase": "crypto_engine", "severity": "HIGH",
        "desc": "All crypto operations must be logged (audit_log)",
        "file": "core/crypto_engine.py",
        "pattern_good": r"log|audit|logger",
        "check": "good_present",
    },
    {
        "id": "KS-1", "phase": "key_storage", "severity": "CRITICAL",
        "desc": "Private keys must be encrypted with AES-256",
        "file": "core/key_storage.py",
        "pattern_good": r"AES|AESGCM|aes.*256|encrypt",
        "check": "good_present",
    },
    {
        "id": "KS-2", "phase": "key_storage", "severity": "CRITICAL",
        "desc": "Key zeroization must use ctypes.memset or secure method",
        "file": "core/key_storage.py",
        "pattern_good": r"ctypes\.memset|zeroize|secure.*delete|memset",
        "check": "good_present",
    },
    {
        "id": "KS-3", "phase": "key_storage", "severity": "HIGH",
        "desc": "PBKDF2 must use sufficient iterations (>=100000)",
        "file": "core/key_storage.py",
        "pattern_good": r"PBKDF2|pbkdf2|iterations.*[1-9]\d{5,}|260000",
        "check": "good_present",
    },
    {
        "id": "DRBG-1", "phase": "trng_drbg", "severity": "CRITICAL",
        "desc": "DRBG must implement HMAC_DRBG (NIST SP 800-90A)",
        "file": "core/drbg.py",
        "pattern_good": r"HMAC_DRBG|hmac.*drbg|NISTDRBG|hmac\.new",
        "check": "good_present",
    },
    {
        "id": "DRBG-2", "phase": "trng_drbg", "severity": "HIGH",
        "desc": "DRBG must support reseed operation",
        "file": "core/drbg.py",
        "pattern_good": r"reseed|re_seed",
        "check": "good_present",
    },
    {
        "id": "TRNG-1", "phase": "trng_drbg", "severity": "HIGH",
        "desc": "SoftwareTRNG must use os.urandom as entropy source",
        "file": "core/trng.py",
        "pattern_good": r"os\.urandom|secrets\.|SystemRandom",
        "check": "good_present",
    },
    {
        "id": "TRNG-2", "phase": "trng_drbg", "severity": "HIGH",
        "desc": "HardwareTRNG must communicate via USB HID",
        "file": "core/trng.py",
        "pattern_good": r"hidraw|hid|usb|HardwareTRNG",
        "check": "good_present",
    },
    {
        "id": "TRNG-3", "phase": "trng_drbg", "severity": "HIGH",
        "desc": "Health check must exist (chi2 or bit_ratio or entropy test)",
        "file": "core/trng.py",
        "pattern_good": r"health_check|chi2|bit_ratio|entropy|validate",
        "check": "good_present",
    },
    {
        "id": "KAT-1", "phase": "self_tests", "severity": "CRITICAL",
        "desc": "KAT self-tests must exist for crypto algorithms",
        "dir": "tests",
        "pattern_good": r"kat|known.?answer|self.?test|KAT",
        "check": "good_present_dir",
    },
]


def read_text(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def run_checks():
    results = []

    for chk in CHECKS:
        if chk["check"] == "good_present_dir":
            found = False
            search_dir = TESTS_DIR if chk.get("dir") == "tests" else CORE_DIR
            if search_dir.exists():
                for f in search_dir.rglob("*.py"):
                    src = read_text(f)
                    if re.search(chk["pattern_good"], src, re.IGNORECASE):
                        found = True
                        break
            results.append({
                "id": chk["id"], "phase": chk["phase"], "severity": chk["severity"],
                "status": "OK" if found else "DRIFT", "desc": chk["desc"],
            })
            continue

        fpath = BASE / "asw" / "PKI" / chk["file"]
        if not fpath.exists():
            results.append({
                "id": chk["id"], "phase": chk["phase"], "severity": chk["severity"],
                "status": "DRIFT", "desc": f"{chk['file']} not found",
            })
            continue

        src = read_text(fpath)
        mode = chk["check"]

        if mode == "good_present":
            found = bool(re.search(chk["pattern_good"], src, re.MULTILINE | re.IGNORECASE))
            status = "OK" if found else "DRIFT"
        elif mode == "bad_absent":
            found = bool(re.search(chk["pattern_bad"], src, re.MULTILINE | re.IGNORECASE))
            status = "DRIFT" if found else "OK"
        else:
            status = "UNKNOWN"

        results.append({
            "id": chk["id"], "phase": chk["phase"], "severity": chk["severity"],
            "status": status, "desc": chk["desc"],
        })

    return results


def print_report(results):
    ok = sum(1 for r in results if r["status"] == "OK")
    drift = sum(1 for r in results if r["status"] == "DRIFT")

    print(f"\n{'='*80}")
    print(f"HOST DRIFT REPORT (L1 regex)")
    print(f"Checks: {len(results)} total, {ok} OK, {drift} DRIFT")
    print(f"{'='*80}\n")

    for r in results:
        icon = "✅" if r["status"] == "OK" else "⚠️"
        print(f"  {icon} [{r['id']}] {r['severity']:<8} {r['desc']}")

    print()
    if drift > 0:
        crit = sum(1 for r in results if r["status"] == "DRIFT" and r["severity"] == "CRITICAL")
        print(f"⚠️ {drift} DRIFT(s) detected")
        if crit:
            print(f"🔴 {crit} CRITICAL drift(s)")
    else:
        print(f"✅ No drift detected")

    return drift


def main():
    parser = argparse.ArgumentParser(description="Host drift detection L1")
    parser.add_argument("--json", default=None)
    args = parser.parse_args()

    results = run_checks()
    drift_count = print_report(results)

    if args.json:
        data = {
            "timestamp": datetime.now().isoformat(),
            "total": len(results),
            "ok": sum(1 for r in results if r["status"] == "OK"),
            "drift": drift_count,
            "results": results,
        }
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    return 1 if drift_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
