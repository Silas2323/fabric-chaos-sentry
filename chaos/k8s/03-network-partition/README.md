# K8s Scenario 03 — Network Partition (STUB)

**Status:** 🚧 TODO — not yet implemented

## Planned injection
Chaos Mesh `NetworkChaos` (action: `partition`) splitting pod traffic between
two worker nodes. Explicitly excludes control-plane traffic — partitioning
etcd is a different (and much more dangerous) experiment.

## Expected signals (to be validated)
- Cross-node service calls fail fast vs hang (document which, per app)
- kubelet/node heartbeats unaffected (partition is pod-network scoped)
- CNI-level drop counters; endpoint readiness churn if probes cross the partition

## Rollback
`kubectl delete -f experiment.yaml`.

## TODO
- [ ] `experiment.yaml` with explicit worker-only selectors
- [ ] `expected-signals.md`
- [ ] Alert rule `K8sCrossNodeConnectivityLoss`
