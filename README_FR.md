[🇬🇧 English](README.md) | [🇷🇺 Русский](README_RU.md) | [🇫🇷 Français](README_FR.md) | [🇨🇳 简体中文](README_ZH.md)

# hw.pki-on-box

> ⚠️ **Projet éducatif** — exploration de la PKI, du TRNG matériel, des contrats SDD et de la sécurité du noyau Linux. Non destiné à la production sans audit de sécurité indépendant.

Serveur PKI + gestionnaire de clés fonctionnant sur RK3328 (ARM64, Linux) avec STM32 comme source d'entropie matérielle (TRNG via USB HID). Chaîne d'entropie complète du silicium aux certificats X.509 pour 50$.

## En quoi c'est différent

La plupart des dépôts « PKI sur GitHub » sont des générateurs de clés avec une API REST. Ce n'est pas de la PKI.

Ce projet connecte du matériel bas niveau à une pile PKI complète :

- **Entropie matérielle** — le TRNG STM32 (G474/G431/H750) injecte de l'aléa physique réel dans le pool RAND d'OpenSSL. Pas `os.urandom()`.
- **NIST DRBG** — HMAC-DRBG SP 800-90A au-dessus de l'entropie matérielle, avec contrôles de santé.
- **PKI complète** — cérémonie CA, émission X.509, CRL, OCSP. API REST + CLI.
- **Matériel à 50$** — SBC RK3328 (35$) + carte STM32 (12$). Pas de HSM à 10k$.
- **Contrats SDD** — le firmware est vérifié par Design by Contract (phases/pré/post/invariants YAML) + détection de dérive.
- **FIPS 140-2** — auto-tests KAT, mise à zéro des clés, documentation Security Policy (niveau éducatif).
- **Testé** — 62 tests de contrat (mock→réel), 99 tests au total, CI GitHub Actions.
- **Déployé** — fonctionne sur du matériel ARM64 réel : 16 Ko/s d'entropie matérielle, 15ms de latence API.

## Ce qu'il fait

- Fonctionne sur SBC RK3328 ARM64 (nativement, sans Docker)
- Utilise STM32 comme générateur de nombres aléatoires matériel (USB HID, 16 Ko/s)
- Effectue la cérémonie Root CA avec TRNG matériel
- Émet des certificats X.509 via API REST (1.6s) et CLI
- Auto-tests FIPS 140-2 KAT + mise à zéro des clés
- Contrat SDD pour le firmware TRNG (trng_hid.contract.yaml)
- Support multi-cartes (STM32G474 / G431 / H750)

---

## Statut d'implémentation

| Composant | Statut |
|-----------|--------|
| core : TRNG / DRBG / CryptoEngine / KeyStorage | ✅ terminé |
| services : CA / Cert / CRL / OCSP | ✅ terminé |
| stockage : SQLite + FileStorage | ✅ terminé |
| API REST (Flask) + CLI (Click) | ✅ terminé |
| Tests de contrat W1-W2 (62 tests réels) | ✅ terminé |
| FIPS 140-2 (KAT, mise à zéro, Security Policy) | ✅ terminé |
| CI/CD GitHub Actions + drift_check | ✅ terminé |
| Firmware STM32 (multi-cartes G474/G431/H750) | ✅ terminé |
| Contrat SDD firmware (trng_hid.contract.yaml) | ✅ terminé |
| Déploiement sur RK3328 (natif, systemd) | ✅ terminé |
| Validation HW TRNG sur cible (16 Ko/s) | ✅ terminé |
| SELinux + eBPF (complet, nécessite noyau 5.x) | 📋 prévu |

---

## Chaîne d'entropie

```
Périphérique RNG STM32 (USB HID 0x0483:0x5750)
    └─ HardwareTRNG.get_entropy()     64 octets / appel, 16 Ko/s
        └─ NISTDRBG.generate()        HMAC-DRBG SP 800-90A
            └─ RAND_add()             → pool RAND OpenSSL
                └─ rsa/ec.generate_private_key()
```

---

## Démarrage rapide

```bash
pip install -r asw/PKI/requirements.txt
cd asw/PKI
PKI_TRNG_MODE=software python serve.py
```

---

## Normes

- NIST SP 800-90A (HMAC-DRBG)
- NIST SP 800-90B (tests de santé de la source d'entropie)
- FIPS 140-2 (KAT, mise à zéro, Security Policy — niveau éducatif)
- ISO 26262 ASIL A (niveau éducatif)
