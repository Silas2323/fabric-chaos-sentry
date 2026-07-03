# Runbook — PFC Misconfiguration / Pause Frame Storm

**Triggered by alerts:** `PFCPauseFrameStorm`, `PFCLosslessClassDrops`

## 1. Confirm it's real

- Open the Fabric Overview dashboard → "Pause frames per port" panel.
- Real PFC trouble shows a *rate* increase sustained across scrape intervals,
  on multiple ports around a common point. A single-sample blip is noise.
- Cross-check drops: `node_network_transmit_drop_total` climbing on any
  fabric port carrying the lossless class confirms impact.

## 2. Localize the culprit

The broken port is usually the *quiet* one:

```bash
# On each suspect switch — who is NOT sending pause while neighbors are?
net show interface pluggables   # or: nv show interface
ethtool -S swpX | grep -i pause
nv show interface swpX qos pfc  # is a PFC profile bound?
```

A port whose neighbors show climbing `rx_pause` while its own `tx_pause` is
flat, and whose `qos pfc` shows **no profile bound**, is your misconfiguration.

## 3. Remediate

```bash
cd chaos/fabric
ansible-playbook -i inventory/hosts.yml 01-pfc-misconfig/rollback.yml \
  -e target_switch=<switch> -e target_interface=<port> -e pfc_profile=roce-lossless
```

Manual equivalent on the switch:

```bash
nv set interface swpX qos pfc profile roce-lossless
nv config apply --assume-yes
nv config save        # only after verifying — make the fix survive reboot
```

## 4. Verify

- Pause-frame rate returns to baseline within ~1 minute under load.
- Drops counter stops incrementing.
- `PFCPauseFrameStorm` resolves in Alertmanager.
- Re-run `ib_write_bw` and confirm throughput at baseline.

## 5. Follow-up

- Find out *how* the config drifted (change window? partial playbook run?).
- Add/verify config-drift checking for PFC bindings so this is caught at
  apply time, not under production load.

## Why this is a runbook and not an auto-fix

See [Design Decisions](../../README.md#design-decisions). Short version: an
automated actor that rewrites QoS config in response to a congestion signal
can amplify an outage if the signal is a false positive or the root cause is
elsewhere (e.g., genuine incast). Automation graduates from runbook → gated
auto-fix only after the detection has proven precision over repeated chaos runs.
