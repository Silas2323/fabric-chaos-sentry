# Scenario 03 — BGP Session Reset (STUB)

**Status:** 🚧 TODO — not yet implemented

## Planned injection
Hard-reset a single eBGP underlay session on one leaf:
`vtysh -c "clear bgp <neighbor>"` (or `nv action` equivalent) via `inject.yml`.
Variant: soft reset vs hard reset to compare convergence behavior.

## Expected signals (to be validated)
- BGP peer state metric leaves Established (frr_exporter / `bgp_peer_state`)
- EVPN type-2/type-5 route count dips and recovers
- Sub-second traffic loss window visible in iperf3/ib_write_bw stream

## Rollback
Session re-establishes on its own; `rollback.yml` only verifies Established state
and route counts back at baseline.

## TODO
- [ ] `inject.yml` targeting one named neighbor
- [ ] `expected-signals.md` with convergence time measurements
- [ ] `rollback.yml` (verification-only)
- [ ] Alert rule `FabricBGPPeerDown` in `sentry/prometheus/rules/`
