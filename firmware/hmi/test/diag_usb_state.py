#!/usr/bin/env python3
"""diag_usb_state.py — проверка состояния USB через GDB"""
import subprocess, time, sys
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
echo send_ok:
x/1xw 0x200003d8
echo send_busy:
x/1xw 0x200003d4
echo dev_state:
x/1xb 0x200003A0
echo dev_old_state:
x/1xb 0x200003A1
echo dev_address:
x/1xb 0x200003A2
echo dev_config:
x/1xw 0x20000108
quit
"""

def kill_ocd():
    subprocess.run(["taskkill", "/F", "/IM", "openocd.exe"], capture_output=True)

def main():
    if not ELF.exists():
        print(f"ELF not found: {ELF}"); sys.exit(1)

    kill_ocd(); time.sleep(0.5)
    ocd = subprocess.Popen(OCD_CMD, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2.5)

    gdb_file = Path(__file__).parent / "_diag.gdb"
    gdb_file.write_text(GDB_SCRIPT, encoding="ascii")
    try:
        r = subprocess.run([str(GDB), "-batch", "-x", str(gdb_file), str(ELF)],
                           capture_output=True, text=True, timeout=15)
        print(r.stdout)
        if r.stderr: print("STDERR:", r.stderr[:500])
    except subprocess.TimeoutExpired:
        print("TIMEOUT")
    finally:
        gdb_file.unlink(missing_ok=True)
        ocd.terminate(); kill_ocd()

if __name__ == "__main__":
    main()
