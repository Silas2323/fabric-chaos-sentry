# Scenario 02 — Link Flap (STUB)

**Status:** 🚧 TODO — not yet implemented

## Planned injection
Repeatedly bounce a single fabric link (leaf↔spine) on one switch:
`nv set interface swpX link state down` → wait → `up`, N cycles with jitter,
via `inject.yml`.

## Expected signals (to be validated)
- `node_network_carrier_changes_total` spikes on both ends of the link
- BGP session to the affected neighbor cycles Established → Idle (EVPN underlay)
- ECMP path count drops; traffic shifts to surviving uplinks (watch per-port throughput)

## Rollback
`rollback.yml`: force link admin-up, verify carrier and BGP Established.

## TODO
- [ ] `inject.yml` with flap count/interval variables and single-host guard
- [ ] `expected-signals.md` with measured detection time
- [ ] `rollback.yml` with post-checks
- [ ] Alert rule `FabricLinkFlapping` in `sentry/prometheus/rules/`
