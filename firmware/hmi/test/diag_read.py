#!/usr/bin/env python3
import hid, time

VID, PID = 0x0483, 0x5750
devs = hid.enumerate(VID, PID)
if not devs:
    print("device not found"); exit(1)

d = next((x for x in devs if x['usage_page'] == 0xFF00), devs[0])
print("path:", d['path'])
print("usage_page:", hex(d['usage_page']))

dev = hid.device()
dev.open_path(d['path'])

# nonblocking
dev.set_nonblocking(1)
print("nonblocking reads x5:")
for i in range(5):
    r = dev.read(65)
    hex4 = bytes(r[:4]).hex() if r else "empty"
    print(f"  [{i}] len={len(r)} data={hex4}")
    time.sleep(0.1)

# blocking
dev.set_nonblocking(0)
print("blocking read 2000ms:")
r = dev.read(65, timeout_ms=2000)
hex4 = bytes(r[:4]).hex() if r else "empty"
print(f"  len={len(r)} data={hex4}")

dev.close()
