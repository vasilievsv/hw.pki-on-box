[🇬🇧 English](README.md) | [🇷🇺 Русский](README_RU.md) | [🇫🇷 Français](README_FR.md) | [🇨🇳 简体中文](README_ZH.md)

# hw.pki-on-box

> ⚠️ **教学项目** — 探索PKI、硬件TRNG、SDD合约和Linux内核安全。未经独立安全审计，不适用于生产环境。

PKI服务器 + 密钥管理器，运行在RK3328（ARM64，Linux）上，使用STM32作为硬件熵源（通过USB HID的TRNG）。从芯片到X.509证书的完整熵链，成本仅50美元。

## 有何不同

GitHub上大多数"PKI"仓库只是带REST API的密钥生成器。那不是PKI。

本项目将底层硬件连接到完整的PKI栈：

- **硬件熵** — STM32 TRNG（G474/G431/H750）将真实物理随机性注入OpenSSL RAND池。不是`os.urandom()`。
- **NIST DRBG** — 基于硬件熵的HMAC-DRBG SP 800-90A，带健康检查。
- **完整PKI** — CA仪式、X.509签发、CRL、OCSP。REST API + CLI。
- **50美元硬件** — RK3328 SBC（35美元）+ STM32开发板（12美元）。无需1万美元的HSM。
- **SDD合约** — 通过Design by Contract验证固件（YAML phases/pre/post/invariants）+ 漂移检测。
- **FIPS 140-2** — KAT自检、密钥清零、安全策略文档（教学级别）。
- **已测试** — 62个合约测试（mock→real），共99个测试，GitHub Actions CI。
- **已部署** — 在真实ARM64硬件上运行：16 KB/s硬件熵，15ms API延迟。

## 功能

- 在RK3328 ARM64 SBC上原生运行（无Docker）
- 使用STM32作为硬件随机数生成器（USB HID，16 KB/s）
- 使用硬件TRNG执行Root CA仪式
- 通过REST API（1.6秒）和CLI签发X.509证书
- FIPS 140-2 KAT自检 + 密钥清零
- 固件TRNG的SDD合约（trng_hid.contract.yaml）
- 多板固件支持（STM32G474 / G431 / H750）

---

## 实现状态

| 组件 | 状态 |
|------|------|
| core：TRNG / DRBG / CryptoEngine / KeyStorage | ✅ 完成 |
| services：CA / Cert / CRL / OCSP | ✅ 完成 |
| storage：SQLite + FileStorage | ✅ 完成 |
| REST API（Flask）+ CLI（Click） | ✅ 完成 |
| 合约测试 W1-W2（62个真实测试） | ✅ 完成 |
| FIPS 140-2（KAT、清零、安全策略） | ✅ 完成 |
| GitHub Actions CI/CD + drift_check | ✅ 完成 |
| STM32固件（多板 G474/G431/H750） | ✅ 完成 |
| SDD固件合约（trng_hid.contract.yaml） | ✅ 完成 |
| 部署到RK3328（原生，systemd） | ✅ 完成 |
| 目标硬件上的HW TRNG验证（16 KB/s） | ✅ 完成 |
| SELinux + eBPF（完整版，需要内核5.x） | 📋 计划中 |

---

## 熵链

```
STM32 RNG外设（USB HID 0x0483:0x5750）
    └─ HardwareTRNG.get_entropy()     64字节/次，16 KB/s
        └─ NISTDRBG.generate()        HMAC-DRBG SP 800-90A
            └─ RAND_add()             → OpenSSL RAND池
                └─ rsa/ec.generate_private_key()
```

---

## 快速开始

```bash
pip install -r asw/PKI/requirements.txt
cd asw/PKI
PKI_TRNG_MODE=software python serve.py
```

---

## 标准

- NIST SP 800-90A（HMAC-DRBG）
- NIST SP 800-90B（熵源健康测试）
- FIPS 140-2（KAT、清零、安全策略 — 教学级别）
- ISO 26262 ASIL A（教学级别）
