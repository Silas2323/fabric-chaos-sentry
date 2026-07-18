# Troubleshooting Guide

Incidents actually hit while building this lab, kept in the form "symptom →
mechanism → fix → rule for next time." Cross-reference the [scenario
runbooks](runbooks/) for chaos-injected failures — this file is for the
build itself.

## "It's up" but nothing works: Established with zero PfxRcd

**Symptom:** `nv show bgp summary` shows a neighbor as `Established`, but
routes aren't being learned and downstream connectivity fails.

**Mechanism:** Established only means the session negotiated — it says
nothing about whether prefixes are actually being exchanged. A route-map,
address-family mismatch, or a filter can leave a perfectly healthy session
carrying zero routes.

**Fix:** Never read `Established` alone. Always check `PfxRcd` (and
`Up/Down` time, to rule out a session that just flapped) in the same
command. Established-with-zero-PfxRcd is up-but-useless — treat it as a
failure, not a partial success.

## Wrong-box pings: asymmetric packet death on a healthy network

**Symptom:** 100% ping loss between two hosts that are otherwise fine —
looks like a fabric problem.

**Mechanism:** Ran a leaf's ping test from the spine by mistake. The
command was correct; the box it ran on wasn't. Source and destination
existed on different Layer 3 boundaries than intended, so the packet had no
symmetric return path.

**Fix:** Read the hostname in the shell prompt *before* running any test
command, every time — especially after `ssh`-hopping between nodes in a
lab where every prompt looks similar. If a test's failure signature looks
like "impossible," suspect the box before the network.

## Confirm what a ping actually tested

**Symptom:** A ping "passes" or "fails" in a way that doesn't match the
path you thought you were testing.

**Mechanism:** `ping -I` (capital) sets the source address/interface;
`ping -i` (lowercase) sets the interval and will warn about flooding if set
too low. Typo the case and you've silently changed what the test measures
— or triggered a rate-limit warning that looks like an error. `-I` also
silently fails to do what you want if you try to source an address the
local box doesn't actually own.

**Fix:** Always read the `PING ... from X` header line the command prints.
It tells you the actual source address used — confirm it matches what you
intended before trusting the result either way.

## The redacted-password restore trap

**Symptom:** Restoring a saved config (or replaying a config dump) locks
you out of the local account.

**Mechanism:** `nv config show -o commands` prints the local account's
password field as `hashed-password '*'` — it *redacts* the real hash, it
doesn't export it. `'*'` is a value no real password can hash to. If that
line is replayed onto a device (restore, template reuse, copy-paste from a
saved dump), the account's password becomes unmatchable and login fails.

**Fix:** Strip `aaa`/`user` lines from any config meant to be replayed or
committed — this repo's [configs/](../configs/) never carry them. In
production, this is the argument for keeping credentials out of config
artifacts entirely and in a vault or TACACS+. Related: password history
(`pwhistory`, last 10 by default) can independently block resetting to an
old password — the history lives in `/etc/security/opasswd`.

**Standing rule:** keep a second, already-authenticated shell open during
*any* auth or identity change. If the change locks the session you're
working in, the second shell is how you get back in without a full device
reset.

## Config apply ≠ save ≠ verified

**Symptom:** A change "worked" in the session you made it in, but is gone
or different after a reboot, session reset, or NVIDIA Air's revert action.

**Mechanism:** `nv config apply` puts a change into the running config.
`nv config save` persists it to survive a reboot. Neither one *proves* the
change is correct — only a fresh session re-checking state does. NVIDIA
Air's revert button in particular resets a node's running state on a
session hiccup, including anything applied-but-unsaved.

**Fix:** Treat config as unverified until a new session (or `nv config
show`) confirms it fresh. Save deliberately once verified. Keep the
authoritative config in git — see the README's "config-as-source-of-truth"
lesson — rather than trusting whatever's currently running on the box.

## SVI exists but doesn't work

**Symptom:** On LEAF-1, `vlan20` showed up in `nv config show` — created
(`type svi`) and bound to VRF `TENANT1` — but hosts couldn't use it as a
gateway. Nothing errored.

**Mechanism:** The SVI's `ipv4 address` line was lost in a turbulent
apply. An addressless SVI is a real interface object with nothing to route
— "the object exists" and "the object is functional" are different
checkpoints, and NVUE won't warn you the second one hasn't been met.

**How it was found:** by diffing the healthy `vlan10` output against
`vlan20` side-by-side. The working twin made the missing address line
obvious in a way staring at the broken SVI alone never did. When a
known-good sibling exists, diff against it first — comparative diagnosis
beats reading the patient in isolation.

**Fix:** Assign the IP address in the same command sequence as creating the
SVI (see the IRB template in [fabric-cheatsheet.md](fabric-cheatsheet.md)),
and after any messy apply, re-verify the whole intended block, not just the
last command.

## Duplicate VNI — manual config vs derived config

**Symptom:** `nv config apply` rejects a VNI mapping as a duplicate.

**Mechanism:** VLAN 30 was manually mapped to VNI 104001 using an
older-style method — but the `TENANT1` VRF declaration was already
auto-deriving the L3VNI plumbing for that same VNI. Two sources of intent
(hand-placed and system-derived) were claiming the same object, and
validation caught the conflict at apply time.

**Fix:** In an intent-based config model, don't hand-build objects the
system derives from your declarations — declare the intent (the VRF's
L3VNI) and let the derivation own the plumbing. And when an `apply` is
rejected, read what it's telling you about intended state instead of
re-typing the command harder; a validating control plane rejecting a
conflict is the good outcome, the alternative being a subtle broken state.

## FRR restart warning on first BGP config

**Symptom:** Applying the first BGP config on a node triggers a warning
about FRR restarting (daemon list changed).

**Mechanism:** Enabling BGP for the first time changes which FRR daemons
need to run, which requires a restart of the FRR process group, not just a
config reload.

**Fix:** Harmless in a lab session. In production this is a
maintenance-window event — plan the first BGP enablement on a device
accordingly, not as an inline "quick change."

## Console output is garbled / wrapping badly

**Fix:** `stty cols 200 rows 50` fixes most console wrap issues. For
already-wide output, pipe through `less -S` instead of letting it wrap.
