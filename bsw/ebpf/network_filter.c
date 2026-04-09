// eBPF socket_filter: контроль сетевого доступа PKI-box
// Фильтрация по dst port через BPF_MAP + bitmap

#include <linux/bpf.h>
#include <linux/if_ether.h>
#include <linux/ip.h>
#include <linux/tcp.h>
#include <linux/in.h>

#define SEC(NAME) __attribute__((section(NAME), used))
#define __uint(name, val) int (*name)[val]
#define __type(name, val) typeof(val) *name

static void *(*bpf_map_lookup_elem)(void *map, const void *key) =
    (void *) 1;
static long (*bpf_trace_printk)(const char *fmt, __u32 fmt_size, ...) =
    (void *) 6;

#ifndef htons
#define htons(x) ((__be16)__builtin_bswap16((__u16)(x)))
#endif
#ifndef ntohs
#define ntohs(x) ((__u16)__builtin_bswap16((__be16)(x)))
#endif

#define MAX_ALLOWED_PORTS 16

struct port_policy {
    __u16 allowed_ports[MAX_ALLOWED_PORTS];
    __u8  count;
    __u8  deny_all;
};

struct {
    __uint(type, BPF_MAP_TYPE_ARRAY);
    __uint(max_entries, 1);
    __type(key, __u32);
    __type(value, struct port_policy);
} pki_net_policy SEC(".maps");

SEC("socket")
int pki_socket_filter(struct __sk_buff *skb) {
    void *data = (void *)(long)skb->data;
    void *data_end = (void *)(long)skb->data_end;

    struct ethhdr *eth = data;
    if ((void *)(eth + 1) > data_end)
        return 0;
    if (eth->h_proto != htons(ETH_P_IP))
        return 0;

    struct iphdr *ip = (void *)(eth + 1);
    if ((void *)(ip + 1) > data_end)
        return 0;
    if (ip->protocol != IPPROTO_TCP)
        return 0;

    struct tcphdr *tcp = (void *)ip + (ip->ihl * 4);
    if ((void *)(tcp + 1) > data_end)
        return 0;

    __u16 dest_port = ntohs(tcp->dest);

    __u32 key = 0;
    struct port_policy *policy = bpf_map_lookup_elem(&pki_net_policy, &key);
    if (!policy)
        return 0;

    if (policy->deny_all)
        return 1;

    for (int i = 0; i < MAX_ALLOWED_PORTS; i++) {
        if (i >= policy->count)
            break;
        if (policy->allowed_ports[i] == dest_port)
            return 0;
    }

    return 1;
}

char _license[] SEC("license") = "GPL";
