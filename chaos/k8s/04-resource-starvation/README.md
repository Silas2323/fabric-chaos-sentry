# K8s Scenario 04 — Resource Starvation (STUB)

**Status:** 🚧 TODO — not yet implemented

## Planned injection
Chaos Mesh `StressChaos` burning CPU and/or memory inside one target pod (or a
node-scoped stress via `stress-ng` DaemonSet variant) to trigger throttling,
OOM behavior, and scheduler pressure.

## Expected signals (to be validated)
- `container_cpu_cfs_throttled_periods_total` climbs (CPU) or working set
  approaches limit (memory)
- OOMKill event + restart if memory limit exceeded
- Node pressure conditions (`MemoryPressure`) if node-scoped; pod evictions

## Rollback
`kubectl delete -f experiment.yaml`; verify throttling counters flatten and
evicted pods reschedule.

## TODO
- [ ] `experiment.yaml` (StressChaos, one pod)
- [ ] `expected-signals.md`
- [ ] Alert rules `K8sCPUThrottlingHigh`, `K8sOOMKill`
