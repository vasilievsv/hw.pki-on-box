[🇬🇧 English](README.md) | [🇷🇺 Русский](README_RU.md) | [🇫🇷 Français](README_FR.md) | [🇨🇳 简体中文](README_ZH.md)

# hw.pki-on-box

> ⚠️ **Учебный проект** — исследование PKI, аппаратного TRNG, SDD-контрактов и безопасности ядра Linux. Не предназначен для production без независимого аудита безопасности.

PKI-сервер + менеджер ключей на RK3328 (ARM64, Linux) с STM32 в качестве аппаратного источника энтропии (TRNG через USB HID). Полная цепочка энтропии от кремния до X.509 сертификатов за $50.

## Чем отличается

Большинство «PKI на GitHub» — это генераторы ключей с REST API обёрткой. Это не PKI.

Этот проект связывает низкоуровневое железо с полным PKI стеком:

- **Аппаратная энтропия** — STM32 TRNG (G474/G431/H750) подаёт реальную физическую случайность в OpenSSL RAND pool. Не `os.urandom()`.
- **NIST DRBG** — HMAC-DRBG SP 800-90A поверх аппаратной энтропии с health checks.
- **Полный PKI** — церемония CA, выпуск X.509, CRL, OCSP. REST API + CLI.
- **Железо за $50** — RK3328 SBC ($35) + STM32 плата ($12). Без HSM за $10k.
- **SDD-контракты** — firmware верифицируется через Design by Contract (YAML phases/pre/post/invariants) + drift detection.
- **FIPS 140-2** — KAT self-tests, зануление ключей, документация Security Policy (учебный уровень).
- **Тесты** — 62 contract-теста (mock→real), 99 всего, GitHub Actions CI.
- **Задеплоен** — работает на реальном ARM64 железе: 16 КБ/с аппаратной энтропии, 15мс latency API.

Цепочка энтропии от кремния до OpenSSL задокументирована и открыта. Это редкость.

## Что делает

- Работает на RK3328 ARM64 SBC (нативно, без Docker)
- Использует STM32 как аппаратный генератор случайных чисел (USB HID, 16 КБ/с)
- Проводит церемонию Root CA с аппаратным TRNG
- Выпускает X.509 сертификаты через REST API (1.6с) и CLI
- FIPS 140-2 KAT self-tests + зануление ключей
- SDD-контракт для firmware TRNG (trng_hid.contract.yaml)
- Поддержка нескольких плат (STM32G474 / G431 / H750)
- BSW hardening с graceful degradation (SELinux + eBPF планируется для ядра 5.x)

---

## Статус реализации

| Компонент | Статус |
|-----------|--------|
| core: TRNG / DRBG / CryptoEngine / KeyStorage | ✅ готово |
| services: CA / Cert / CRL / OCSP | ✅ готово |
| storage: SQLite + FileStorage | ✅ готово |
| REST API (Flask) + CLI (Click) | ✅ готово |
| Contract-тесты W1-W2 (62 реальных теста) | ✅ готово |
| FIPS 140-2 (KAT, зануление, Security Policy) | ✅ готово |
| GitHub Actions CI/CD + drift_check | ✅ готово |
| Firmware STM32 (multi-board G474/G431/H750) | ✅ готово |
| SDD firmware контракт (trng_hid.contract.yaml) | ✅ готово |
| Деплой на RK3328 (нативный, systemd) | ✅ готово |
| Валидация HW TRNG на железке (16 КБ/с) | ✅ готово |
| BSW hardening (graceful degradation) | ✅ готово |
| SELinux + eBPF (полный, требует ядро 5.x) | 📋 планируется |
| Contract-тесты W3 (Linux-only) | 📋 планируется |

---

## Цепочка энтропии

```
STM32 RNG периферия (USB HID 0x0483:0x5750)
    └─ HardwareTRNG.get_entropy()     64 байта / вызов, 16 КБ/с
        └─ NISTDRBG.generate()        HMAC-DRBG SP 800-90A
            └─ RAND_add()             → OpenSSL RAND pool
                └─ rsa/ec.generate_private_key()
```

Настраивается через `trng.mode: hardware | auto | software`.

---

## Быстрый старт

```bash
pip install -r asw/PKI/requirements.txt
cd asw/PKI
PKI_TRNG_MODE=software python serve.py
```

---

## Тестирование

```bash
pip install -r asw/PKI/requirements-dev.txt
PKI_TRNG_MODE=software pytest asw/PKI/tests/ -v
# Результат: 99 passed
```

---

## Деплой на ARM64

Целевая платформа: RK3328 (Cortex-A53, 2GB RAM, Ubuntu 18.04, Python 3.6)

```bash
python3 -m venv /opt/pki-on-box/venv
source /opt/pki-on-box/venv/bin/activate
pip install -r deploy/requirements-rk3328.txt
```

---

## Стандарты

- NIST SP 800-90A (HMAC-DRBG)
- NIST SP 800-90B (health tests источника энтропии)
- FIPS 140-2 (KAT, зануление, Security Policy — учебный уровень)
- ISO 26262 ASIL A (учебный уровень)
