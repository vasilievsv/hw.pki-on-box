import sys
from pathlib import Path
import click
from cryptography import x509
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption


def _get_services(ctx):
    return ctx.obj["services"]


def _save_pem(data: bytes, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    click.echo(f"  → {path}")


# ── Root ──────────────────────────────────────────────────────────────────────

@click.group()
@click.pass_context
def pki_cli(ctx):
    """PKI-on-Box CLI"""
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from core import load_config
    from serve import build_services
    ctx.ensure_object(dict)
    ctx.obj["services"] = build_services(load_config())


# ── CA ────────────────────────────────────────────────────────────────────────

@pki_cli.group()
def ca():
    """Управление центрами сертификации"""
    pass


@ca.command("create-root")
@click.option("--name", required=True)
@click.option("--validity", default=20, show_default=True, help="Validity years")
@click.pass_context
def ca_create_root(ctx, name, validity):
    """Создать корневой ЦС"""
    _, db, ca_svc, *_ = _get_services(ctx)
    cert = ca_svc.create_root_ca(name, validity)
    click.echo(f"✅ Root CA создан: {name}")
    click.echo(f"   Serial: {format(cert.serial_number, 'x')}")
    click.echo(f"   Valid until: {cert.not_valid_after_utc.date()}")


@ca.command("create-intermediate")
@click.option("--name", required=True)
@click.option("--parent", required=True, help="Parent CA id (e.g. ca_root_name)")
@click.option("--validity", default=10, show_default=True, help="Validity years")
@click.pass_context
def ca_create_intermediate(ctx, name, parent, validity):
    """Создать промежуточный ЦС"""
    _, db, ca_svc, *_ = _get_services(ctx)
    cert = ca_svc.create_intermediate_ca(name, parent, validity)
    click.echo(f"✅ Intermediate CA создан: {name}")
    click.echo(f"   Serial: {format(cert.serial_number, 'x')}")


@ca.command("list")
@click.pass_context
def ca_list(ctx):
    """Список CA"""
    _, db, *_ = _get_services(ctx)
    rows = db.list_ca_certs()
    if not rows:
        click.echo("Нет CA в базе")
        return
    click.echo(f"{'ID':<30} {'Name':<20} {'Created'}")
    click.echo("-" * 70)
    for r in rows:
        click.echo(f"{r['id']:<30} {r['name']:<20} {r['created_at'][:10]}")


# ── Cert ──────────────────────────────────────────────────────────────────────

@pki_cli.group()
def cert():
    """Управление сертификатами"""
    pass


@cert.command("issue-server")
@click.option("--cn", required=True, help="Common name")
@click.option("--san", multiple=True, required=True, help="SAN DNS (можно несколько)")
@click.option("--ca", "ca_id", required=True, help="CA id")
@click.option("--out", default=".", show_default=True, help="Output directory")
@click.pass_context
def cert_issue_server(ctx, cn, san, ca_id, out):
    """Выпустить серверный сертификат"""
    _, db, ca_svc, crl_svc, cert_svc, _ = _get_services(ctx)
    key, certificate = cert_svc.issue_server_certificate(cn, list(san), ca_id)
    out_dir = Path(out)
    _save_pem(certificate.public_bytes(Encoding.PEM), out_dir / f"{cn}.cert.pem")
    _save_pem(key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()), out_dir / f"{cn}.key.pem")
    click.echo(f"✅ Server cert: {cn} | serial: {format(certificate.serial_number, 'x')}")


@cert.command("issue-client")
@click.option("--user", required=True, help="User ID")
@click.option("--ca", "ca_id", required=True)
@click.option("--out", default=".", show_default=True)
@click.pass_context
def cert_issue_client(ctx, user, ca_id, out):
    """Выпустить клиентский сертификат"""
    _, db, ca_svc, crl_svc, cert_svc, _ = _get_services(ctx)
    key, certificate = cert_svc.issue_client_certificate(user, ca_id)
    out_dir = Path(out)
    _save_pem(certificate.public_bytes(Encoding.PEM), out_dir / f"{user}.cert.pem")
    _save_pem(key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()), out_dir / f"{user}.key.pem")
    click.echo(f"✅ Client cert: {user} | serial: {format(certificate.serial_number, 'x')}")


@cert.command("issue-firmware")
@click.option("--device", required=True, help="Device ID")
@click.option("--ca", "ca_id", required=True)
@click.option("--out", default=".", show_default=True)
@click.pass_context
def cert_issue_firmware(ctx, device, ca_id, out):
    """Выпустить firmware сертификат"""
    _, db, ca_svc, crl_svc, cert_svc, _ = _get_services(ctx)
    key, certificate = cert_svc.issue_firmware_certificate(device, ca_id)
    out_dir = Path(out)
    _save_pem(certificate.public_bytes(Encoding.PEM), out_dir / f"{device}.cert.pem")
    _save_pem(key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()), out_dir / f"{device}.key.pem")
    click.echo(f"✅ Firmware cert: {device} | serial: {format(certificate.serial_number, 'x')}")


@cert.command("list")
@click.pass_context
def cert_list(ctx):
    """Список выпущенных сертификатов"""
    _, db, ca_svc, crl_svc, cert_svc, _ = _get_services(ctx)
    certs = cert_svc._file_storage.list_certs()
    if not certs:
        click.echo("Нет сертификатов")
        return
    click.echo(f"{'Serial':<20} {'CN':<30} Path")
    click.echo("-" * 80)
    for c in certs:
        click.echo(f"{format(c['serial'], 'x')[:18]:<20} {c['cn']:<30} {c['path']}")


# ── CRL ───────────────────────────────────────────────────────────────────────

@pki_cli.group()
def crl():
    """Управление CRL и отзывом"""
    pass


@crl.command("revoke")
@click.option("--serial", required=True, help="Certificate serial (hex)")
@click.option("--ca", "ca_id", required=True)
@click.option("--reason", default="unspecified", show_default=True,
              help="Reason: unspecified|key_compromise|ca_compromise|...")
@click.pass_context
def crl_revoke(ctx, serial, ca_id, reason):
    """Отозвать сертификат"""
    _, db, ca_svc, crl_svc, *_ = _get_services(ctx)
    try:
        reason_flag = x509.ReasonFlags[reason]
    except KeyError:
        click.echo(f"❌ Неизвестный reason: {reason}", err=True)
        sys.exit(1)
    crl_svc.register_ca_cert(ca_id, ca_svc.get_ca_cert(ca_id))
    crl_svc.revoke_certificate(int(serial, 16), reason_flag)
    click.echo(f"✅ Отозван: {serial} (reason: {reason})")


@crl.command("generate")
@click.option("--ca", "ca_id", required=True)
@click.option("--out", default=None, help="Output file (default: stdout)")
@click.pass_context
def crl_generate(ctx, ca_id, out):
    """Сгенерировать CRL"""
    _, db, ca_svc, crl_svc, *_ = _get_services(ctx)
    crl_svc.register_ca_cert(ca_id, ca_svc.get_ca_cert(ca_id))
    crl_obj = crl_svc.generate_crl(ca_id)
    pem = crl_obj.public_bytes(Encoding.PEM)
    if out:
        Path(out).write_bytes(pem)
        click.echo(f"✅ CRL сохранён: {out}")
    else:
        click.echo(pem.decode())


@crl.command("check")
@click.option("--serial", required=True, help="Certificate serial (hex)")
@click.pass_context
def crl_check(ctx, serial):
    """Проверить статус сертификата"""
    _, db, ca_svc, crl_svc, cert_svc, ocsp_svc = _get_services(ctx)
    status = ocsp_svc.check_certificate_status(int(serial, 16))
    icon = "✅" if status.value == "good" else "❌"
    click.echo(f"{icon} Serial {serial}: {status.value.upper()}")


if __name__ == "__main__":
    pki_cli()
