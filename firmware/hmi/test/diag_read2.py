#!/usr/bin/env python3
import hid, time

VID, PID = 0x0483, 0x5750
devs = hid.enumerate(VID, PID)
if not devs:
    print("device not found"); exit(1)

d = next((x for x in devs if x['usage_page'] == 0xFF00), devs[0])
dev = hid.device()
dev.open_path(d['path'])
dev.set_nonblocking(0)
print("opened, waiting 2s for device to wake from suspend...")
time.sleep(2)

print("reading 5 reports (blocking, 2000ms timeout each):")
for i in range(5):
    r = dev.read(64, timeout_ms=2000)
    if r:
        print(f"  [{i}] len={len(r)} first4={bytes(r[:4]).hex()}")
    else:
        print(f"  [{i}] timeout (0 bytes)")

dev.close()
