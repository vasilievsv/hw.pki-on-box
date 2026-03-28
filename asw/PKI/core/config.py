import os
import yaml


_DEFAULTS = {
    "trng": {
        "mode": "hardware",
        "hid_vid": "0x0483",
        "hid_pid": "0x5750",
        "device": "/dev/random",
    },
    "drbg": {
        "algorithm": "hmac-sha256",
        "reseed_interval": 1000,
        "personalization": "",
    },
    "crypto": {
        "rsa_key_size": 4096,
        "ec_curve": "P-384",
        "aes_key_size": 256,
    },
    "storage": {
        "path": "asw/PKI/storage",
        "backend": "file",
    },
}

_ENV_MAP = {
    "PKI_TRNG_MODE":    ("trng", "mode"),
    "PKI_STORAGE_PATH": ("storage", "path"),
    "PKI_HID_VID":      ("trng", "hid_vid"),
    "PKI_HID_PID":      ("trng", "hid_pid"),
}


def load_config(path: str = None) -> dict:
    config_path = path or os.environ.get("PKI_CONFIG", "asw/PKI/config.yaml")

    import copy
    cfg = copy.deepcopy(_DEFAULTS)

    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            file_cfg = yaml.safe_load(f) or {}
        for section, values in file_cfg.items():
            if section in cfg and isinstance(values, dict):
                cfg[section].update(values)
            else:
                cfg[section] = values

    for env_key, (section, key) in _ENV_MAP.items():
        val = os.environ.get(env_key)
        if val is not None:
            cfg.setdefault(section, {})[key] = val

    return cfg
