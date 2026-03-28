import os
import sys

from core import build_core, load_config


def main():
    cfg = load_config()
    trng, drbg, crypto, storage = build_core(cfg)

    print("🚀 PKI-on-Box запущен")
    print(f"   TRNG mode : {cfg['trng']['mode']}")
    print(f"   Storage   : {cfg['storage']['path']}")

    health = trng.health_check()
    if not health.get("passed", False):
        print(f"❌ TRNG health check failed: {health}", file=sys.stderr)
        sys.exit(1)
    print("   TRNG      : ✅ health check passed")

    keys = storage.list_keys()
    print(f"   Keys      : {len(keys)} stored")


if __name__ == "__main__":
    main()
