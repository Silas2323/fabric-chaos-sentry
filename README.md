# fabric-chaos-sentry

A hand-built EVPN-VXLAN fabric, run to production-adjacent behavior, now
being instrumented to break deliberately — so a monitoring stack can prove
it catches what matters. This is an operator's notebook, not a demo repo:
every number below was measured on the lab in this repository's
`configs/`, every "what broke" entry is a real incident, and anything not
yet run says so explicitly.

**The thesis:** AI training traffic assumes a lossless, low-latency fabric.
The failures that hurt most aren't hard-down links — they're silent
misconfigurations and gray failures that leave everything "up" while
collective operations crawl. You don't know your monitoring catches those
until you've injected them on purpose. And you don't know your fabric
actually works until you've broken it by accident first.

## What was built

Topology: a full CLOS — 2 spines, 2 leaves, every leaf connected to every
spine — built in NVIDIA Air on Cumulus Linux (NVUE CLI, FRR 10.x
underneath). Four Ubuntu hosts hang off the leaves (two per leaf) as
EVPN-VXLAN tenants.

| Node    | Loopback / Router-ID | ASN            | Fabric ports                    |
|---------|-----------------------|----------------|----------------------------------|
| SPINE-1 | 10.0.0.1/32           | 65100 (shared) | swp1→LEAF-1, swp2→LEAF-2         |
| SPINE-2 | 10.0.0.2/32           | 65100 (shared) | swp1→LEAF-1, swp2→LEAF-2         |
| LEAF-1  | 10.0.0.11/32          | 65101          | swp1/2 uplinks; swp10/11 servers |
| LEAF-2  | 10.0.0.12/32          | 65102          | swp1/2 uplinks; swp10/11 servers |

Full per-node config dumps are in [configs/](configs/).

**BGP unnumbered underlay (RFC 5549).** Every fabric-facing link runs eBGP
with no IPv4 addressing at all — neighbors are named by interface, sessions
form over IPv6 link-local (`fe80::`) next-hops, and IPv4 prefixes (the
loopbacks) are carried *over* that IPv6 next-hop. Loopbacks are advertised
via `redistribute connected` — which is why they carry origin `?`
(incomplete) in the BGP table; `network` statements are the cleaner
production pattern, and this lab took the shortcut knowingly. Zero-touch
adjacency: plug a link in between two Cumulus boxes and the session comes
up with no per-link IP plan.

**EVPN-VXLAN overlay.** L2VPN EVPN address-family is enabled on all four
nodes — including both spines, which never originate a VTEP but have to
relay EVPN routes between leaves; skipping them is the classic first
mistake. The two leaves run the actual VTEPs, sourced from their loopbacks.
VLAN 10 → VNI 10010 and VLAN 20 → VNI 10020 stretch as single broadcast
domains across both leaves.

**Symmetric IRB with anycast gateway + L3VNI.** Both leaves run an SVI per
VLAN as the local default gateway, sharing one anycast gateway MAC
(`44:38:39:ff:00:01`) so a host gets the same gateway identity no matter
which leaf it's attached to. Inter-VLAN traffic (VLAN 10 ↔ VLAN 20, tenant
VRF `TENANT1`) routes symmetrically through L3VNI `104001` instead of
hairpinning through one central router — each leaf routes locally into the
VXLAN fabric and the far leaf routes locally back out.

## What was measured

- **ECMP, verified in both the FIB and BGP.** `10.0.0.12/32` (LEAF-2's
  loopback, seen from LEAF-1) resolves to two `fe80::` next-hops — one via
  each spine — both installed in the FIB, with BGP showing 2 paths under
  multipath. Because both spines share ASN 65100, the two AS-paths are
  identical and standard ECMP conditions hold with no extra knobs; BGP
  still marks one path "best (Older Path)" — that's only the
  advertisement tiebreaker, both paths forward. The design trade-off:
  unique per-spine ASNs (the other common CLOS pattern) would make the
  AS-paths differ and require `bestpath as-path multipath-relax` to keep
  both paths.
- **~3 second link-failure convergence.** Killing a leaf↔spine link and
  timing re-convergence measured ~3s: unnumbered BGP sessions die with the
  link itself (no IP neighbor to hold onto, so no hold-timer wait), and the
  rest is VM carrier-detection latency. BFD is the known next step to push
  this toward sub-second — see Roadmap.
- **Underlay reachability with hop-count evidence.** Loopback-to-loopback
  pings verified in both directions: `ttl=64` between adjacent nodes,
  `ttl=63` leaf-to-leaf through a spine — the TTL delta confirming the
  actual path length, not just "ping works."
- **TTL evidence of symmetric IRB at 62.** A ping between hosts on VLAN 10
  and VLAN 20 attached to different leaves lands at TTL 62 (64 − 2): one
  decrement at the ingress leaf's SVI, one at the egress leaf's SVI. That
  two-hop signature is the proof the traffic actually routed symmetrically
  through both leaves' local gateways, rather than hairpinning through a
  single box.

Raw captures backing these numbers live in [evidence/](evidence/).

## What broke, and what it taught

- **Config-as-source-of-truth, the hard way.** NVIDIA Air's revert button
  resets a node's running state on a session hiccup — including config that
  was never saved. That killed an in-progress build once. The fix isn't
  "be careful," it's the same posture production network-as-code takes:
  the config dump in git is the source of truth, not whatever's running on
  the box right now. Every file in `configs/` exists because of this.
- **The redacted-password restore trap.** `nv config show -o commands`
  prints `hashed-password '*'` for the local account — it redacts the real
  hash rather than showing it. Replay that output verbatim (e.g. restoring
  from a saved dump) and you set the account's password to a value nothing
  can match, locking yourself out. The fix: strip `aaa`/`user` lines before
  a config is ever meant to be replayed, and never touch auth config
  without a second, already-authenticated session open as a lifeline. The
  production analog is a vault or TACACS+ — credentials live outside the
  config artifact entirely, which is why they're scrubbed from `configs/`
  here too.
- **SVI-created-but-unaddressed.** On LEAF-1, `vlan20` ended up created
  and VRF-bound but never addressed — the `ipv4 address` line was lost in
  a turbulent apply. The SVI existed, showed up in config, and was
  silently non-functional: nothing to route with, no usable gateway,
  nothing errored. It was found by diffing the healthy `vlan10` output
  against `vlan20` side-by-side — the working twin made the missing line
  obvious in a way staring at the broken one alone never did. Two lessons:
  "object exists" and "object is functional" are different checkpoints,
  and when you have a known-good sibling, comparative diagnosis beats
  reading the patient in isolation.
- **Duplicate-VNI validation catch.** Manually mapped VLAN 30 → VNI 104001
  using an older-style method — while the `TENANT1` VRF declaration was
  already auto-deriving the L3VNI plumbing for that same VNI. `nv config
  apply` rejected the duplicate claim outright: the manually-entered
  config and the derived config were both asserting ownership of VNI
  104001. The lesson is about intent-based config models: when the system
  derives objects from your declarations, hand-placing those same objects
  the old way isn't redundant — it's a conflict, and a validating control
  plane that catches it at apply time is the difference between a rejected
  command and a subtle broken state.

## Chaos + detection layer

The fabric above is the substrate. On top of it, `chaos/` injects the
failures a fabric like this actually produces in the field, and `sentry/`
(Prometheus/Grafana/Alertmanager) has to prove it catches them — with a
measured detection time, not a guess.

```
┌─────────────────────────────┐     ┌──────────────────────────────┐
│  NVIDIA Air lab             │     │  Kubernetes cluster          │
│  EVPN-VXLAN fabric (BUILT)  │     │  (PLANNED — see Roadmap)     │
│  SPINE-1/2 ── LEAF-1/2      │     │  Proxmox VMs, kubespray      │
│        ▲                    │     │        ▲                     │
│        │ chaos/fabric/      │     │        │ chaos/k8s/          │
│        │ (Ansible + NVUE)   │     │        │ (Chaos Mesh)        │
└────────┼────────────────────┘     └────────┼─────────────────────┘
         │ node_exporter                     │ node_exporter
         │ (ethtool collector)               │ (+ kube-state-metrics)
         ▼                                   ▼
      ┌──────────────────────────────────────────┐
      │  sentry/  (Docker Compose)               │
      │  Prometheus ──► Alertmanager ──► webhook │
      │      │                                   │
      │      └──► Grafana (Fabric Overview)      │
      └──────────────────────────────────────────┘
```

## Repository layout

```
configs/    # Per-node NVUE config dumps (nv config show -o commands), scrubbed of secrets
docs/       # Cheat sheet, troubleshooting guide, one runbook per chaos scenario
evidence/   # Raw command output backing the "what was measured" claims above
chaos/
  fabric/   # Cumulus failure injection (Ansible/NVUE) — 6 scenarios
  k8s/      # Chaos Mesh experiments — 4 scenarios
sentry/     # Prometheus + Grafana + Alertmanager (Docker Compose)
```

Every chaos scenario folder contains an injection script, an
`expected-signals.md` (the causal chain + exact metrics/alerts that must
fire), and a rollback script.

## Scenario table

| # | Failure injected | Expected signal | Detection time | Remediation |
|---|------------------|-----------------|----------------|-------------|
| F01 | **PFC misconfig** — lossless priority unbound from one leaf port | Pause-frame rate spike on neighbors, drops on TC3; `PFCPauseFrameStorm`, `PFCLosslessClassDrops` | target < 60 s (measured: TODO) | [Runbook](docs/runbooks/01-pfc-misconfig.md) → [rollback](chaos/fabric/01-pfc-misconfig/rollback.yml) |
| F02 | Link flap (leaf↔spine) | Carrier changes, BGP cycling, ECMP path loss | TODO | TODO |
| F03 | BGP session reset | Peer leaves Established, EVPN route dip | TODO | TODO |
| F04 | ECN threshold mistuning | Queue depth high **with ECN marks absent**, pause storm | TODO | TODO |
| F05 | MTU mismatch | Drops on one hop, large-payload RDMA fails while BGP stays up | TODO | TODO |
| F06 | Gray failure (degraded link) | Slow CRC/error creep, per-flow asymmetry | TODO | TODO |
| K01 | Pod kill | Restart count, time-to-Ready | TODO | TODO |
| K02 | Network latency between nodes | RTT shift, TCP retransmits | TODO | TODO |
| K03 | Network partition | Cross-node call failures, endpoint churn | TODO | TODO |
| K04 | Resource starvation | CPU throttling, OOMKill, node pressure | TODO | TODO |

**Status:** F01 is scaffolded — inject/rollback playbooks, alert rules, and
runbook are all written — but it has **never been run**: no measured
detection time, nothing exercised against a live fabric yet. It also
injects against a PFC/QoS profile that isn't bound on the base fabric yet
(see Roadmap), so the first real run requires that layer first. All other
scenarios are stubs with TODO docs. K01–K04 additionally depend on the
Kubernetes cluster, which does not exist yet.

## Intended workflow (target state)

> **Note:** Nothing below has been exercised yet — the sentry stack and chaos
> playbooks are scaffolding written ahead of first run (see Status and
> Roadmap). Commands show the designed workflow, not a tested one.

```bash
# 1. Start the detection stack
cd sentry
docker compose up -d
# Prometheus :9090 │ Grafana :3000 (admin/admin) │ Alertmanager :9093

# 2. Point Prometheus at your lab
#    Edit sentry/prometheus/prometheus.yml with your NVIDIA Air mgmt IPs
#    and K8s node IPs, then: curl -X POST localhost:9090/-/reload

# 3. Run scenario F01
cd ../chaos/fabric
ansible-playbook -i inventory/hosts.yml 01-pfc-misconfig/inject.yml \
  -e target_switch=leaf01 -e target_interface=swp1

# 4. Generate RoCE load, watch Grafana, record time-to-alert, then roll back
ansible-playbook -i inventory/hosts.yml 01-pfc-misconfig/rollback.yml \
  -e target_switch=leaf01 -e target_interface=swp1
```

## Design decisions

### Remediation is runbooks, not auto-fix (for now)

Every alert maps to a documented runbook, not an automated remediation. This
is deliberate, and it's about blast radius:

1. **A wrong auto-fix is worse than a slow human fix.** An automated actor
   that rewrites QoS config or bounces links in response to a congestion
   signal will, on a false positive, *create* the outage it exists to prevent.
   In a fabric, remediation actions (drain a link, reset a session, rewrite
   PFC/ECN config) reduce capacity or churn state — exactly what you don't
   want during real congestion caused by something else (e.g., genuine incast).
2. **Detection precision must be proven first.** The chaos scenarios exist to
   measure that precision: every injected failure has a known ground truth, so
   false-positive and false-negative rates are measurable, not guessed.
3. **Graduation path.** A remediation earns automation only after its
   detection has survived repeated chaos runs: runbook → scripted fix a human
   triggers (the rollback playbooks are already this) → gated auto-fix with a
   scope limit (one port, one switch) and an automatic stop condition.

The rollback playbooks are intentionally written as the future automation:
they verify state after acting and refuse to run against more than one device.

### Other choices

- **1:1 scenario→alert mapping.** Every chaos scenario has a named alert.
  If a scenario fires no alert, that's a detection gap — the most valuable
  finding this project can produce.
- **15s scrape interval** so measured detection times reflect rule latency,
  not scrape latency.
- **Injected config is never saved to startup** — a reboot is always a valid
  last-resort rollback.
- **Recording rules abstract platform metric names** (pause counters differ
  by NIC/driver), so dashboards and alerts share one definition.
- **Configs in git, secrets scrubbed.** `configs/` holds the exact
  `nv config show -o commands` output per node with `aaa`/`user` lines
  removed — see "the redacted-password restore trap" above for why those
  lines are dangerous to keep, let alone commit.

## Lab environment

- **Fabric:** NVIDIA Air — 2 spine / 2 leaf Cumulus Linux (NVUE), EVPN-VXLAN,
  symmetric IRB with anycast gateway. RoCEv2 PFC/ECN QoS is scoped but not
  yet bound on the base fabric (roadmap).
- **Detection:** Prometheus / Grafana / Alertmanager via Docker Compose

A Kubernetes cluster (Proxmox VMs via kubespray, Chaos Mesh for injection)
is planned but not built — see Roadmap. The `chaos/k8s/` scenario docs and
the k8s scrape job in `sentry/` are scaffolding written ahead of it.

## Roadmap

- [ ] BFD on fabric links; re-run the convergence drill and record
      before/after numbers against the ~3s baseline above.
- [ ] Bind an actual RoCEv2 QoS layer (PFC on switch-priority 3 + ECN/DCQCN
      thresholds) on the base fabric — today only the F01 chaos scenario
      assumes this exists; the known-good profile itself isn't built yet.
- [ ] Run F01 for the first time against real RDMA load and record measured
      detection times; implement F02–F06.
- [ ] Build the Kubernetes cluster: Proxmox VMs via kubespray, Chaos Mesh,
      kube-state-metrics — then implement K01–K04 against it.
- [ ] Grafana annotations from injection scripts (chaos timeline overlay).
- [ ] Architecture diagram.
- [ ] Parallel build: Arista + Ansible on EVE-NG, as a second vendor
      implementation of the same underlay/overlay design — multi-vendor
      reps, not a rebuild of the thesis.
- [ ] First gated auto-remediation for F01 once detection precision is
      proven.
