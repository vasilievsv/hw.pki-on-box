# mb-jd4 rev1 — Backplane Image (RK3328)

## Платформа

| Параметр | Значение |
|----------|----------|
| SoC | RK3328 (Cortex-A53 x4, aarch64) |
| RAM | 2GB DDR3 |
| eMMC | 8GB |
| Backplane | mb-jd4 первая ревизия (Firefly AIO-RK3328-JD4) |
| WiFi | RTL8723DS (SDIO), маркировка на чипе: 6223A |
| Ethernet | RMII 100Mbit (stmmac, random MAC) |
| Console | UART2 (ttyS2), 1500000 baud |
| SDK | rk3328_linux_release_v2.5.1_20210301 |

## Ядро

- Версия: 5.10.226 (Rockchip BSP develop-5.10)
- Источник: https://github.com/rockchip-linux/kernel (ветка develop-5.10)
- Defconfig: `firefly_aiojd4_defconfig` (см. файл в этой директории)
- Image: ~22MB (влезает в 32MB boot partition)

### Ключевые опции

- SELinux: подготовлен (CONFIG_SECURITY_SELINUX=y), policy не установлен
- eBPF: CONFIG_BPF_SYSCALL=y, BPF_JIT_ALWAYS_ON=y, CGROUP_BPF=y
- CAN: CONFIG_CAN=y, vcan, mcp251xfd
- WiFi: CONFIG_RTL8723DS=m (out-of-tree модуль lwfinger)
- Модульная сборка: GPU, media, codecs, sound — всё =m для уменьшения Image

## DTS

Файл: `rk3328-firefly-aiojd4.dts`

Портирован с BSP 4.4 aiojd4 на базу BSP 5.10 rk3328-roc-cc.dts.

Кастомные изменения:
- GMAC: RMII mode, clock_in_out="output", кастомный rmiim1_pins (без gpio1-24, конфликт с PMIC)
- SDIO WiFi: RTL8723DS + sdio_pwrseq (gpio3-RK_PB0)
- Console: ttyS2 1500000 baud (fiq-debugger отключён)
- USB: OTG mode (не host)
- Audio: i2s0/i2s1 + codec + hdmi-sound
- LEDs: rk805 gpio, aiojd4 polarity
- bootargs: console=ttyS2,1500000n8 + overlayroot + cgroup_enable=memory

## WiFi модуль (RTL8723DS)

Чип на плате маркирован как **6223A** — это RTL8723DS (Realtek SDIO WiFi+BT combo).

BSP 5.10 содержит исходники в `drivers/net/wireless/rockchip_wlan/rtl8723ds/`,
но они не компилируются с ядром 5.10 (конфликты: sha256, sched_param, cfg80211 API).

Решение: out-of-tree модуль из https://github.com/lwfinger/rtl8723ds

Сборка:
```bash
git clone --depth 1 https://github.com/lwfinger/rtl8723ds.git
cd rtl8723ds

# Фикс VFS namespace (Rockchip BSP)
echo 'MODULE_IMPORT_NS(VFS_internal_I_am_really_a_filesystem_and_am_NOT_a_driver);' >> os_dep/linux/os_intfs.c

make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- KSRC=/path/to/kernel-5.10 modules -j$(nproc)
# Результат: 8723ds.ko (~2.6MB)
```

Установка в rootfs:
```bash
cp 8723ds.ko /lib/modules/5.10.226/extra/
depmod -a 5.10.226
echo "8723ds" >> /etc/modules
```

## Serial Getty fix

Firefly rootfs содержит кастомный `serial-getty@.service` с захардкоженным `ttyFIQ0`.
При использовании ttyS2 (BSP 5.10) login prompt не появляется.

Фикс в `/lib/systemd/system/serial-getty@.service`:
```diff
-ExecStart=-/sbin/agetty -L --noclear -o '-p -- \\u' --keep-baud 115200,38400,9600 %I ttyFIQ0
+ExecStart=-/sbin/agetty -L --noclear -o '-p -- \\u' --keep-baud 1500000,115200,38400,9600 %I $TERM

-DeviceAllow=/dev/ttyFIQ0 rw
+DeviceAllow=/dev/%I rw
```

Плюс симлинк:
```bash
mkdir -p /etc/systemd/system/getty.target.wants
ln -sf /lib/systemd/system/serial-getty@.service \
  /etc/systemd/system/getty.target.wants/serial-getty@ttyS2.service
```

## Сборка boot.img

boot.img пакуется SDK 4.4 тулами (формат U-Boot 2017.09):
```bash
cd /path/to/kernel-5.10

# DTB
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- rockchip/rk3328-firefly-aiojd4.dtb

# resource.img (RSCE format)
/path/to/sdk/kernel/scripts/resource_tool arch/arm64/boot/dts/rockchip/rk3328-firefly-aiojd4.dtb

# boot.img
/path/to/sdk/kernel/scripts/mkbootimg \
  --kernel arch/arm64/boot/Image \
  --ramdisk /path/to/sdk/kernel/ramdisk.img \
  --second resource.img \
  -o boot_sdk.img

cp boot_sdk.img /path/to/sdk/kernel/boot.img
```

## Сборка update.img

```bash
cd /path/to/sdk
echo "n" | ./build.sh updateimg
```

## Известные проблемы

- Ethernet: tx_delay/rx_delay warnings (RMII не использует, драйвер ругается)
- USB2 PHY: IRQ index 0 not found (не критично)
- overlayroot: нет overlay модуля в initramfs
- SELinux: Could not open policy file (policy не установлен)
- rk808-clkout: probe failed -17 (xin32k конфликт)
- systemd-resolved, systemd-timesyncd: fail loop при старте (нет сети)
- systemd-rfkill: fail loop
