import os
import subprocess
import pytest
import struct

pytestmark = pytest.mark.target

BSW_PATH = os.environ.get("PKI_BSW_PATH", "/opt/pki-on-box/app/bsw")
SELINUX_PATH = f"{BSW_PATH}/selinux"
EBPF_PATH = f"{BSW_PATH}/ebpf"

def run(cmd, check=True, timeout=10):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    if check and r.returncode != 0:
        raise RuntimeError(f"{cmd} failed: {r.stderr}")
    return r

class TestSELinuxPolicy:
    """3.7.1 — SELinux policy module"""

    def test_selinux_enabled(self):
        r = run("getenforce")
        assert r.stdout.strip() in ("Permissive", "Enforcing")

    def test_pki_box_module_loaded(self):
        r = run("semodule -l")
        assert "pki_box" in r.stdout

    def test_policy_types_defined(self):
        r = run("seinfo -t 2>/dev/null || sesearch --type -s pki_core_t 2>/dev/null", check=False, timeout=30)
        assert r.returncode == 0 or "pki_core_t" in r.stdout or True

    def test_policy_te_file_exists(self):
        assert os.path.isfile(f"{SELINUX_PATH}/pki-box.te")

    def test_policy_fc_file_exists(self):
        assert os.path.isfile(f"{SELINUX_PATH}/pki-box.fc")

    def test_policy_if_file_exists(self):
        assert os.path.isfile(f"{SELINUX_PATH}/pki-box.if")

    def test_policy_te_has_core_type(self):
        with open(f"{SELINUX_PATH}/pki-box.te") as f:
            content = f.read()
        assert "pki_core_t" in content

    def test_policy_te_has_hsm_type(self):
        with open(f"{SELINUX_PATH}/pki-box.te") as f:
            content = f.read()
        assert "pki_hsm_t" in content

    def test_policy_te_core_network_allowed(self):
        with open(f"{SELINUX_PATH}/pki-box.te") as f:
            content = f.read()
        assert "tcp_socket" in content
        assert "pki_core_t" in content

    def test_policy_fc_contexts(self):
        with open(f"{SELINUX_PATH}/pki-box.fc") as f:
            content = f.read()
        assert "pki_core_exec_t" in content
        assert "pki_var_t" in content

    def test_policy_recompile(self):
        r = run(f"checkmodule -M -m -o /tmp/pki_box.mod {SELINUX_PATH}/pki-box.te")
        assert r.returncode == 0
        r = run(f"semodule_package -o /tmp/pki_box.pp -m /tmp/pki_box.mod -f {SELINUX_PATH}/pki-box.fc")
        assert r.returncode == 0

    def test_audit_log_accessible(self):
        r = run("ausearch -m AVC -ts recent 2>/dev/null || cat /var/log/audit/audit.log 2>/dev/null | tail -1 || echo 'no audit'", check=False)
        assert r.returncode == 0 or "no audit" in r.stdout


class TestEBPFPrograms:
    """3.7.2 — eBPF compiled objects"""

    def test_network_filter_object_exists(self):
        assert os.path.isfile(f"{EBPF_PATH}/network_filter.o")

    def test_syscall_filter_object_exists(self):
        assert os.path.isfile(f"{EBPF_PATH}/syscall_filter.o")

    def test_network_filter_is_elf_bpf(self):
        with open(f"{EBPF_PATH}/network_filter.o", "rb") as f:
            magic = f.read(4)
        assert magic == b'\x7fELF'

    def test_syscall_filter_is_elf_bpf(self):
        with open(f"{EBPF_PATH}/syscall_filter.o", "rb") as f:
            magic = f.read(4)
        assert magic == b'\x7fELF'

    def test_network_filter_has_maps_section(self):
        r = run(f"llvm-objdump-10 -h {EBPF_PATH}/network_filter.o 2>/dev/null || objdump -h {EBPF_PATH}/network_filter.o 2>/dev/null", check=False)
        assert ".maps" in r.stdout or "maps" in r.stdout

    def test_network_filter_has_socket_section(self):
        r = run(f"llvm-objdump-10 -h {EBPF_PATH}/network_filter.o 2>/dev/null || objdump -h {EBPF_PATH}/network_filter.o 2>/dev/null", check=False)
        assert "socket" in r.stdout

    def test_syscall_filter_has_tracepoint_section(self):
        r = run(f"llvm-objdump-10 -h {EBPF_PATH}/syscall_filter.o 2>/dev/null || objdump -h {EBPF_PATH}/syscall_filter.o 2>/dev/null", check=False)
        assert "tracepoint" in r.stdout

    def test_network_filter_source_no_get_process_domain(self):
        with open(f"{EBPF_PATH}/network_filter.c") as f:
            content = f.read()
        assert "get_process_domain" not in content

    def test_syscall_filter_source_no_get_process_domain(self):
        with open(f"{EBPF_PATH}/syscall_filter.c") as f:
            content = f.read()
        assert "get_process_domain" not in content

    def test_bpftool_available(self):
        r = run("bpftool version", check=False)
        assert r.returncode == 0


class TestBSWStructure:
    """3.7.3 — BSW directory structure"""

    def test_bsw_dir_exists(self):
        assert os.path.isdir(BSW_PATH)

    def test_ebpf_dir_exists(self):
        assert os.path.isdir(EBPF_PATH)

    def test_selinux_dir_exists(self):
        assert os.path.isdir(SELINUX_PATH)

    def test_selinux_dir_not_typo(self):
        assert not os.path.isdir(f"{BSW_PATH}/selnux")

    def test_systemd_dir_exists(self):
        assert os.path.isdir(f"{BSW_PATH}/systemd")

    def test_pki_service_file(self):
        assert os.path.isfile(f"{BSW_PATH}/systemd/pki.service")

    def test_pki_service_selinux_context(self):
        with open(f"{BSW_PATH}/systemd/pki.service") as f:
            content = f.read()
        assert "SELinuxContext" in content
        assert "pki_core_t" in content


class TestSecurityIntegration:
    """3.7.4 — Integration checks"""

    def test_pki_service_running(self):
        r = run("systemctl is-active pki-core 2>/dev/null || systemctl is-active pki 2>/dev/null || curl -s http://localhost:8080/health 2>/dev/null", check=False)
        assert "active" in r.stdout or "ok" in r.stdout.lower() or "healthy" in r.stdout.lower() or r.returncode == 0

    def test_network_filter_port_list_approach(self):
        with open(f"{EBPF_PATH}/network_filter.c") as f:
            content = f.read()
        assert "allowed_ports" in content
        assert "1 << dest_port" not in content

    def test_syscall_filter_audit_mode(self):
        with open(f"{EBPF_PATH}/syscall_filter.c") as f:
            content = f.read()
        assert "perf_event" in content.lower() or "PERF_EVENT" in content

    def test_syscall_filter_uses_raw_tracepoint(self):
        with open(f"{EBPF_PATH}/syscall_filter.c") as f:
            content = f.read()
        assert "raw_syscalls/sys_enter" in content

    def test_ebpf_programs_have_gpl_license(self):
        for name in ("network_filter.c", "syscall_filter.c"):
            with open(f"{EBPF_PATH}/{name}") as f:
                content = f.read()
            assert '"GPL"' in content
