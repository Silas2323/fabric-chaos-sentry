# K8s Scenario 02 — Network Latency (STUB)

**Status:** 🚧 TODO — not yet implemented

## Planned injection
Chaos Mesh `NetworkChaos` (action: `delay`) adding latency + jitter to traffic
between pods on two specific nodes, one direction first, then both.

```yaml
# experiment.yaml (planned)
apiVersion: chaos-mesh.org/v1alpha1
kind: NetworkChaos
metadata:
  name: node-to-node-delay
  namespace: chaos-mesh
spec:
  action: delay
  mode: all
  selector:
    namespaces: [chaos-target]
  delay:
    latency: 50ms
    jitter: 10ms
  direction: to
  target:
    mode: all
    selector:
      namespaces: [chaos-target]
```

## Expected signals (to be validated)
- Inter-pod RTT histogram shifts (blackbox exporter / app latency metrics)
- TCP retransmit counters on affected nodes
- etcd/API server warnings if control-plane nodes are included (they should NOT be — scope to workers)

## Rollback
`kubectl delete -f experiment.yaml`.

## TODO
- [ ] `experiment.yaml` scoped to worker nodes only
- [ ] `expected-signals.md`
- [ ] Alert rule `K8sInterNodeLatencyHigh`
