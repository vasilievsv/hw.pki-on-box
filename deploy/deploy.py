#!/usr/bin/env python3
import sys
import os
import yaml
import subprocess
import time
import argparse

DEFAULT_CONFIG = os.path.join(os.path.dirname(__file__), "config.yaml")
SERVICE_NAME = "pki.service"

def load_config(path):
    with open(path) as f:
        return yaml.safe_load(f)

def ssh_cmd(cmd, timeout=30):
    print(f"  → {cmd}")
    result = subprocess.run(
        ["ssh", f"{os.environ['PKI_SSH_USER']}@{os.environ['PKI_SSH_HOST']}",
         "-p", os.environ.get("PKI_SSH_PORT", "22"), cmd],
        capture_output=True, text=True, timeout=timeout
    )
    if result.stdout.strip():
        print(f"    {result.stdout.strip()}")
    if result.returncode != 0 and result.stderr.strip():
        print(f"    ⚠ {result.stderr.strip()}")
    return result

def scp_upload(local, remote):
    port = os.environ.get("PKI_SSH_PORT", "22")
    target = f"{os.environ['PKI_SSH_USER']}@{os.environ['PKI_SSH_HOST']}:{remote}"
    print(f"  → scp {local} → {remote}")
    result = subprocess.run(
        ["scp", "-P", port, "-r", local, target],
        capture_output=True, text=True, timeout=120
    )
    return result.returncode == 0

def health_check(cfg, retries=3):
    url = cfg["service"]["health_check_url"]
    timeout = cfg["service"].get("health_check_timeout_sec", 5)
    for i in range(retries):
        r = ssh_cmd(f"curl -sf --max-time {timeout} {url}", timeout=timeout + 5)
        if r.returncode == 0:
            return True
        time.sleep(2)
    return False

def backup(cfg):
    app_dir = cfg["paths"]["app_dir"]
    backup_dir = cfg["paths"]["backup_dir"]
    print("[1/4] Backup...")
    ssh_cmd(f"rm -rf {backup_dir} && cp -a {app_dir} {backup_dir}")

def upload(cfg, source_dir):
    app_dir = cfg["paths"]["app_dir"]
    print("[2/4] Upload...")
    ssh_cmd(f"rm -rf {app_dir}/*")
    if not scp_upload(source_dir + "/.", app_dir):
        print("  ✗ upload failed")
        return False
    return True

def restart(cfg):
    print("[3/4] Restart service...")
    ssh_cmd(f"systemctl restart {SERVICE_NAME}")
    time.sleep(cfg["service"].get("restart_timeout_sec", 10))

def rollback(cfg):
    app_dir = cfg["paths"]["app_dir"]
    backup_dir = cfg["paths"]["backup_dir"]
    print("[ROLLBACK] Restoring from backup...")
    r = ssh_cmd(f"test -d {backup_dir} && rm -rf {app_dir} && mv {backup_dir} {app_dir}")
    if r.returncode == 0:
        ssh_cmd(f"systemctl restart {SERVICE_NAME}")
        print("  ✓ rollback complete")
    else:
        print("  ✗ no backup found")

def deploy(cfg, source_dir, skip_health=False):
    backup(cfg)
    if not upload(cfg, source_dir):
        return False
    restart(cfg)
    if skip_health:
        print("[4/4] Health check skipped")
        return True
    print("[4/4] Health check...")
    if health_check(cfg):
        print("  ✓ service healthy")
        return True
    else:
        print("  ✗ health check failed")
        rollback(cfg)
        return False

def main():
    parser = argparse.ArgumentParser(description="PKI-on-Box deploy")
    parser.add_argument("source", help="local app/ directory to deploy")
    parser.add_argument("--config", default=DEFAULT_CONFIG, help="deploy config yaml")
    parser.add_argument("--rollback", action="store_true", help="rollback to previous version")
    parser.add_argument("--skip-health", action="store_true", help="skip health check")
    args = parser.parse_args()

    for var in ["PKI_SSH_USER", "PKI_SSH_HOST"]:
        if var not in os.environ:
            print(f"✗ {var} not set")
            sys.exit(1)

    cfg = load_config(args.config)

    if args.rollback:
        rollback(cfg)
    else:
        ok = deploy(cfg, args.source, skip_health=args.skip_health)
        sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
