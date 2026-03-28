import sqlite3
import datetime
from pathlib import Path
from cryptography import x509
from cryptography.hazmat.primitives.serialization import Encoding


class PKIDatabase:
    def __init__(self, db_path: str = "asw/PKI/storage/pki.db"):
        self._path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS ca_certificates (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    cert_pem TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS certificates (
                    serial TEXT PRIMARY KEY,
                    common_name TEXT NOT NULL,
                    cert_pem TEXT NOT NULL,
                    ca_id TEXT NOT NULL,
                    issued_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    status TEXT DEFAULT 'active'
                );
                CREATE TABLE IF NOT EXISTS revoked_certificates (
                    serial TEXT PRIMARY KEY,
                    reason TEXT NOT NULL,
                    revoked_at TEXT NOT NULL
                );
            """)

    def _now(self) -> str:
        return datetime.datetime.now(datetime.timezone.utc).isoformat()

    def _cert_to_pem(self, cert: x509.Certificate) -> str:
        return cert.public_bytes(Encoding.PEM).decode()

    def _pem_to_cert(self, pem: str) -> x509.Certificate:
        return x509.load_pem_x509_certificate(pem.encode())

    def store_ca_cert(self, ca_id: str, name: str, cert: x509.Certificate) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO ca_certificates (id, name, cert_pem, created_at) VALUES (?,?,?,?)",
                (ca_id, name, self._cert_to_pem(cert), self._now()),
            )

    def load_ca_cert(self, ca_id: str) -> x509.Certificate | None:
        with self._connect() as conn:
            row = conn.execute("SELECT cert_pem FROM ca_certificates WHERE id=?", (ca_id,)).fetchone()
        return self._pem_to_cert(row["cert_pem"]) if row else None

    def list_ca_certs(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute("SELECT id, name, created_at FROM ca_certificates").fetchall()
        return [dict(r) for r in rows]

    def store_certificate(self, cert: x509.Certificate, ca_id: str) -> None:
        serial = format(cert.serial_number, "x")
        cn = cert.subject.get_attributes_for_oid(x509.oid.NameOID.COMMON_NAME)
        common_name = cn[0].value if cn else ""
        issued = cert.not_valid_before_utc.isoformat()
        expires = cert.not_valid_after_utc.isoformat()
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO certificates (serial, common_name, cert_pem, ca_id, issued_at, expires_at, status) VALUES (?,?,?,?,?,?,?)",
                (serial, common_name, self._cert_to_pem(cert), ca_id, issued, expires, "active"),
            )

    def load_certificate(self, serial: int) -> x509.Certificate | None:
        serial_hex = format(serial, "x")
        with self._connect() as conn:
            row = conn.execute("SELECT cert_pem FROM certificates WHERE serial=?", (serial_hex,)).fetchone()
        return self._pem_to_cert(row["cert_pem"]) if row else None

    def revoke_certificate(self, serial: int, reason: x509.ReasonFlags) -> None:
        serial_hex = format(serial, "x")
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO revoked_certificates (serial, reason, revoked_at) VALUES (?,?,?)",
                (serial_hex, reason.name, self._now()),
            )
            conn.execute("UPDATE certificates SET status='revoked' WHERE serial=?", (serial_hex,))

    def get_revoked(self, ca_id: str) -> dict[int, x509.ReasonFlags]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT r.serial, r.reason FROM revoked_certificates r "
                "JOIN certificates c ON c.serial=r.serial WHERE c.ca_id=?",
                (ca_id,),
            ).fetchall()
        return {int(r["serial"], 16): x509.ReasonFlags[r["reason"]] for r in rows}

    def is_revoked(self, serial: int) -> bool:
        serial_hex = format(serial, "x")
        with self._connect() as conn:
            row = conn.execute("SELECT 1 FROM revoked_certificates WHERE serial=?", (serial_hex,)).fetchone()
        return row is not None
