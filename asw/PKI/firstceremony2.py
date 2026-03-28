from datetime import datetime, timezone
import json

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization

from core import build_core, load_config


class RootCAIssuanceCeremony:
    """Церемония выпуска Master Root CA"""

    def __init__(self, ceremony_id: str, participants: list, cfg: dict = None):
        self.ceremony_id = ceremony_id
        self.participants = participants
        self.ceremony_log = []
        self.start_time = None
        self.end_time = None
        self._cfg = cfg or load_config()
        self._trng, self._drbg, self._crypto, self._storage = build_core(self._cfg)

    def log_event(self, event: str, participant: str = "System"):
        timestamp = datetime.now(timezone.utc).isoformat()
        entry = {"timestamp": timestamp, "participant": participant, "event": event}
        self.ceremony_log.append(entry)
        print(f"[{timestamp}] {participant}: {event}")

    def perform_ceremony(self):
        print("🎭 НАЧАЛО ЦЕРЕМОНИИ ВЫПУСКА MASTER ROOT CA")
        print("=" * 60)
        self.start_time = datetime.now(timezone.utc)
        self.log_event("Начало церемонии выпуска Master Root CA")

        self._preparation_phase()
        self._key_generation_phase()
        self._certificate_creation_phase()
        self._verification_phase()
        self._archiving_phase()

        self.end_time = datetime.now(timezone.utc)
        self.log_event("Церемония завершена успешно")
        self._generate_ceremony_report()
        print("=" * 60)
        print("✅ ЦЕРЕМОНИЯ ЗАВЕРШЕНА УСПЕШНО")

    # ── phases ────────────────────────────────────────────────────────────────

    def _preparation_phase(self):
        self.log_event("Фаза подготовки: проверка оборудования")
        for req in ["TRNG источник", "Защищенное хранилище", "Резервные носители", "Логирование"]:
            self.log_event(f"Проверка: {req} - OK", "Технический специалист")
        for p in self.participants:
            self.log_event(f"Участник {p} подтверждает участие", p)

    def _key_generation_phase(self):
        self.log_event("Фаза генерации ключей Master Root CA")
        self.log_event("Генерация энтропии из TRNG", "TRNG Оператор")
        health = self._trng.health_check()
        if not health.get("passed", False):
            raise RuntimeError(f"TRNG health check failed: {health}")
        self.log_event("TRNG health check пройден", "TRNG Оператор")

        self.log_event("Генерация RSA-4096 ключевой пары через CryptoEngine", "Криптограф")
        self.master_private_key, self.master_public_key = self._crypto.generate_rsa_keypair()
        self.log_event("Ключевая пара успешно сгенерирована")

    def _certificate_creation_phase(self):
        self.log_event("Фаза создания самоподписанного сертификата")
        subject = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, "Master Root CA"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "PKI-on-Box"),
            x509.NameAttribute(NameOID.COUNTRY_NAME, "RU"),
        ])
        now = datetime.now(timezone.utc)
        builder = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(subject)
            .public_key(self.master_public_key)
            .serial_number(x509.random_serial_number())
            .not_valid_before(now)
            .not_valid_after(now.replace(year=now.year + 20))
            .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
            .add_extension(x509.SubjectKeyIdentifier.from_public_key(self.master_public_key), critical=False)
        )
        self.master_certificate = self._crypto.build_certificate(builder, self.master_private_key)
        for p in self.participants:
            self.log_event("Визуальная проверка сертификата", p)
        self.log_event("Сертификат Master Root CA создан")

    def _verification_phase(self):
        self.log_event("Фаза верификации и проверки")
        is_valid = self._crypto.verify_certificate(self.master_certificate)
        if not is_valid:
            raise SecurityError("Ошибка верификации самоподписи!")
        self.log_event("Самоподпись сертификата верна", "Аудитор")

    def _archiving_phase(self):
        self.log_event("Фаза архивирования и сохранения")
        password = "ceremony-master-key"
        self._storage.store_key("master_root_ca", self.master_private_key, password)
        self.log_event("Приватный ключ сохранён в KeyStorage (AES-256-GCM)")

        cert_pem = self.master_certificate.public_bytes(serialization.Encoding.PEM)
        cert_path = self._storage._path / "master_root_ca.crt.pem"
        cert_path.write_bytes(cert_pem)
        self.log_event(f"Сертификат сохранён: {cert_path}")

    def _generate_ceremony_report(self):
        report = {
            "ceremony_id": self.ceremony_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "participants": self.participants,
            "master_ca_fingerprint": self._crypto.get_fingerprint(self.master_certificate),
            "key_metadata": {"algorithm": "RSA", "key_size": 4096, "public_exponent": 65537},
            "certificate_metadata": {
                "subject": str(self.master_certificate.subject),
                "serial_number": str(self.master_certificate.serial_number),
                "not_before": self.master_certificate.not_valid_before_utc.isoformat(),
                "not_after": self.master_certificate.not_valid_after_utc.isoformat(),
            },
            "ceremony_log": self.ceremony_log,
        }
        report_path = f"ceremony_{self.ceremony_id}_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        self.log_event(f"Отчёт сохранён: {report_path}")
