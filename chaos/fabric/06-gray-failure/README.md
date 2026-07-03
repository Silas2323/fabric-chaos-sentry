# Scenario 06 — Gray Failure / Degraded Link (STUB)

**Status:** 🚧 TODO — not yet implemented

## Planned injection
Inject low-rate packet corruption/loss on one link so it stays "up" but
degrades traffic — the hardest failure mode to catch. Options in a virtual lab:
`tc netem` loss/corruption on the switch port, or ethtool-forced speed
downshift. `inject.yml` picks one link, keeps loss <1%.

## Expected signals (to be validated)
- Slow creep in interface CRC/error counters (not a step change — needs
  rate-based alerting, not thresholds on absolute values)
- ECMP flows hashed onto the bad link show retransmits/latency; others are fine
  (per-flow asymmetry is the gray-failure fingerprint)
- Collective operations (all-reduce) throughput drops far more than 1% —
  document the amplification effect

## Rollback
`rollback.yml`: remove netem qdisc / restore port, verify error counters stop
incrementing.

## TODO
- [ ] `inject.yml` with loss-rate variable
- [ ] `expected-signals.md` with amplification measurements
- [ ] `rollback.yml` with post-checks
- [ ] Alert rule `FabricLinkDegraded` (error *rate*, not count)
