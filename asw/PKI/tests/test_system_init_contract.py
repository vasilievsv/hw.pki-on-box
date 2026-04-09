import os
import pytest

from core import build_core, load_config, run_kat, CryptoSelfTestError
from core.config import load_config as _load_config
from storage.database import PKIDatabase
from storage.file_storage import CertificateFileStorage
from services.ca_service import CertificateAuthorityService
from services.certificate_service import CertificateService
from services.crl_service import CRLService
from services.ocsp_service import OCSPResponder
from security.security_manager import (
    SecurityManager, SecurityCapabilities, SecurityDomain,
)


@pytest.fixture
def init_cfg(tmp_path):
    return {
        "trng": {"mode": "software"},
        "drbg": {"algorithm": "hmac-sha256", "reseed_interval": 1000, "personalization": ""},
        "crypto": {"rsa_key_size": 2048, "ec_curve": "P-384", "aes_key_size": 256},
        "storage": {
            "path": str(tmp_path / "keys"),
            "backend": "file",
            "db_path": str(tmp_path / "pki.db"),
            "certs_path": str(tmp_path / "certs"),
            "ca_key_password": "test-init-key",
        },
    }


@pytest.fixture
def full_stack(init_cfg):
    trng, drbg, crypto, key_storage = build_core(init_cfg)
    storage_cfg = init_cfg["storage"]
    db = PKIDatabase(storage_cfg["db_path"])
    file_storage = CertificateFileStorage(storage_cfg["certs_path"])
    ca_svc = CertificateAuthorityService(crypto, key_storage, db, init_cfg)
    crl_svc = CRLService(crypto, key_storage, ca_svc, db, init_cfg)
    cert_svc = CertificateService(crypto, key_storage, ca_svc, db, file_storage)
    ocsp_svc = OCSPResponder(crl_svc, crypto, init_cfg)
    return {
        "trng": trng, "drbg": drbg, "crypto": crypto,
        "key_storage": key_storage, "db": db,
        "ca_svc": ca_svc, "cert_svc": cert_svc,
        "crl_svc": crl_svc, "ocsp_svc": ocsp_svc,
    }


class TestSystemInitPreconditions:

    def test_kat_passes_before_build_core(self):
        run_kat()

    def test_kat_runs_during_build_core(self, init_cfg):
        trng, drbg, crypto, storage = build_core(init_cfg)
        assert crypto is not None

    def test_config_loads_defaults(self):
        cfg = _load_config()
        assert "trng" in cfg
        assert "drbg" in cfg
        assert "crypto" in cfg

    def test_software_trng_mode_accepted(self, init_cfg):
        trng, drbg, crypto, storage = build_core(init_cfg)
        assert trng is not None

    def test_storage_path_created(self, init_cfg):
        build_core(init_cfg)
        assert os.path.isdir(init_cfg["storage"]["path"])


class TestSystemInitPostconditions:

    def test_build_core_returns_four_components(self, init_cfg):
        result = build_core(init_cfg)
        assert len(result) == 4

    def test_trng_initialized(self, full_stack):
        trng = full_stack["trng"]
        health = trng.health_check()
        if isinstance(health, dict):
            assert health.get("passed", False) is True
        else:
            assert bool(health) is True

    def test_drbg_initialized(self, full_stack):
        drbg = full_stack["drbg"]
        assert drbg.initialized is True

    def test_crypto_engine_functional(self, full_stack):
        crypto = full_stack["crypto"]
        priv, pub = crypto.generate_rsa_keypair(bits=2048)
        assert priv.key_size == 2048

    def test_key_storage_functional(self, full_stack):
        storage = full_stack["key_storage"]
        keys = storage.list_keys()
        assert isinstance(keys, list)

    def test_database_initialized(self, full_stack):
        db = full_stack["db"]
        certs = db.list_ca_certs()
        assert isinstance(certs, list)

    def test_ca_service_functional(self, full_stack):
        ca_svc = full_stack["ca_svc"]
        cert = ca_svc.create_root_ca("Init-Test-CA", validity_years=1)
        assert cert is not None

    def test_full_stack_services_created(self, full_stack):
        for key in ("ca_svc", "cert_svc", "crl_svc", "ocsp_svc"):
            assert full_stack[key] is not None


class TestSystemInitSecurityManager:

    def test_security_capabilities_created(self):
        caps = SecurityCapabilities()
        summary = caps.summary()
        assert "linux" in summary
        assert "selinux" in summary
        assert "ebpf" in summary
        assert "bpftool" in summary

    def test_security_manager_created(self):
        sm = SecurityManager()
        assert sm.domain == SecurityDomain.UNTRUSTED

    def test_security_manager_initial_status(self):
        sm = SecurityManager()
        status = sm.get_status()
        assert status["current_domain"] == "UNTRUSTED"
        assert "capabilities" in status
        assert "selinux_loaded" in status
        assert "ebpf_loaded" in status

    def test_security_manager_domain_switch(self):
        sm = SecurityManager()
        sm.domain = SecurityDomain.PKI_CORE
        assert sm.domain == SecurityDomain.PKI_CORE
        sm.domain = SecurityDomain.PKI_HSM
        assert sm.domain == SecurityDomain.PKI_HSM


class TestSystemInitInvariants:

    def test_drbg_seeded_before_crypto(self, full_stack):
        drbg = full_stack["drbg"]
        assert drbg.initialized is True
        assert drbg._reseed_counter >= 0

    def test_kat_failure_prevents_init(self, init_cfg, monkeypatch):
        import core as core_pkg
        original = core_pkg.run_kat
        def bad_kat():
            raise CryptoSelfTestError("forced failure")
        monkeypatch.setattr(core_pkg, "run_kat", bad_kat)
        with pytest.raises(CryptoSelfTestError):
            build_core(init_cfg)

    def test_security_domains_enum_complete(self):
        domains = list(SecurityDomain)
        names = {d.name for d in domains}
        assert "PKI_CORE" in names
        assert "PKI_HSM" in names
        assert "UNTRUSTED" in names

    def test_hsm_domain_no_network_syscalls(self):
        sm = SecurityManager()
        allowed = sm._get_allowed_syscalls(SecurityDomain.PKI_HSM)
        fork_bit = 1 << 57
        execve_bit = 1 << 59
        socket_bit = 1 << 41
        assert allowed & fork_bit == 0
        assert allowed & execve_bit == 0
        assert allowed & socket_bit == 0

    def test_core_domain_has_network_syscalls(self):
        sm = SecurityManager()
        allowed = sm._get_allowed_syscalls(SecurityDomain.PKI_CORE)
        socket_bit = 1 << 41
        bind_bit = 1 << 49
        listen_bit = 1 << 50
        assert allowed & socket_bit != 0
        assert allowed & bind_bit != 0
        assert allowed & listen_bit != 0
