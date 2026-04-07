#include <linux/bpf.h>
#include <bpf/bpf_helpers.h>
#include <linux/if_ether.h>
#include <linux/ip.h>
#include <linux/tcp.h>

char LICENSE[] SEC("license") = "GPL";

struct network_policy {
    __u32 allowed_ports;
    __u32 denied_ports;
};

struct {
    __uint(type, BPF_MAP_TYPE_HASH);
    __uint(max_entries, 10);
    __type(key, __u32);
    __type(value, struct network_policy);
} network_policies SEC(".maps");

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

SEC("socket")
int socket_filter(struct __sk_buff *skb) {
    __u64 pid_tgid = bpf_get_current_pid_tgid();
    __u32 pid = pid_tgid >> 32;
    __u32 domain_id = get_process_domain(pid);

    struct network_policy *policy = bpf_map_lookup_elem(&network_policies, &domain_id);
    if (!policy)
        return 0;

    void *data = (void *)(long)skb->data;
    void *data_end = (void *)(long)skb->data_end;

    struct ethhdr *eth = data;
    if ((void *)eth + sizeof(*eth) > data_end)
        return 0;

    if (eth->h_proto != __constant_htons(ETH_P_IP))
        return 0;

    struct iphdr *ip = data + sizeof(*eth);
    if ((void *)ip + sizeof(*ip) > data_end)
        return 0;

    if (ip->protocol != IPPROTO_TCP)
        return 0;

    struct tcphdr *tcp = (void *)ip + sizeof(*ip);
    if ((void *)tcp + sizeof(*tcp) > data_end)
        return 0;

    __u32 dest_port = __constant_ntohs(tcp->dest);

    if (dest_port < 32 && (policy->denied_ports & (1 << dest_port))) {
        bpf_printk("Blocked port %d domain %d\n", dest_port, domain_id);
        return 1;
    }

    return 0;
}
