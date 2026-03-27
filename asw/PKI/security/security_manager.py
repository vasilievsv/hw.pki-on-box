# src/security/security_manager.py
import ctypes
import os
import subprocess
from enum import Enum

class SecurityDomain(Enum):
    PKI_CORE = 1
    PKI_HSM = 2
    UNTRUSTED = 3

class SecurityManager:
    """Управление SELinux и eBPF политиками"""
    
    def __init__(self):
        self.ebpf_programs = {}
        self.selinux_loaded = False
        
    def initialize_security(self):
        """Инициализация системы безопасности"""
        self._load_selinux_policy()
        self._load_ebpf_programs()
        self._configure_process_isolation()
        
    def _load_selinux_policy(self):
        """Загрузка SELinux политики"""
        try:
            # Компиляция и загрузка политики
            subprocess.run([
                'checkmodule', '-M', '-m', '-o', 
                'pki-box.mod', 'selinux/pki-box.te'
            ], check=True)
            
            subprocess.run([
                'semodule_package', '-o', 'pki-box.pp', 
                '-m', 'pki-box.mod', '-f', 'selinux/pki-box.fc'
            ], check=True)
            
            subprocess.run(['semodule', '-i', 'pki-box.pp'], check=True)
            
            # Установка контекстов файлов
            subprocess.run([
                'restorecon', '-R', '/var/lib/pki-box',
                '/var/log/pki-box', '/etc/pki-box'
            ], check=True)
            
            self.selinux_loaded = True
            print("✅ SELinux политика загружена")
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Ошибка загрузки SELinux: {e}")
            
    def _load_ebpf_programs(self):
        """Загрузка eBPF программ"""
        try:
            # Загрузка фильтра syscall
            subprocess.run([
                'bpftool', 'prog', 'load', 
                'ebpf/syscall_filter.o', '/sys/fs/bpf/syscall_filter'
            ], check=True)
            
            # Загрузка сетевого фильтра
            subprocess.run([
                'bpftool', 'prog', 'load',
                'ebpf/network_filter.o', '/sys/fs/bpf/network_filter'  
            ], check=True)
            
            # Настройка карт eBPF
            self._configure_ebpf_maps()
            print("✅ eBPF программы загружены")
            
        except Exception as e:
            print(f"❌ Ошибка загрузки eBPF: {e}")
    
    def _configure_ebpf_maps(self):
        """Настройка eBPF карт с политиками"""
        # Разрешенные syscall для PKI Core
        pki_core_syscalls = self._get_allowed_syscalls(SecurityDomain.PKI_CORE)
        subprocess.run([
            'bpftool', 'map', 'update', 'pinned',
            '/sys/fs/bpf/syscall_filter/allowed_syscalls',
            'key', '1', 'value', hex(pki_core_syscalls)
        ], check=True)
        
        # Разрешенные syscall для HSM
        hsm_syscalls = self._get_allowed_syscalls(SecurityDomain.PKI_HSM)
        subprocess.run([
            'bpftool', 'map', 'update', 'pinned', 
            '/sys/fs/bpf/syscall_filter/allowed_syscalls',
            'key', '2', 'value', hex(hsm_syscalls)
        ], check=True)
    
    def switch_security_domain(self, domain: SecurityDomain):
        """Переключение домена безопасности для текущего процесса"""
        if not self.selinux_loaded:
            return
            
        context_map = {
            SecurityDomain.PKI_CORE: "pki_core_t",
            SecurityDomain.PKI_HSM: "pki_hsm_t", 
            SecurityDomain.UNTRUSTED: "unconfined_t"
        }
        
        context = context_map[domain]
        
        # Установка SELinux контекста
        with open(f"/proc/self/attr/current", "w") as f:
            f.write(context)
        
        # Установка домена в eBPF карту
        self._set_ebpf_domain(os.getpid(), domain.value)
    
    def _get_allowed_syscalls(self, domain: SecurityDomain) -> int:
        """Получение битовой маски разрешенных syscall"""
        # Базовые syscall для всех процессов
        base_syscalls = {
            'read', 'write', 'open', 'close', 'mmap',
            'mprotect', 'munmap', 'brk', 'rt_sigaction'
        }
        
        domain_syscalls = {
            SecurityDomain.PKI_CORE: base_syscalls | {
                'socket', 'connect', 'bind', 'listen', 'accept',
                'clone', 'fork', 'execve', 'wait4'
            },
            SecurityDomain.PKI_HSM: base_syscalls | {
                'ioctl', 'fcntl', 'flock'  # Только файловые операции
            },
            SecurityDomain.UNTRUSTED: base_syscalls
        }
        
        return self._syscalls_to_bitmask(domain_syscalls[domain])