#include <linux/bpf.h>
#include <bpf/bpf_helpers.h>

char LICENSE[] SEC("license") = "GPL";

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

struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 256);
    __type(key, __u32);
    __type(value, __u64);
} allowed_syscalls SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 4096);
    __type(key, __u32);
    __type(value, __u32);
} pid_to_domain SEC(".maps");

static __always_inline __u32 get_process_domain(__u32 pid) {
    __u32 *domain = bpf_map_lookup_elem(&pid_to_domain, &pid);
    return domain ? *domain : 0;
}

SEC("tracepoint/syscalls/sys_enter_openat")
int trace_syscall_enter(struct trace_event_raw_sys_enter *args) {
    __u64 pid_tgid = bpf_get_current_pid_tgid();
    __u32 pid = pid_tgid >> 32;
    __u32 domain_id = get_process_domain(pid);

    __u64 *allowed = bpf_map_lookup_elem(&allowed_syscalls, &domain_id);
    if (!allowed) {
        return 0;
    }

    __u32 syscall_nr = args->id;
    if (syscall_nr < 64 && !(*allowed & (1ULL << syscall_nr))) {
        bpf_printk("Blocked syscall %d for domain %d\n", syscall_nr, domain_id);
        bpf_send_signal(SIGSYS);
        return 0;
    }

    return 0;
}
