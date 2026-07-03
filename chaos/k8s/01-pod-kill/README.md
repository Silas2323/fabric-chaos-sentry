# K8s Scenario 01 — Pod Kill (STUB)

**Status:** 🚧 TODO — not yet implemented

## Planned injection
Chaos Mesh `PodChaos` (action: `pod-kill`) against one replica of a target
workload, selected by label, in a dedicated `chaos-target` namespace.

```yaml
# experiment.yaml (planned)
apiVersion: chaos-mesh.org/v1alpha1
kind: PodChaos
metadata:
  name: pod-kill-single
  namespace: chaos-mesh
spec:
  action: pod-kill
  mode: one                    # blast radius: exactly one pod
  selector:
    namespaces: [chaos-target]
    labelSelectors:
      app: demo-workload
```

## Expected signals (to be validated)
- `kube_pod_status_phase` transition + restart count increment
- ReplicaSet reschedules replacement; measure time-to-Ready
- Brief 5xx/error blip on the workload's service if not gracefully drained

## Rollback
`kubectl delete -f experiment.yaml` — Chaos Mesh stops the experiment;
the ReplicaSet has already healed the workload.

## TODO
- [ ] `experiment.yaml` + demo target workload manifest
- [ ] `expected-signals.md` with measured time-to-Ready
- [ ] Alert rule `K8sPodChurn` in `sentry/prometheus/rules/`
