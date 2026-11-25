# MIA's directions to the node: the command interface (design)

*For DEC-0185 (Zac, 2026-11-16: "MIA absolutely should be able to adjust greenhouse controllers but stop shouldnt
effect this"), the smart ag plan's phase B (`../../docs/future/SMART_AG_PLAN.md`). Written 2026-11-24 before any code,
because it changes this node's security posture: today nothing here accepts a write (`viewer/serve_exports.py`
refuses every POST).*

## What MIA may direct, and what she never may

**May (targets, schedules, modes; DEC-0185):** a cell's pH and EC target band, its water-temperature and air
targets, an irrigation schedule's interval, the grow lights' hours, a module's mode (normal, conservative). Each is a
named parameter on a whitelist in this repo (`config/command_limits.yaml`), with a hard low and high that MIA can't
change.

**Never:** a dose, a pump or valve switched directly, a notification sent, a firmware or config rollback, the safety
MCU's limits, or anything not on the whitelist. Those stay with the control loop, the safety MCU and the existing
approval queues (this repo's CLAUDE.md rules 5 and 6). "Stop" in MIA never touches any of this.

## The path of one direction

1. **MIA asks.** On MIA's side, an action kind (`greenhouse.adjust`) goes through her action contract: his yes on the
   card, or a grant he gave for that parameter (DEC-0156). Nothing she reads can grant it.
2. **MIA sends.** One signed request to the node over his own network or Tailscale: the parameter, the cell, the new
   value, the value she believes is current, who approved and when. The signature is a key made when the node was set
   up (`core/greenhouse_provision.py` already pushes the node's secrets), so nothing else on the network can send
   one.
3. **The node checks** (`core/mia_commands.py`, new). The parameter is on the whitelist; the value is inside its hard
   limits; the current value matches what MIA believed (else it's refused as stale); and no more than one change to
   that parameter an hour, so nothing can oscillate. A refusal is recorded with its reason and never retried around.
4. **The node applies it through its own queue.** It becomes a `parameter_change_proposals` row (source "mia", with
   the approver), and is applied as a `target_overrides` row exactly as an approved experiment's change is: the
   control loop reads it from there. The safety MCU's hard limits still apply on top and may refuse an actuation.
5. **The node confirms.** The command's state (applied with the old and new value, or refused and why) goes into the
   export MIA already reads, and MIA reports the change only once she sees it there (REQ-AI-002). Undo is a new
   command that sets the old value back, through the same path.

## The decision for Zac (WAITING_ON 0zu)

**Whose approval does the node trust?**

- **A: his yes in MIA counts.** The node trusts a signed request that says he approved in MIA (or that he granted that
  parameter), and applies it within its limits. This is DEC-0185 as written. Recommended, with the limits and the
  one-change-an-hour rule above.
- **B: he approves twice at first.** The node stages MIA's direction as a proposal on its own dashboard, and only his
  press there applies it, as today's experiment changes are. This is safest while the pilot is new, and slower. It
  could move to A after the pilot runs a while.

Recommended: B for the 55-gallon pilot's first month, then A. The node's code is the same either way; only whether a
signed approval applies at once or waits for his press on the node differs (one setting, his).

## The order of work (each tested against the simulator first)

1. **Built 2026-11-24.** The whitelist and limits (`config/command_limits.yaml`: the pH and EC target bands, the
   four parameters the cell reads from target_overrides today, with fish-safe hard ranges and a kept band; approval
   `node` until Zac decides 0zu), and the node's check (`core/mia_commands.py`, table `mia_commands`), with six
   scenarios (`mia_command_*`): inside the limits it's staged for the node (or applied with approval `mia`, reaching
   the cell's targets), outside it's refused, a stale current value is refused, a second change within the hour is
   refused, anything off the list (a dose, a pump) or crowding its band or unapproved is refused. 262 scenarios pass
   (the three rsync ones fail on Windows only), self_audit's coverage is 41/41. Water temperature, irrigation
   intervals, light hours and modes join the list once the control loop reads them from an override.
2. **Built 2026-11-24.** The signed endpoint on the export server: `POST /mia/command` only (everything else still
   refused), with `--db`; `core/command_auth.py` checks a timestamp within 5 minutes, a one-time nonce (kept in
   `mia_command_nonces`) and an HMAC-SHA256 signature over both and the body, with the key in
   `config/mia_command_key` (git-ignored). MIA makes the key once (`data/.keys/greenhouse_command_key`) and sends it at
   the end of "push the greenhouse to ..." over SSH on standard input (MIA's core/greenhouse_provision.py). Three
   `mia_command_endpoint_*` scenarios over real HTTP: a signed direction is staged; unsigned, another key, an hour
   old, a body changed after signing and a replay are refused; a node with no key refuses everything.

   **Hardened after a security review (2026-11-24).** Each direction is decided in one write transaction, one at a
   time (two at once can't both pass); nothing for a parameter or its other end may be waiting when another is
   staged, and approving a change from MIA checks it again against the picture then (a stale one is denied, whoever
   presses Approve); values must be finite numbers of the right type; a request more than five minutes older than
   one already accepted is refused (a high-water mark, so moving the node's clock back can't replay one); a caller is
   only ever told "refused"; a key per node; each connection has ten seconds and at most sixteen are served at once;
   any unexpected error is answered as a refusal. The node's limits are its own copy (`config/command_limits.yaml`,
   git-ignored, seeded from `command_limits.default.yaml`), which a push from MIA's PC never overwrites, and the
   push never carries the node's key. MIA's free text never reaches the node's assistant.
3. **The node's half built 2026-11-24.** `dashboard_state.json` (which MIA already reads) carries `mia_directions`:
   each cell's current adjustable targets (what MIA sends as the value she believes) and her latest directions with
   what became of each (`outcome`: refused with why, waiting for approval, denied, or applied once its change is a
   live target). Scenario `mia_command_outcomes_and_targets_are_in_the_export_mia_reads`. **MIA's side built the same
   day** (MIA's `core/greenhouse_adjust.py`): "set the greenhouse pH minimum to 6.4" reads the node fresh, says the
   exact change from its current value and sends it only on "yes, set it" (the tool `adjust_greenhouse` does the
   same; the Greenhouse page's Water tab has The Node's Targets with Set Target, the action `greenhouse.adjust` on an
   approval card), signed with this node's key, then says what it became from the node's answer and export. There's
   no Undo button: setting it back is another adjustment (one an hour per target), and a waiting change can be
   denied on the node. Tested against the node's own signature check, and live (2026-11-24) against the real export
   server: a change staged, a second one while it waited refused by the node with its reason.
4. Live against the simulator (`main.py` plus `drivers/simulator.py --run`): a change applied, read back, undone.
   **Done 2026-11-24 on Windows** (a temporary copy: `drivers/simulator.py --run`, `main.py --interval 2` and the
   export server, approval `node`): MIA read the cell's pH minimum (6.6), said and sent 6.4 on "yes, set it"; the
   node staged it and refused a second change while it waited; approved through the node's own approval call, the
   control loop took it and MIA read it back from the export as applied, the target 6.4. Set back the same way (with
   the node's own limits copy at `min_minutes_between_changes: 0` for the run): "set the greenhouse pH minimum to
   6.6" said "from 6.4 to 6.6", was approved and read back as applied, the target 6.6. The interface's four steps
   are done; what's left is Zac's 0zu (whose approval the node trusts) and real hardware.

**Widened 2026-11-24:** the air's temperature band (`temp_min` 40-75 °F, `temp_max` 70-95 °F, 5 °F apart) and
`humidity_max` (60-90 %, a lone limit with no band), which modules/climate_control.py already reads from
target_overrides. Scenario `mia_command_sets_the_greenhouse_air_and_humidity`; MIA says "set the greenhouse air
temperature maximum to 82". Irrigation intervals, light hours and modes wait until the loop reads them from an
override. Live run the same day (main.py cycling): the air maximum 85 °F to 80 °F and back, each approved on the node
and read back as applied.
