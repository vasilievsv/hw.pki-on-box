import ctypes
import logging
import os
import platform
import shutil
import subprocess
from enum import Enum

logger = logging.getLogger(__name__)

SYSCALL_NR = {
    'read': 0, 'write': 1, 'open': 2, 'close': 3,
    'mmap': 9, 'mprotect': 10, 'munmap': 11, 'brk': 12,
    'rt_sigaction': 13, 'ioctl': 16, 'fcntl': 72, 'flock': 73,
    'socket': 41, 'connect': 42, 'accept': 43, 'bind': 49,
    'listen': 50, 'clone': 56, 'fork': 57, 'execve': 59, 'wait4': 61,
}

BSW_BASE = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'bsw')


class SecurityDomain(Enum):
    PKI_CORE = 1
    PKI_HSM = 2
    UNTRUSTED = 3


class SecurityCapabilities:
    def __init__(self):
        self.is_linux = platform.system() == 'Linux'
        self.has_selinux = False
        self.has_ebpf = False
        self.has_bpftool = False
        if self.is_linux:
            self.has_selinux = (
                os.path.isfile('/sys/fs/selinux/enforce')
                or os.path.isfile('/etc/selinux/config')
            )
            self.has_ebpf = os.path.isdir('/sys/fs/bpf')
            self.has_bpftool = shutil.which('bpftool') is not None

    def summary(self):
        return {
            'linux': self.is_linux,
            'selinux': self.has_selinux,
            'ebpf': self.has_ebpf,
            'bpftool': self.has_bpftool,
        }


class SecurityManager:
    def __init__(self, bsw_path=None):
        self.bsw_path = bsw_path or os.path.abspath(BSW_BASE)
        self.caps = SecurityCapabilities()
        self.selinux_loaded = False
        self.ebpf_loaded = False
        self.domain = SecurityDomain.UNTRUSTED

    def initialize_security(self):
        caps = self.caps.summary()
        logger.info("Security caps: %s", caps)

        if caps['selinux']:
            self._load_selinux_policy()
        else:
            logger.warning("SELinux unavailable, skipping policy load")

        if caps['ebpf'] and caps['bpftool']:
            self._load_ebpf_programs()
        else:
            logger.warning("eBPF unavailable, skipping program load")

        self._configure_process_isolation()
        return caps

    def _load_selinux_policy(self):
        selinux_dir = os.path.join(self.bsw_path, 'selinux')
        te_file = os.path.join(selinux_dir, 'pki-box.te')
        fc_file = os.path.join(selinux_dir, 'pki-box.fc')
        mod_file = os.path.join(selinux_dir, 'pki-box.mod')
        pp_file = os.path.join(selinux_dir, 'pki-box.pp')

        try:
            subprocess.run(
                ['checkmodule', '-M', '-m', '-o', mod_file, te_file],
                check=True, capture_output=True,
            )
            subprocess.run(
                ['semodule_package', '-o', pp_file, '-m', mod_file, '-f', fc_file],
                check=True, capture_output=True,
            )
            subprocess.run(
                ['semodule', '-i', pp_file],
                check=True, capture_output=True,
            )
            subprocess.run(
                ['restorecon', '-R', '/var/lib/pki-box', '/var/log/pki-box', '/etc/pki-box'],
                check=True, capture_output=True,
            )
            self.selinux_loaded = True
            logger.info("SELinux policy loaded")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.error("SELinux load failed: %s", e)

    def _load_ebpf_programs(self):
        ebpf_dir = os.path.join(self.bsw_path, 'ebpf')
        programs = {
            'syscall_filter': os.path.join(ebpf_dir, 'syscall_filter.o'),
            'network_filter': os.path.join(ebpf_dir, 'network_filter.o'),
        }
        try:
            for name, obj_path in programs.items():
                pin_path = '/sys/fs/bpf/{}'.format(name)
                subprocess.run(
                    ['bpftool', 'prog', 'load', obj_path, pin_path],
                    check=True, capture_output=True,
                )
            self._configure_ebpf_maps()
            self.ebpf_loaded = True
            logger.info("eBPF programs loaded")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.error("eBPF load failed: %s", e)

    def _configure_ebpf_maps(self):
        for domain in (SecurityDomain.PKI_CORE, SecurityDomain.PKI_HSM):
            bitmask = self._get_allowed_syscalls(domain)
            subprocess.run(
                [
                    'bpftool', 'map', 'update', 'pinned',
                    '/sys/fs/bpf/syscall_filter/allowed_syscalls',
                    'key', str(domain.value), 'value', hex(bitmask),
                ],
                check=True, capture_output=True,
            )

    def _configure_process_isolation(self):
        if not self.caps.is_linux:
            logger.info("Not Linux, process isolation skipped")
            return
        try:
            import resource
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
            logger.info("Core dumps disabled")
        except Exception as e:
            logger.warning("Could not disable core dumps: %s", e)

    def switch_security_domain(self, domain):
        self.domain = domain
        if self.selinux_loaded:
            self._set_selinux_context(domain)
        if self.ebpf_loaded:
            self._set_ebpf_domain(os.getpid(), domain.value)
        logger.info("Switched to domain: %s", domain.name)

    def _set_selinux_context(self, domain):
        context_map = {
            SecurityDomain.PKI_CORE: "pki_core_t",
            SecurityDomain.PKI_HSM: "pki_hsm_t",
            SecurityDomain.UNTRUSTED: "unconfined_t",
        }
        try:
            with open("/proc/self/attr/current", "w") as f:
                f.write(context_map[domain])
        except (IOError, OSError) as e:
            logger.error("SELinux context switch failed: %s", e)

    def _set_ebpf_domain(self, pid, domain_value):
        try:
            subprocess.run(
                [
                    'bpftool', 'map', 'update', 'pinned',
                    '/sys/fs/bpf/syscall_filter/pid_to_domain',
                    'key', str(pid), 'value', str(domain_value),
                ],
                check=True, capture_output=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.error("eBPF domain switch failed: %s", e)

    def _get_allowed_syscalls(self, domain):
        base = {'read', 'write', 'open', 'close', 'mmap', 'mprotect', 'munmap', 'brk', 'rt_sigaction'}
        domain_extra = {
            SecurityDomain.PKI_CORE: {'socket', 'connect', 'bind', 'listen', 'accept', 'clone', 'fork', 'execve', 'wait4'},
            SecurityDomain.PKI_HSM: {'ioctl', 'fcntl', 'flock'},
            SecurityDomain.UNTRUSTED: set(),
        }
        return self._syscalls_to_bitmask(base | domain_extra[domain])

    @staticmethod
    def _syscalls_to_bitmask(syscall_names):
        mask = 0
        for name in syscall_names:
            nr = SYSCALL_NR.get(name)
            if nr is not None and nr < 64:
                mask |= (1 << nr)
        return mask

    def get_status(self):
        return {
            'capabilities': self.caps.summary(),
            'selinux_loaded': self.selinux_loaded,
            'ebpf_loaded': self.ebpf_loaded,
            'current_domain': self.domain.name,
        }
