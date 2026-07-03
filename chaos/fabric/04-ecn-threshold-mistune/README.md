# Scenario 04 — ECN Threshold Mistuning (STUB)

**Status:** 🚧 TODO — not yet implemented

## Planned injection
Raise the ECN marking min/max thresholds on one leaf's RoCE traffic class so
congestion is signaled far too late (`nv set qos congestion-control ...` via
`inject.yml`). DCQCN senders never back off in time → queues fill → PFC storms
do the work ECN should have done early.

## Expected signals (to be validated)
- ECN-marked packet counters flatline *while* queue depth climbs (the tell:
  congestion without marking)
- Pause frame rate rises as PFC becomes the only congestion signal
- RoCE throughput becomes bursty; tail latency spikes in ib_write_bw

## Rollback
`rollback.yml`: restore baseline ECN min/max thresholds, verify with
`nv show qos congestion-control`.

## TODO
- [ ] `inject.yml` with threshold variables
- [ ] `expected-signals.md` — this one is subtle; document the *absence* signal
- [ ] `rollback.yml` with post-checks
- [ ] Alert rule `FabricECNMarkingStalled` (queue depth high AND ECN rate ~0)
