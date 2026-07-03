# Scenario 01 — PFC Misconfiguration: Expected Signals

## The failure

RoCEv2 traffic rides a lossless traffic class built on Priority Flow Control
(802.1Qbb). The fabric maps RoCE to **switch-priority 3** and binds a PFC
profile to every RoCE-facing port. This scenario unbinds that profile from
**one port on one leaf** — the kind of drift a fat-fingered change window or a
partial automation run leaves behind. Nothing goes "down". BGP stays up.
Links stay up. The failure only exists under load.

## Causal chain

```
PFC profile unbound on leaf01:swp1
        │
        ▼
Port no longer generates priority pause when its ingress buffer fills
        │
        ▼
Sender (GPU node / neighbor switch) keeps transmitting into congestion
        │
        ▼
Buffer overrun → drops on the "lossless" class (TC3)
        │
        ▼
RoCE go-back-N retransmits → throughput collapse, tail-latency spikes
        │
        ▼
Neighboring ports emit pause frames trying to compensate → pause storm spreads
```

## How to generate load

From two hosts whose path crosses the misconfigured port:

```bash
# RDMA (preferred — this is what actually breaks)
ib_write_bw -d mlx5_0 --report_gbits <server-ip>

# TCP fallback if no RDMA-capable endpoints in the sim
iperf3 -c <server-ip> -P 8 -t 300
```

## Metrics to watch

| Signal | Metric (node_exporter, `--collector.ethtool`) | Behavior under failure |
|--------|-----------------------------------------------|------------------------|
| Pause frames received | `node_ethtool_rx_pause` | Sharp rate increase on ports *neighboring* the misconfigured one |
| Pause frames sent | `node_ethtool_tx_pause` | Rises on congested upstream ports; **flatlines on the broken port itself** |
| Interface drops | `node_network_transmit_drop_total` / `node_network_receive_drop_total` | Nonzero on a class that should never drop |
| Throughput | app-level (ib_write_bw output) | Collapse / sawtooth |

> Metric names for pause counters vary by NIC driver and exporter version
> (`rx_pause`, `rx_pause_ctrl_phy`, `rx_prio3_pause`, ...). Run
> `ethtool -S swp1 | grep -i pause` on the switch and adjust
> `sentry/prometheus/rules/fabric-pfc.yml` to match what your platform exposes.

The subtle signature worth calling out: the **misconfigured port goes quiet**
(no tx pause) while **everything around it gets loud** (rx pause, drops).
Alerting only on "pause frames high" finds the neighbors; correlating with the
quiet port finds the culprit.

## Alerts that must fire

| Alert | Rule file | Expected latency |
|-------|-----------|------------------|
| `PFCPauseFrameStorm` | `sentry/prometheus/rules/fabric-pfc.yml` | < 60 s from load start (15 s scrape + 30 s `for:`) |
| `PFCLosslessClassDrops` | `sentry/prometheus/rules/fabric-pfc.yml` | < 90 s |

## Measured results (fill in after each run)

| Run date | Load type | Time to first alert | Time to identify culprit port | Notes |
|----------|-----------|---------------------|-------------------------------|-------|
| TODO     |           |                     |                               |       |

## Remediation

Runbook: [docs/runbooks/01-pfc-misconfig.md](../../../docs/runbooks/01-pfc-misconfig.md)
Rollback: `rollback.yml` (re-binds profile, verifies, checks counters flatten).
