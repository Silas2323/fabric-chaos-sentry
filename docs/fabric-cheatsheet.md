# Fabric Cheat Sheet

Living reference for the lab described in the root [README](../README.md).
Addressing, config templates, the verification ladder, EVPN route types,
RoCE notes, and one-liners — update this as things are learned or measured,
don't let it go stale.

## Addressing

| Node    | Loopback / Router-ID | ASN            | Role                    |
|---------|-----------------------|----------------|--------------------------|
| SPINE-1 | 10.0.0.1/32           | 65100 (shared) | EVPN relay only, no VTEP |
| SPINE-2 | 10.0.0.2/32           | 65100 (shared) | EVPN relay only, no VTEP |
| LEAF-1  | 10.0.0.11/32          | 65101          | VTEP, source of NVE      |
| LEAF-2  | 10.0.0.12/32          | 65102          | VTEP, source of NVE      |

| Tenant object       | Value                         |
|----------------------|--------------------------------|
| VLAN 10 → VNI        | 10010, gateway 10.10.10.254/24 |
| VLAN 20 → VNI        | 10020, gateway 10.10.20.254/24 |
| L3VNI (VRF TENANT1)  | 104001                        |
| Anycast gateway MAC  | 44:38:39:ff:00:01             |

Fabric links: SPINE swp1→LEAF-1, swp2→LEAF-2 (both spines). Leaf swp1/swp2
are uplinks; swp10/swp11 are server-facing access ports.

## Config templates (NVUE)

**BGP unnumbered underlay** (per node, adjust ASN/loopback):
```
nv set interface lo type loopback
nv set interface lo ip address <loopback>/32
nv set interface swp1-2 type swp
nv set router bgp autonomous-system <asn>
nv set router bgp router-id <loopback>
nv set router bgp state enabled
nv set vrf default router bgp neighbor swp1 type unnumbered
nv set vrf default router bgp neighbor swp1 remote-as external
nv set vrf default router bgp address-family ipv4-unicast redistribute connected state enabled
nv set vrf default router bgp address-family ipv4-unicast state enabled
```

**EVPN address-family — all four nodes, spines included:**
```
nv set vrf default router bgp address-family l2vpn-evpn state enabled
nv set vrf default router bgp neighbor swp1 address-family l2vpn-evpn state enabled
nv set vrf default router bgp neighbor swp2 address-family l2vpn-evpn state enabled
```
Skipping the spines here is the single most common mistake — they relay
EVPN routes between leaves even though they never terminate a VTEP.

**VXLAN + bridge — leaves only:**
```
nv set nve vxlan source address <leaf loopback>
nv set nve vxlan state enabled
nv set bridge domain br_default vlan 10 vni 10010
nv set bridge domain br_default vlan 20 vni 10020
nv set interface swp10 bridge domain br_default access 10
nv set interface swp11 bridge domain br_default access 20
```

**Symmetric IRB — leaves only, IP addresses first:**
```
nv set interface vlan10,20 type svi
nv set interface vlan10 vlan 10
nv set interface vlan10 ipv4 address 10.10.10.254/24
nv set interface vlan20 vlan 20
nv set interface vlan20 ipv4 address 10.10.20.254/24
nv set interface vlan10,20 vrf TENANT1
nv set evpn route-advertise svi-ip enabled
nv set evpn state enabled
nv set vrf TENANT1 evpn state enabled
nv set vrf TENANT1 evpn vni 104001
nv set system global anycast-mac 44:38:39:ff:00:01
```
Assign the IPv4 address in the same breath as creating the SVI — see
"SVI-created-but-unaddressed" in the README and [troubleshooting.md](troubleshooting.md).

## Verification ladder

`nv config apply` ≠ `nv config save` ≠ verified. A change isn't done until a
**fresh session** proves it — don't trust the terminal you typed the change
into. Climb this ladder in order; each rung's failure points at the layer
below it:

1. **Link/interface:** `nv show interface swpX` — link state up, correct type.
2. **Underlay BGP:** `nv show bgp summary` — session `Established`, **and**
   `PfxRcd` non-zero. Established with zero PfxRcd is up-but-useless — see
   troubleshooting.
3. **Underlay reachability:** loopback-to-loopback ping. `ttl=64` adjacent
   (single hop), `ttl=63` leaf-to-leaf through a spine (underlay only, no
   overlay routing yet).
4. **EVPN control plane, Type 3 first:** `nv show bgp l2vpn evpn route` —
   before any host has an IP, you should see **Type 3 (IMET) only**. This is
   the "before" checkpoint — screenshot it. `nv show evpn vni` should list
   the remote VTEP.
5. **EVPN control plane, Type 2:** bring up host IPs, ping same-leaf first
   (`nv show evpn mac vni <vni>` shows only local MACs), then cross-fabric
   (remote Type 2s appear, next-hop = the far leaf's loopback).
6. **Overlay routing (symmetric IRB):** cross-VLAN, cross-leaf ping. TTL
   decrements by 2 (64 → 62) — one hop per leaf's SVI. That two-hop TTL
   signature is the proof routing is symmetric, not hairpinned.
7. **Data plane under load:** `ib_write_bw` (RDMA, once QoS is bound) or
   `iperf3` as a TCP fallback.

## EVPN route types, as used here

| Type | Name                    | Carries                                   | When you should see it |
|------|--------------------------|--------------------------------------------|-------------------------|
| 2    | MAC/IP advertisement     | Host MAC (+ optionally IP) reachability    | After a host has traffic on the wire |
| 3    | Inclusive multicast (IMET) | "I have a VTEP participating in this VNI" | As soon as VXLAN/bridge config is applied — before any host exists |
| 5    | IP prefix route          | Subnet/external prefix reachability        | Inter-subnet/external routes exchanged via the L3VNI — verify with `nv show bgp l2vpn evpn route type prefix` before assuming it's there |

## RoCE / QoS notes (target design, not yet bound — see README roadmap)

- RoCEv2 traffic is planned onto **switch-priority 3** as the lossless class.
- PFC (802.1Qbb) profile must be bound on every RoCE-facing port on **both**
  ends of a link — a profile bound on one side and not the other is exactly
  the F01 chaos scenario's failure mode.
- ECN/DCQCN thresholds mark before PFC pauses, so congestion is signaled
  before the fabric goes lossless-via-pause. "Queue depth high with ECN
  marks absent" (F04) is the signature of thresholds mistuned too high.
- Verify a bound profile with `nv show interface swpX qos pfc` and
  `ethtool -S swpX | grep -i pause` — metric names for pause counters vary
  by NIC driver/exporter version, so confirm against what's actually
  exposed before trusting a dashboard.

## One-liners / gotchas

- `sudo` for the Linux layer (vtysh, shadow, systemctl); bare `nv` for NVUE.
  Prefer per-command `sudo` over a root shell; `sudo -i` over `sudo su`.
- `stty cols 200 rows 50` fixes console line-wrap garbage; pipe wide output
  through `less -S` instead of letting it wrap.
- `ping -I <iface/addr>` (capital) sets the **source** address; `ping -i`
  (lowercase) sets the **interval** and will warn about flooding if too low.
  `-I` can only source addresses the local box actually owns.
- Read the `PING` header line (`... from X`) to confirm the test actually
  used the source/interface you meant, not just the destination.
- First BGP config on a node triggers an FRR restart warning (daemon list
  changed) — harmless in a lab, a maintenance-window event in production.

## Roadmap

See the root [README](../README.md#roadmap) for the full list. Highlights
relevant to this cheat sheet: BFD (convergence drill re-run), binding the
RoCEv2 QoS layer for real, and a parallel Arista/Ansible build on EVE-NG.
