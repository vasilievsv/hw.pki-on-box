#!/usr/bin/env python3
"""task4_debug_check.py — TASK-4: OpenOCD + GDB debug checklist"""
import subprocess, time, sys, re
from pathlib import Path

_PIO        = Path.home() / ".platformio/packages"
OPENOCD     = _PIO / "tool-openocd/bin/openocd.exe"
OCD_SCRIPTS = _PIO / "tool-openocd/openocd/scripts"
GDB         = _PIO / "toolchain-gccarmnoneeabi/bin/arm-none-eabi-gdb.exe"
ELF         = Path(__file__).parent.parent / ".pio/build/weact_g474ceu/firmware.elf"

OCD_CMD = [str(OPENOCD), "-s", str(OCD_SCRIPTS),
           "-f", "interface/cmsis-dap.cfg", "-f", "target/stm32g4x.cfg"]

GDB_SCRIPT = """set pagination off
set confirm off
target remote localhost:3333
monitor halt
info reg pc
x/4xw 0x200003dc
x/1xw 0x200003d8
x/1xw 0x200003d4
x/1xb 0x200003a0
monitor resume
quit
"""

def kill_ocd():
    subprocess.run(["taskkill", "/F", "/IM", "openocd.exe"], capture_output=True)

def run_gdb(script):
    f = Path(__file__).parent / "_t4.gdb"
    f.write_text(script, encoding="ascii")
    try:
        r = subprocess.run([str(GDB), "-batch", "-x", str(f), str(ELF)],
                           capture_output=True, text=True, timeout=15)
        return r.stdout + r.stderr
    except subprocess.TimeoutExpired:
        return "TIMEOUT"
    finally:
        f.unlink(missing_ok=True)

def main():
    if not ELF.exists():
        print(f"ELF not found: {ELF}"); sys.exit(1)

    kill_ocd(); time.sleep(0.5)
    ocd = subprocess.Popen(OCD_CMD, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2.5)

    results = {}
    try:
        out = run_gdb(GDB_SCRIPT)

        # 1. OpenOCD подключается — GDB подключился если есть PC
        results["OpenOCD connect"] = "pc" in out.lower() or "halted" in out.lower()

        # 2. PC в диапазоне прошивки
        m = re.search(r"pc\s+(0x[0-9a-f]+)", out, re.IGNORECASE)
        if m:
            pc = int(m.group(1), 16)
            results["PC in flash (0x08000000+)"] = 0x08000000 <= pc <= 0x08080000
        else:
            results["PC in flash (0x08000000+)"] = False

        # 3. hrng.State == HAL_RNG_STATE_READY (0x20) — первый байт hrng struct
        lines = out.splitlines()
        vals = [l for l in lines if "0x200003dc" in l or "0x200003d8" in l or
                "0x200003d4" in l or "0x200003a0" in l]

        hrng_val = None
        send_ok_val = None
        send_busy_val = None
        dev_state_val = None
        for l in lines:
            m2 = re.search(r"0x200003dc.*?0x([0-9a-f]+)", l, re.IGNORECASE)
            if m2: hrng_val = int(m2.group(1), 16)
            m2 = re.search(r"0x200003d8.*?0x([0-9a-f]+)", l, re.IGNORECASE)
            if m2: send_ok_val = int(m2.group(1), 16)
            m2 = re.search(r"0x200003d4.*?0x([0-9a-f]+)", l, re.IGNORECASE)
            if m2: send_busy_val = int(m2.group(1), 16)
            m2 = re.search(r"0x200003a0.*?0x([0-9a-f]+)", l, re.IGNORECASE)
            if m2: dev_state_val = int(m2.group(1), 16)

        # hrng: читаем 4 слова начиная с 0x200003dc
        # вывод: "0x200003dc <hrng>: 0xXXXX 0xXXXX 0xXXXX 0xXXXX"
        # State находится в третьем слове, байт 1 (offset 9 от начала struct)
        hrng_ok = False
        for l in lines:
            if "200003dc" in l:
                nums = re.findall(r"0x([0-9a-fA-F]+)", l)
                # пропускаем первый — это адрес 0x200003dc
                words = [int(x, 16) for x in nums if len(x) == 8]
                # words[0] = адрес 0x200003dc, words[1..4] = данные
                if len(words) >= 4:
                    state_word = words[3]  # третье слово данных
                    state_byte = (state_word >> 8) & 0xFF
                    # READY=0x20, BUSY=0x01/0x02 — если send_ok>0 значит RNG работает
                    hrng_ok = state_byte in (0x01, 0x02, 0x20)
                break
        results["hrng.State == READY/BUSY (RNG active)"] = hrng_ok
        results["send_ok > 0"] = (send_ok_val is not None and send_ok_val > 0)
        results["dev_state CONFIGURED/SUSPENDED"] = dev_state_val in (0x03, 0x04)

    finally:
        ocd.terminate(); kill_ocd()

    print("\nTASK-4 Debug Checklist:")
    print("-" * 45)
    passed = 0
    for name, ok in results.items():
        icon = "[PASS]" if ok else "[FAIL]"
        print(f"  {icon} {name}")
        if ok: passed += 1
    print("-" * 45)
    print(f"  {passed}/{len(results)} PASSED")
    print(f"\n{'[PASS] TASK-4 OK' if passed == len(results) else '[FAIL] TASK-4 FAILED'}")
    return passed == len(results)

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
