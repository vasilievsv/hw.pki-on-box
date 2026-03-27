### Архитектура безопасности pki-box


```
┌─────────────────────────────────────────────────┐
│                  pki-box system                 │
├─────────────────────────────────────────────────┤
│  PKI Core (unconfined_t) ← eBPF filters → HSM   │
│               ↓                                 │
│        SELinux Policy Enforcement               │
│               ↓                                 │
│        Linux Kernel (SELinux + eBPF)            │
└─────────────────────────────────────────────────┘
```

#### обеспечивает микро-сегментацию на уровне ядра, где PKI Core и HSM работают в полностью изолированных контекстах безопасности


### Проверка безопасности

```
# Проверка SELinux контекстов
ps -eZ | grep pki-box
ls -Z /var/lib/pki-box/

# Проверка eBPF программ
bpftool prog show
bpftool map show

# Аудит SELinux
ausearch -m avc -ts recent
```