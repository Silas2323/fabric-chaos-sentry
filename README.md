# fabric-chaos-sentry

Chaos engineering and observability for AI network fabrics and Kubernetes
clusters. Inject realistic failures into an EVPN-VXLAN + RoCEv2 fabric
(Cumulus Linux, built in NVIDIA Air) and a Kubernetes cluster — then prove
the monitoring stack actually catches them, and measure how fast.

**The thesis:** AI training traffic assumes a lossless, low-latency fabric.
The failures that hurt most aren't hard-down links — they're silent
misconfigurations and gray failures that leave everything "up" while
collective operations crawl. You don't know your monitoring catches those
until you've injected them on purpose.

## Architecture

<!-- TODO: architecture diagram (docs/architecture.png) -->
```
┌─────────────────────────────┐     ┌──────────────────────────────┐
│  NVIDIA Air lab             │     │  Kubernetes cluster          │
│  EVPN-VXLAN / RoCEv2 fabric │     │  (Proxmox VMs, kubespray)    │
│  spine01/02 ── leaf01/02    │     │  master + workers            │
│        ▲                    │     │        ▲                     │
│        │ chaos/fabric/      │     │        │ chaos/k8s/          │
│        │ (Ansible + NVUE)   │     │        │ (Chaos Mesh)        │
└────────┼────────────────────┘     └────────┼─────────────────────┘
         │ node_exporter                     │ node_exporter
         │ (ethtool collector)               │ (+ kube-state-metrics, TODO)
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
chaos/
  fabric/   # Cumulus failure injection (Ansible/NVUE) — 6 scenarios
  k8s/      # Chaos Mesh experiments — 4 scenarios
sentry/     # Prometheus + Grafana + Alertmanager (Docker Compose)
docs/
  runbooks/ # One remediation runbook per scenario
```

Every scenario folder contains an injection script, an `expected-signals.md`
(the causal chain + exact metrics/alerts that must fire), and a rollback script.

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

**Status:** F01 is implemented end-to-end (inject → detect → alert → runbook →
rollback). All others are stubs with TODO docs — see each scenario folder.

## Quick start

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

## Lab environment

- **Fabric:** NVIDIA Air — 2 spine / 2 leaf Cumulus Linux (NVUE), EVPN-VXLAN,
  RoCEv2 with PFC on switch-priority 3 + ECN (DCQCN-style)
- **Kubernetes:** Proxmox VMs deployed with kubespray, Chaos Mesh for injection
- **Detection:** Prometheus / Grafana / Alertmanager via Docker Compose

## Roadmap

- [ ] Measure and record real detection times for F01
- [ ] Implement F02–F06 fabric scenarios
- [ ] Implement K01–K04 with Chaos Mesh + kube-state-metrics
- [ ] Grafana annotations from injection scripts (chaos timeline overlay)
- [ ] Architecture diagram
- [ ] First gated auto-remediation for F01 once detection precision is proven
