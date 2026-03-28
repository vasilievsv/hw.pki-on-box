# PKI-on-Box — ASW / PKI

Python-стек PKI для Radxa Zero. Аппаратная энтропия от STM32G474CEU (USB HID TRNG).

## Архитектура

```
STM32G474CEU (USB HID 0x0483:0x5750)
    └─ HardwareTRNG          core/trng.py
        └─ NISTDRBG           core/drbg.py       HMAC-DRBG SP 800-90A
            └─ _seed_openssl()                    RAND_add → OpenSSL RAND пул
                └─ CryptoEngine  core/crypto_engine.py   RSA/EC keygen, sign, verify
                    └─ KeyStorage    core/key_storage.py  AES-256 зашифрованные ключи
                        └─ Services  services/            CA, Cert, CRL, OCSP
                            └─ REST API  api/rest_api.py
```

## Entropy chain

Аппаратная энтропия подмешивается в OpenSSL RAND пул перед каждой генерацией ключа:

```python
# CryptoEngine._seed_openssl()
data = self._drbg.generate(64)          # NISTDRBG ← HardwareTRNG ← STM32 USB HID
_openssl.lib.RAND_add(data, len(data), float(len(data)))
# затем rsa/ec.generate_private_key() — библиотека не знает откуда энтропия
```

Режимы TRNG (config.yaml → `trng.mode`):

| Режим | Поведение |
|-------|-----------|
| `hardware` | только USB HID, ошибка если нет устройства |
| `auto` | USB HID если доступен, иначе SoftwareTRNG |
| `software` | только os.urandom (для тестов) |

## Структура

```
core/
  trng.py           HardwareTRNG + SoftwareTRNG
  drbg.py           NISTDRBG (HMAC-SHA256)
  crypto_engine.py  RSA/EC keygen + sign/verify + RAND_add injection
  key_storage.py    AES-256 encrypted key storage
services/
  ca_service.py     Root CA / Intermediate CA
  certificate_service.py  выпуск сертификатов
  crl_service.py    CRL генерация и отзыв
  ocsp_service.py   OCSP responder
api/
  rest_api.py       Flask REST API
storage/
  database.py       SQLite
  file_storage.py   файловое хранилище сертификатов
tests/
  conftest.py       fixtures (mode: software для unit-тестов)
  test_core.py
  test_services.py
  test_api.py
```

## Запуск

```bash
pip install -r requirements.txt

# Запуск (hardware TRNG — STM32G474CEU должен быть подключён)
python main.py

# Конфигурация
cp config.example.yaml config.yaml
# trng.mode: hardware | auto | software
```

## Тесты

```bash
pytest tests/ -v
```

Unit-тесты используют `mode: software` — железо не требуется.

## Hardware smoke test

```bash
# Проверка STM32G474CEU (WeAct G474CEU) — USB HID TRNG
python firmware/hmi/test/check_trng_hid.py
```

## Зависимости

- `cryptography >= 36` — X.509, RSA, EC, OpenSSL bindings
- `hid` — USB HID для чтения энтропии с STM32
- `flask` — REST API