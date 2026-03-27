// eBPF для контроля системных вызовов
// pki-box/ebpf/syscall_filter.c


#include <linux/bpf.h>
#include <bpf/bpf_helpers.h>

struct syscall_event {
    __u32 pid;
    __u32 syscall_nr;
    char comm[16];
};

struct {
    __uint(type, BPF_MAP_TYPE_PERF_EVENT_ARRAY);
    __uint(key_size, sizeof(__u32));
    __uint(value_size, sizeof(__u32));
} events SEC(".maps");

// Карта разрешенных syscall для каждого домена
struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 256);
    __type(key, __u32);  // domain_id
    __type(value, __u64); // bitmask разрешенных syscall
} allowed_syscalls SEC(".maps");

SEC("tracepoint/syscalls/sys_enter_*")
int trace_syscall_enter(struct trace_event_raw_sys_enter *args) {
    __u64 pid_tgid = bpf_get_current_pid_tgid();
    __u32 pid = pid_tgid >> 32;
    __u32 domain_id = get_process_domain(pid); // наша функция
    
    // Получаем битовую маску разрешенных syscall для домена
    __u64 *allowed = bpf_map_lookup_elem(&allowed_syscalls, &domain_id);
    if (!allowed) {
        // Домен не найден - блокируем все
        bpf_send_signal(SIGKILL);
        return 0;
    }
    
    // Проверяем разрешен ли этот syscall
    __u32 syscall_nr = args->id;
    if (!(*allowed & (1ULL << syscall_nr))) {
        bpf_printk("Blocked syscall %d for domain %d\n", syscall_nr, domain_id);
        bpf_send_signal(SIGSYS);
        return 0;
    }
    
    return 0;
}