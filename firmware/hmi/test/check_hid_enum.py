#!/usr/bin/env python3
"""check_hid_enum.py — проверка USB HID enumeration PKI-TRNG (TASK-2)"""
import sys
import hid

VID, PID = 0x0483, 0x5750

def test_enumeration():
    devs = hid.enumerate(VID, PID)
    if not devs:
        print(f"[FAIL] enumeration: устройство {VID:04X}:{PID:04X} не найдено")
        print("\nВсе HID устройства:")
        for d in hid.enumerate():
            print(f"  {d['vendor_id']:04X}:{d['product_id']:04X}  {d['manufacturer_string']}  {d['product_string']}")
        return False

    print(f"[PASS] enumeration: найдено {len(devs)} интерфейс(ов)")
    for d in devs:
        print(f"  {d['vendor_id']:04X}:{d['product_id']:04X} | {d['manufacturer_string']} | {d['product_string']}")
        print(f"  usage_page=0x{d['usage_page']:04X} usage=0x{d['usage']:04X}")
    return True

def test_open():
    devs = hid.enumerate(VID, PID)
    if not devs:
        print("[SKIP] open: устройство не найдено")
        return False

    target = next((d for d in devs if d['usage_page'] == 0xFF00), devs[0])
    dev = hid.device()
    try:
        dev.open_path(target['path'])
        mfr  = dev.get_manufacturer_string()
        prod = dev.get_product_string()
        print(f"[PASS] open: {mfr} | {prod}")
        return True
    except Exception as e:
        print(f"[FAIL] open: {e}")
        return False
    finally:
        dev.close()

if __name__ == '__main__':
    ok = True
    ok &= test_enumeration()
    ok &= test_open()
    print(f"\n{'[PASS] TASK-2 USB HID OK' if ok else '[FAIL] TASK-2 FAILED'}")
    sys.exit(0 if ok else 1)
