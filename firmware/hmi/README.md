# firmware/hmi — STM32H750VBT6 TRNG Streamer

MCU: STM32H750VBT6  
Toolchain: PlatformIO + STM32Cube  
Role: Hardware TRNG → USB HID stream → host PKI service

## Build

```bash
pio run -e hmi
```

## Flash

```bash
pio run -e hmi --target upload
```
