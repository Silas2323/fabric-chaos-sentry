# Kubernetes Chaos Scenarios

Chaos Mesh experiment manifests targeting a planned Kubernetes cluster
(Proxmox VMs via kubespray — **the cluster does not exist yet**; this
directory is scaffolding written ahead of it, see the root README roadmap).
Same contract as the fabric scenarios: each folder
gets an experiment manifest (the injection), an `expected-signals.md`, and a
rollback (for Chaos Mesh, usually `kubectl delete -f` on the experiment, since
experiments are declarative and self-reverting on deletion).

## Prerequisites

```bash
# Install Chaos Mesh (once)
helm repo add chaos-mesh https://charts.chaos-mesh.org
helm install chaos-mesh chaos-mesh/chaos-mesh -n chaos-mesh --create-namespace
```

## Scenarios

| # | Scenario | Status |
|---|----------|--------|
| 01 | [Pod kill](01-pod-kill/) | 🚧 Stub |
| 02 | [Network latency](02-network-latency/) | 🚧 Stub |
| 03 | [Network partition](03-network-partition/) | 🚧 Stub |
| 04 | [Resource starvation](04-resource-starvation/) | 🚧 Stub |
