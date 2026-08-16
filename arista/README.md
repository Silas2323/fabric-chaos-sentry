# Arista EVPN-VXLAN Lab (EVE-NG)

A parallel build of the same CLOS spine-leaf fabric as the Cumulus/NVIDIA Air
lab in the repo root, running **Arista vEOS 4.32.11M** in **EVE-NG**. Config
dumps live in [configs/](configs/) — one file per node, exported via
`show running-config`.

This is the multi-vendor leg of the portfolio: same addressing plan, same ASN
layout, same VNI mapping — different NOS and a **numbered /30 underlay**
instead of Cumulus BGP unnumbered (RFC 5549).

## Topology

Full CLOS: every leaf connects to every spine.

```
                    ┌──────────┐     ┌──────────┐
                    │ SPINE-1  │     │ SPINE-2  │
                    │ 65100    │     │ 65100    │
                    └──┬───┬───┘     └───┬───┬───┘
                       │   │             │   │
              Eth1/2   │   │  Eth1/2     │   │  Eth1/2
                       │   └──────┬──────┘   │
                       │          │          │
                    ┌──┴──┐    ┌──┴──┐    ┌──┴──┐
                    │LEAF-1│    │     │    │LEAF-2│
                    │65101 │    │     │    │65102 │
                    └──┬───┘    └─────┘    └──┬───┘
                   Eth5│                      │Eth5
                   (V10)│                      │(V10)
```

| Node    | Loopback     | ASN   | Mgmt IP        | Config file          |
|---------|--------------|-------|----------------|----------------------|
| SPINE-1 | 10.0.0.1/32  | 65100 | 192.168.15.62  | [spine1.eos](configs/spine1.eos) |
| SPINE-2 | 10.0.0.2/32  | 65100 | 192.168.15.63  | [spine2.eos](configs/spine2.eos) |
| LEAF-1  | 10.0.0.11/32 | 65101 | 192.168.15.60  | [leaf1.eos](configs/leaf1.eos)   |
| LEAF-2  | 10.0.0.12/32 | 65102 | 192.168.15.61  | [leaf2.eos](configs/leaf2.eos)   |

Management uses vrf `management` on all nodes with default route
`0.0.0.0/0 → 192.168.15.254`.

## Underlay (BGP + numbered links)

Fabric links are routed `/30` point-to-point — **not** BGP unnumbered.

| Link              | SPINE side        | LEAF side         | Subnet        |
|-------------------|-------------------|-------------------|---------------|
| SPINE-1 ↔ LEAF-1  | Eth1 10.1.1.1/30  | Eth2 10.1.1.2/30  | 10.1.1.0/30   |
| SPINE-1 ↔ LEAF-2  | Eth2 10.1.1.5/30  | Eth2 10.1.1.6/30  | 10.1.1.4/30   |
| SPINE-2 ↔ LEAF-1  | Eth1 10.1.1.9/30  | Eth1 10.1.1.10/30 | 10.1.1.8/30   |
| SPINE-2 ↔ LEAF-2  | Eth2 10.1.1.13/30 | Eth1 10.1.1.14/30 | 10.1.1.12/30  |

On each leaf, **Ethernet1** faces SPINE-2 and **Ethernet2** faces SPINE-1.

- eBGP sessions from each leaf to both spines (two uplinks, ECMP-ready).
- Spines peer to both leaves under ASN 65100.
- Loopbacks advertised via `redistribute connected` (same lab shortcut as
  the Cumulus build — production would use explicit `network` statements).
- Leaves run `maximum-paths 2` for dual-spine ECMP.

## Overlay (EVPN + VXLAN)

**Spines:** EVPN address-family activated toward leaf neighbors. Spines relay
EVPN routes; they do not run VXLAN or originate VTEPs.

**Leaves:** Full L2 EVPN-VXLAN edge configuration.

| VLAN | Name | VNI   | Route-target   |
|------|------|-------|----------------|
| 10   | RoCE | 10010 | 10010:10010    |
| 20   | IRB  | 10020 | 10020:10020    |

Per leaf:

- `interface Vxlan1` — VTEP sourced from `Loopback0`, UDP 4789.
- VLAN-to-VNI mapping for 10 and 20.
- Head-end replication (`vxlan flood vtep`) pointing at the peer leaf
  loopback (LEAF-1 → 10.0.0.12, LEAF-2 → 10.0.0.11).
- VLAN-aware BGP: per-VLAN RD (`<loopback>:<vni>`), import/export RT, and
  `redistribute learned` for MAC/IP advertisement.

## Server-facing ports

| Node   | Interface  | Mode   | VLAN |
|--------|------------|--------|------|
| LEAF-1 | Ethernet5  | access | 10   |
| LEAF-2 | Ethernet5  | access | 10   |

VLAN 20 is defined and mapped to VNI 10020 on both leaves, but no access
or trunk port carries it yet.

## EVE-NG notes

Some fabric interfaces on SPINE-2 and LEAF-2 have explicit `mac-address`
statements — a common EVE-NG workaround when virtual interfaces would
otherwise share duplicate MACs.

LEAF-1 runs `no ip routing vrf management`; LEAF-2 has `ip routing vrf
management` enabled. Both reach the lab gateway the same way via static
default in vrf management.

## Comparison to the Cumulus lab

| Aspect              | Cumulus (Air)              | Arista (EVE-NG)              |
|---------------------|----------------------------|------------------------------|
| Platform            | NVIDIA Air                 | EVE-NG / vEOS 4.32.11M       |
| Underlay            | BGP unnumbered (RFC 5549)  | Numbered /30 eBGP            |
| EVPN on spines      | Yes                        | Yes                          |
| VXLAN VTEPs         | Leaves                     | Leaves                       |
| Symmetric IRB       | Done (SVI + L3VNI)         | **Not configured yet**       |
| Anycast gateway     | 44:38:39:ff:00:01          | **Not configured yet**       |
| Server ports        | swp10 (V10), swp11 (V20)   | Eth5 (V10 only, both leaves) |

The Arista build currently stops at **L2 EVPN-VXLAN stretch**. Inter-VLAN
routing (SVIs, VRF, L3VNI, anycast gateway) is the logical next step to
match the Cumulus lab's symmetric IRB milestone.

## Automation hook

[evpn/scripts/leaf_check.py](../evpn/scripts/leaf_check.py) targets this lab:
`device_type: arista_eos`, mgmt IP `192.168.15.60` (LEAF-1). First script
is read-only (`show version`); config push examples belong here as the
Ansible/Netmiko work grows.

## Verification checklist (not yet documented in evidence/)

Run these on a fresh session after any change:

```bash
# Underlay — from LEAF-1
show ip bgp summary
show ip route 10.0.0.12/32          # expect 2 ECMP paths via spines
ping 10.0.0.12 source 10.0.0.11     # loopback-to-loopback

# Overlay
show bgp evpn summary
show vxlan address-table
show bgp evpn route-type mac-ip

# L2 stretch — host on LEAF-1 Eth5 ↔ host on LEAF-2 Eth5 (same VLAN 10)
```

Measured results and capture files should land in the repo root
[evidence/](../evidence/) once this lab is verified to the same standard as
the Cumulus build.

## Roadmap

1. Add SVI + VRF + L3VNI + anycast gateway (symmetric IRB parity with Cumulus).
2. Cable VLAN 20 to a second access port (or trunk) on each leaf.
3. Record ECMP and overlay verification captures in `evidence/`.
4. Extend Netmiko/Ansible automation under `evpn/` or a new `arista/scripts/`.
5. Optional: BFD on fabric links; compare convergence vs the ~3s Cumulus baseline.
