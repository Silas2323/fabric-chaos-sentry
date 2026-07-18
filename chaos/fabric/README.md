# Fabric Chaos Scenarios

Scripted, repeatable failure injection against a Cumulus Linux EVPN-VXLAN + RoCEv2
fabric (built in NVIDIA Air). Every scenario follows the same contract:

| File                  | Purpose                                             |
|-----------------------|-----------------------------------------------------|
| `inject.yml`          | Ansible playbook that introduces the failure        |
| `expected-signals.md` | The causal chain and the exact metrics/alerts that should fire |
| `rollback.yml`        | Ansible playbook that restores known-good state     |

## Ground rules

1. **One switch at a time.** Every inject playbook asserts it is running against a
   single host. Chaos experiments with an uncontrolled blast radius are outages,
   not experiments.
2. **Nothing is saved to startup config.** Injected changes are applied
   (`nv config apply`) but never saved (`nv config save`), so a switch reboot is
   always a last-resort rollback.
3. **Rollback is verified, not assumed.** Rollback playbooks re-read state after
   applying and assert the known-good config is present.

## Scenarios

| # | Scenario | Status |
|---|----------|--------|
| 01 | [PFC misconfiguration](01-pfc-misconfig/) | 📝 Scaffolded — playbooks/rules/runbook written, never yet run |
| 02 | [Link flap](02-link-flap/) | 🚧 Stub |
| 03 | [BGP session reset](03-bgp-session-reset/) | 🚧 Stub |
| 04 | [ECN threshold mistuning](04-ecn-threshold-mistune/) | 🚧 Stub |
| 05 | [MTU mismatch](05-mtu-mismatch/) | 🚧 Stub |
| 06 | [Gray failure / degraded link](06-gray-failure/) | 🚧 Stub |

## Running a scenario

```bash
cd chaos/fabric
ansible-playbook -i inventory/hosts.yml 01-pfc-misconfig/inject.yml \
  -e target_switch=leaf01 -e target_interface=swp1

# ... observe detection in Grafana/Alertmanager, record detection time ...

ansible-playbook -i inventory/hosts.yml 01-pfc-misconfig/rollback.yml \
  -e target_switch=leaf01 -e target_interface=swp1
```
