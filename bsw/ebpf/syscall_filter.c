// eBPF tracepoint: мониторинг syscall для PKI-box процессов
// Режим: audit (логирование), не enforcement (LSM недоступен)

#include <linux/bpf.h>

#define SEC(NAME) __attribute__((section(NAME), used))
#define __uint(name, val) int (*name)[val]
#define __type(name, val) typeof(val) *name

static void *(*bpf_map_lookup_elem)(void *map, const void *key) =
    (void *) 1;
static long (*bpf_map_update_elem)(void *map, const void *key,
    const void *value, __u64 flags) =
    (void *) 2;
static __u64 (*bpf_get_current_pid_tgid)(void) =
    (void *) 14;
static long (*bpf_get_current_comm)(void *buf, __u32 size) =
    (void *) 16;
static long (*bpf_perf_event_output)(void *ctx, void *map,
    __u64 flags, void *data, __u64 size) =
    (void *) 25;
static long (*bpf_trace_printk)(const char *fmt, __u32 fmt_size, ...) =
    (void *) 6;

struct syscall_event {
    __u32 pid;
    __u32 syscall_nr;
    char comm[16];
};

struct sys_enter_args {
    unsigned long long unused;
    long id;
    unsigned long args[6];
};

struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 16);
    __type(key, __u32);
    __type(value, __u8);
} pki_monitored_pids SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_PERF_EVENT_ARRAY);
    __uint(key_size, sizeof(__u32));
    __uint(value_size, sizeof(__u32));
} syscall_events SEC(".maps");

struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 512);
    __type(key, __u64);
    __type(value, __u64);
} syscall_counter SEC(".maps");

SEC("tracepoint/raw_syscalls/sys_enter")
int trace_sys_enter(struct sys_enter_args *ctx) {
    __u64 pid_tgid = bpf_get_current_pid_tgid();
    __u32 pid = pid_tgid >> 32;

    __u8 *monitored = bpf_map_lookup_elem(&pki_monitored_pids, &pid);
    if (!monitored)
        return 0;

    __u32 syscall_nr = (__u32)ctx->id;

    __u64 key = ((__u64)pid << 32) | syscall_nr;
    __u64 *cnt = bpf_map_lookup_elem(&syscall_counter, &key);
    if (cnt) {
        __u64 new_val = *cnt + 1;
        bpf_map_update_elem(&syscall_counter, &key, &new_val, 0);
    } else {
        __u64 one = 1;
        bpf_map_update_elem(&syscall_counter, &key, &one, 0);
    }

    struct syscall_event evt = {};
    evt.pid = pid;
    evt.syscall_nr = syscall_nr;
    bpf_get_current_comm(&evt.comm, sizeof(evt.comm));

    bpf_perf_event_output(ctx, &syscall_events, 0xffffffffULL,
                          &evt, sizeof(evt));
    return 0;
}

char _license[] SEC("license") = "GPL";
