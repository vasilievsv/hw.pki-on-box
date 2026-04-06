#!/usr/bin/env python3
"""Drift detection L1 для firmware C-кода vs trng_hid.contract.yaml.

Запуск:
  python scripts/drift_check_firmware.py
  python scripts/drift_check_firmware.py --json results.json
"""
import yaml
import re
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).parent.parent
FW_DIR = BASE / "firmware" / "hmi" / "src"

L1_CHECKS = [
    {
        "id": "G1", "phase": "fill_report", "severity": "CRITICAL",
        "desc": "HAL_RNG_GenerateRandomNumber return value must be checked",
        "file": "trng_hid.c",
        "pattern_good": r"if\s*\(\s*HAL_RNG_GenerateRandomNumber\s*\(.+\)\s*!=\s*HAL_OK\s*\)",
        "check": "good_present",
    },
    {
        "id": "G2", "phase": "rng_status_check", "severity": "CRITICAL",
        "desc": "RNG_SR.SECS / RNG_SR.CECS must be checked",
        "file": "trng_hid.c",
        "pattern_good": r"RNG_FLAG_SECS|RNG_SR.*SECS|__HAL_RNG_GET_FLAG.*SECS",
        "check": "good_present",
    },
    {
        "id": "G4", "phase": "startup_test", "severity": "CRITICAL",
        "desc": "Startup self-test (TSR-1) must exist",
        "file": "trng_hid.c",
        "pattern_good": r"TRNG_StartupTest|startup.?test|0x00000000U|0xFFFFFFFF",
        "check": "good_present",
    },
    {
        "id": "G6", "phase": "fill_report", "severity": "CRITICAL",
        "desc": "Continuous health check (TSR-2) — repeat detection",
        "file": "trng_hid.c",
        "pattern_good": r"trng_prev|prev.*rnd|rnd.*==.*prev|continuous.*check",
        "check": "good_present",
    },
    {
        "id": "G7", "phase": "trng_init", "severity": "HIGH",
        "desc": "HAL_RCCEx_PeriphCLKConfig return value must be checked",
        "file": "trng_hid.c",
        "pattern_good": r"if\s*\(\s*HAL_RCCEx_PeriphCLKConfig\s*\(.+\)\s*!=\s*HAL_OK\s*\)",
        "check": "good_present",
    },
    {
        "id": "G8", "phase": "trng_init", "severity": "CRITICAL",
        "desc": "HAL_RNG_Init return value must be checked",
        "file": "trng_hid.c",
        "pattern_good": r"if\s*\(\s*HAL_RNG_Init\s*\(.+\)\s*!=\s*HAL_OK\s*\)",
        "check": "good_present",
    },
    {
        "id": "G10", "phase": "fill_report", "severity": "MEDIUM",
        "desc": "Report ID must be set in report[0]",
        "file": "trng_hid.c",
        "pattern_good": r"report\[0\]\s*=\s*0x01|report\[0\]\s*=\s*1",
        "check": "good_present",
    },
    {
        "id": "G3", "phase": "error_handling", "severity": "HIGH",
        "desc": "Error_Handler must have diagnostics (not empty while(1))",
        "file": "main.c",
        "pattern_bad": r"void\s+Error_Handler\s*\(\s*void\s*\)\s*\{\s*while\s*\(\s*1\s*\)\s*\{\s*\}\s*\}",
        "check": "bad_absent",
    },
    {
        "id": "G5", "phase": "error_handling", "severity": "HIGH",
        "desc": "Watchdog (IWDG) must be initialized",
        "file": "main.c",
        "pattern_good": r"IWDG|HAL_IWDG_Init|__HAL_RCC_IWDG",
        "check": "good_present",
    },
    {
        "id": "G9", "phase": "main_loop", "severity": "MEDIUM",
        "desc": "Rate limiting in main loop (delay on BUSY)",
        "file": "main.c",
        "pattern_good": r"HAL_Delay|rate.?limit|backoff|sleep|osDelay",
        "check": "good_present",
    },
]


def find_c_files(fw_dir):
    files = {}
    for ext in ("*.c", "*.h"):
        for f in fw_dir.glob(ext):
            files[f.name] = f
    return files


def read_text(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def run_checks(fw_dir):
    results = []
    c_files = find_c_files(fw_dir)

    for chk in L1_CHECKS:
        fname = chk["file"]
        if fname not in c_files:
            results.append({
                "id": chk["id"], "phase": chk["phase"], "severity": chk["severity"],
                "status": "DRIFT", "desc": f"{fname} not found",
            })
            continue

        src = read_text(c_files[fname])
        mode = chk["check"]

        if mode == "good_present":
            found = bool(re.search(chk["pattern_good"], src, re.MULTILINE | re.IGNORECASE))
            status = "OK" if found else "DRIFT"
        elif mode == "bad_absent":
            found = bool(re.search(chk["pattern_bad"], src, re.MULTILINE | re.DOTALL))
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
    print(f"FIRMWARE DRIFT REPORT (L1 regex)")
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
    parser = argparse.ArgumentParser(description="Firmware drift detection L1")
    parser.add_argument("--firmware-dir", default=None)
    parser.add_argument("--json", default=None)
    args = parser.parse_args()

    fw_dir = Path(args.firmware_dir) if args.firmware_dir else FW_DIR
    if not fw_dir.exists():
        print(f"❌ Firmware dir not found: {fw_dir}")
        return 1

    results = run_checks(fw_dir)
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
