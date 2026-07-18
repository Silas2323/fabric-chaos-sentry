# Evidence

Raw command output backing the "What was measured" claims in the root
[README](../README.md). Every file here should be a **verbatim capture**
from the lab — full command, full output, no editing beyond redacting
anything sensitive (same rule as [configs/](../configs/): no credential
lines). If a claim in the README can't point at a file in here, it's not
evidence yet — it's a note to go re-capture it.

## Naming convention

`<topic>-<what-it-shows>.txt`, one command's output per file, with the
exact command that produced it as the first line (as a `#`-prefixed
comment) so the capture is reproducible.

## Files expected here (fill in as captured)

| File | Command | Proves |
|------|---------|--------|
| `ecmp-fib-leaf1.txt` | `nv show route 10.0.0.12/32` on LEAF-1 | Two `fe80::` next-hops installed for LEAF-2's loopback |
| `ecmp-bgp-multipath-leaf1.txt` | `nv show bgp ipv4 unicast 10.0.0.12/32` on LEAF-1 | BGP multipath, both spine paths, "best (Older Path)" tiebreaker |
| `convergence-link-kill.txt` | Timestamps around `nv set interface swpX link state down` and session re-establishment | ~3s link-failure convergence number |
| `evpn-type3-checkpoint.txt` | `nv show bgp l2vpn evpn route` before any host has an IP | Type 3 (IMET) only — the "before" frame |
| `evpn-type2-cross-fabric.txt` | `nv show bgp l2vpn evpn route` / `nv show evpn mac vni 10010` after cross-leaf ping | Remote Type 2 routes, next-hop = far leaf loopback |
| `symmetric-irb-ttl.txt` | `ping` between hosts on different VLANs on different leaves | TTL 62, proving the two-hop symmetric IRB path |
| `bgp-summary-underlay.txt` | `nv show bgp summary` on all four nodes | Established sessions with nonzero PfxRcd (see [troubleshooting.md](../docs/troubleshooting.md)) |

**Status:** scaffold only — none of these are captured yet. Populate with
real output from the NVIDIA Air lab; a measured number in the README isn't
final until the capture backing it lives in this folder.
