# PKI-010: PKCS1v15 → RSA-PSS + AllowedSigAlg facade

## Проблема
- Контракт crypto-engine: INV padding == RSA-PSS, PKCS#1 v1.5 == ЗАПРЕЩЕНО
- Код crypto_engine.py sign_data(): использовал padding.PKCS1v15()
- Источник: комментарий Dhwtj на Хабре + расхождение контракт/код

## Изменения

**10.1 — sign_data() → PSS**
- `padding.PSS(mgf=MGF1(SHA256), salt_length=MAX_LENGTH)`

**10.2 — verify_certificate() → signature_algorithm_parameters**
- Автоопределение padding из сертификата (поддержка PSS и PKCS1v15)

**10.3 — Contract-тесты**
- `test_rsa_sign_verify_roundtrip` → verify через PSS
- `test_rejects_pkcs1v15_signature` (новый) → PKCS1v15 подпись отвергается PSS verify
- `test_uses_sha256_not_sha1` → PSS

**10.4 — KAT RSA → PSS round-trip**
- `self_tests.py _kat_rsa_sign()` → PSS sign + verify

**10.5 — AllowedSigAlg + AllowedAead facade**
- Паттерн "parse, don't validate" (Dhwtj)
- `AllowedSigAlg.parse("RSA-PSS-SHA256")` → frozen dataclass
- `AllowedSigAlg.parse("RSA-PKCS1v15-SHA256")` → ValueError: Forbidden
- Предготовленные константы: RSA_PSS_SHA256, RSA_PSS_SHA384, ECDSA_SHA256, ECDSA_SHA384
- sign_data() принимает опциональный `alg: AllowedSigAlg`

**Инфраструктура**
- `requirements.txt`: cryptography>=3.4 → >=41.0
- `drift_check_host.py`: CE-5 (PKCS1v15 ban), CE-6 (AllowedSigAlg)

## Тесты
- 32/32 passed (Windows + RK3328 aarch64)
- drift_check: 15/15 OK, 0 DRIFT
- cryptography на RK3328: 3.4.8 → 46.0.7

## Файлы

| Файл | Изменение |
|------|-----------|
| `asw/PKI/core/crypto_engine.py` | sign_data → PSS, verify_certificate → signature_algorithm_parameters |
| `asw/PKI/core/allowed_algorithms.py` | NEW: AllowedSigAlg + AllowedAead facade |
| `asw/PKI/core/self_tests.py` | KAT RSA → PSS round-trip |
| `asw/PKI/tests/test_crypto_engine_contract.py` | PSS verify + reject PKCS1v15 |
| `asw/PKI/tests/test_core.py` | PSS verify |
| `asw/PKI/tests/test_allowed_algorithms.py` | NEW: 13 тестов для facade |
| `asw/PKI/requirements.txt` | cryptography>=41.0 |
| `scripts/drift_check_host.py` | CE-5, CE-6 |
