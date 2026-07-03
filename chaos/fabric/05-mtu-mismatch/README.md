# Scenario 05 — MTU Mismatch (STUB)

**Status:** 🚧 TODO — not yet implemented

## Planned injection
Lower the MTU on one fabric interface (e.g., 9216 → 1500) on a single leaf via
`inject.yml`. VXLAN-encapsulated jumbo frames from GPU nodes get dropped at
that hop.

## Expected signals (to be validated)
- Interface error / drop counters increment on the mismatched port
- BGP may stay up (small packets pass) while large RDMA payloads silently die —
  a classic partial failure
- ib_write_bw with large message sizes fails or collapses; small messages fine

## Rollback
`rollback.yml`: restore MTU 9216, verify with `nv show interface swpX`.

## TODO
- [ ] `inject.yml` with MTU variable
- [ ] `expected-signals.md` including the "control plane up, data plane broken" trap
- [ ] `rollback.yml` with post-checks
- [ ] Alert rule `FabricOversizeDrops` in `sentry/prometheus/rules/`
