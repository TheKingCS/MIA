---
id: K-0466
kind: security-finding
title: The greenhouse endpoint hardened after its review (DEC-0185 steps 1-2)
status: confirmed
by: claude
created: 2026-11-24T22:32:08+00:00
concerns: homestead/core/mia_commands.py, homestead/core/command_auth.py, homestead/viewer/serve_exports.py, core/greenhouse_provision.py
from: dec:DEC-0185
---
A fresh reviewer found no signature bypass, but eight problems behind it, all fixed the same day before being described anywhere: staged changes could cross (now nothing may be waiting on the parameter or its pair, and approve_parameter_change re-checks a MIA proposal via still_valid, denying a stale one); two simultaneous requests passed the stale and hourly checks (now BEGIN IMMEDIATE in submit plus a process lock in take_command); NaN believed-current skipped the stale check and huge ints raised (now typed, finite numbers only, parse_constant rejects NaN/Infinity, limits YAML shape-validated, any unexpected error answered 500 refused); replay protection rested on the node clock and 401 reasons leaked (now a high-water mark in mia_command_state, callers told only refused, a key per node); every push overwrote the node command limits and could carry its key (now config/command_limits.yaml is the node own git-ignored copy seeded from command_limits.default.yaml, and both are in _EXCLUDE); slow clients held threads forever (handler timeout 10 s, BoundedServer with 16 slots); paths were relative to the start folder (resolved against the node folder). Three new scenarios; slow client and high-water checked by hand.
