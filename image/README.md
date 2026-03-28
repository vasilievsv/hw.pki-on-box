# image — Linux image (Buildroot/Yocto)

Образ Linux для SBC (Single Board Computer) hw.pki-on-box.

## Статус

🚧 Заглушка — реализация в следующих фазах.

## Планируемая структура

```
image/
├── buildroot/    ← Buildroot конфиг и overlay
├── yocto/        ← Yocto layer (альтернатива)
└── scripts/      ← build/flash скрипты
```

## Build (TODO)

```bash
make -C buildroot
```
