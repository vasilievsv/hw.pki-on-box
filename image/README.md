# image — Linux kernel & rootfs for RK3328

Custom Linux 5.10 kernel build for Firefly AIO-RK3328-JD4 with SELinux, eBPF and USB2 PHY support.

## Board

| Parameter | Value |
|-----------|-------|
| SoC | RK3328 (Cortex-A53 x4, ARM64) |
| RAM | 2GB DDR3 |
| eMMC | 8GB |
| Board | Firefly AIO-RK3328-JD4 (mb-jd4 rev1) |
| Kernel | 5.10.226 (Rockchip BSP develop-5.10) |
| Console | UART2 (ttyS2), 1500000 baud |

## Kernel features

| Feature | Config | Status |
|---------|--------|--------|
| SELinux | CONFIG_SECURITY_SELINUX=y | ✅ enabled |
| eBPF | CONFIG_BPF_SYSCALL=y, BPF_JIT_ALWAYS_ON=y | ✅ enabled |
| USB2 PHY | Rebuilt for STM32 HID (/dev/hidraw0) | ✅ fixed |
| CAN | CONFIG_CAN=y, vcan, mcp251xfd | ✅ enabled |
| WiFi | RTL8723DS (lwfinger out-of-tree) | ✅ working |

## Structure

```
image/
└── mb-jd4-rev1/
    ├── firefly_aiojd4_defconfig   ← kernel defconfig
    ├── rk3328-firefly-aiojd4.dts  ← device tree (ported from BSP 4.4)
    └── README.md                  ← detailed build & flash instructions
```

## Quick build

```bash
cd /path/to/kernel-5.10

# Apply defconfig
cp image/mb-jd4-rev1/firefly_aiojd4_defconfig arch/arm64/configs/
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- firefly_aiojd4_defconfig

# Build
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- Image dtbs modules -j$(nproc)
```

See [mb-jd4-rev1/README.md](mb-jd4-rev1/README.md) for full build, flash and troubleshooting instructions.

## Key changes from stock Firefly kernel

- Kernel 4.4 → 5.10 (Rockchip BSP develop-5.10)
- SELinux + eBPF enabled for PKI hardening
- USB2 PHY rebuilt for STM32 HID TRNG device
- DTS ported from BSP 4.4 aiojd4 to BSP 5.10 roc-cc base
- WiFi: in-tree rtl8723ds → lwfinger out-of-tree module
- Console: fiq-debugger → ttyS2 1500000 baud
- Modular build: GPU, media, codecs = modules (smaller Image ~22MB)
