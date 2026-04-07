from typing import Optional, List
import shutil
from pathlib import Path
from cryptography import x509
from cryptography.hazmat.primitives.serialization import Encoding


class CertificateFileStorage:
    def __init__(self, base_path: str = "asw/PKI/storage/certs"):
        self._base = Path(base_path)
        self._by_label = self._base / "by_label"
        self._base.mkdir(parents=True, exist_ok=True)
        self._by_label.mkdir(parents=True, exist_ok=True)

    def _serial_hex(self, cert: x509.Certificate) -> str:
        return format(cert.serial_number, "x")

    def _pem_bytes(self, cert: x509.Certificate) -> bytes:
        return cert.public_bytes(Encoding.PEM)

    def _der_bytes(self, cert: x509.Certificate) -> bytes:
        return cert.public_bytes(Encoding.DER)

    def store_cert(self, cert: x509.Certificate, label: str = None) -> Path:
        serial_hex = self._serial_hex(cert)
        dest = self._base / f"{serial_hex}.pem"
        dest.write_bytes(self._pem_bytes(cert))
        if label:
            label_path = self._by_label / f"{label}.pem"
            shutil.copy2(dest, label_path)
        return dest

    def load_cert(self, serial: int) -> Optional[x509.Certificate]:
        path = self._base / f"{format(serial, 'x')}.pem"
        if not path.exists():
            return None
        return x509.load_pem_x509_certificate(path.read_bytes())

    def load_cert_by_label(self, label: str) -> Optional[x509.Certificate]:
        path = self._by_label / f"{label}.pem"
        if not path.exists():
            return None
        return x509.load_pem_x509_certificate(path.read_bytes())

    def export_pem(self, serial: int, dest: Path) -> None:
        cert = self.load_cert(serial)
        if cert is None:
            raise FileNotFoundError(f"cert {format(serial, 'x')} not found")
        dest.write_bytes(self._pem_bytes(cert))

    def export_der(self, serial: int, dest: Path) -> None:
        cert = self.load_cert(serial)
        if cert is None:
            raise FileNotFoundError(f"cert {format(serial, 'x')} not found")
        dest.write_bytes(self._der_bytes(cert))

    def list_certs(self) -> List[dict]:
        result = []
        for pem_file in sorted(self._base.glob("*.pem")):
            cert = x509.load_pem_x509_certificate(pem_file.read_bytes())
            cn_attrs = cert.subject.get_attributes_for_oid(x509.oid.NameOID.COMMON_NAME)
            result.append({
                "serial": cert.serial_number,
                "cn": cn_attrs[0].value if cn_attrs else "",
                "path": str(pem_file),
            })
        return result
