# MIA Homestead — Features & Capabilities

**Auto-generated 2026-08-31T15:19:38.566451Z from `system_capabilities` — never hand-edit this file, it will be overwritten on the next registration pass.**

**Verification coverage: 18/18 modules have actual proof behind their claims, not just a description.**

---

## Backup & Rollback Manager (`backup_manager`)

Snapshots configuration (files + live control parameters, not history) before changes, restores on demand, and automatically rolls back a recent config change if critical alerts spike shortly after it was applied.

**Can do:**
- create a snapshot
- restore a snapshot
- start an update watch

**Tracks/produces:**
- snapshot history
- update watch status

**Limits:** Only restores CONFIGURATION (files + control-parameter DB tables) — never alerts, sensor history, yield/experiment records, or species knowledge. Auto-rollback triggers on a critical-alert spike within a validation window, then stops watching — it does not repeatedly roll back the same thing. A rollback reverts config only, never code — if a code change is the actual cause, this won't fix it, and says so explicitly.

**Proof this actually works:**
- Live manual test 2026-08-26: full end-to-end proof — applied a deliberately dangerous dosing limit change (10ml -> 500ml max per dose), simulated the resulting critical alert spike, and confirmed automatic detection and rollback to the correct baseline value (500 -> 10) with a clear notification

*Last updated: 2026-08-31 15:19:38*

---

## Bed Planting Tracker (`bed_planting`)

Tracks what species is planted in each grow bed, expected vs actual yield, water usage with the reason behind each use, and flags when two plantings sharing the same cell's water want genuinely incompatible pH/EC ranges — since a cell has one water chemistry for every bed on it.

**Can do:**
- record a new planting
- mark harvested or failed
- record water usage with a reason
- check whether current plantings in a cell are chemically compatible

**Tracks/produces:**
- current plantings per bed, with species/variety/planted date
- expected vs actual yield comparisons
- water usage log with rationale

**Limits:** Warns, does not block — planting something incompatible is allowed, you just get told about it. Compatibility check is a plausibility check against known ranges, not a guarantee of real-world outcome.

**Proof this actually works:**
- Live manual test 2026-08-26: confirmed compatible plantings (lettuce+basil, overlapping ranges) produce no warning; a fabricated incompatible species correctly triggered the warning

*Last updated: 2026-08-31 15:19:38*

---

## Aquaponics Cell Control (`cell_a_aquaponics`)

Monitors pH and EC in one aquaponics cell and issues dosing corrections to keep both within target range, using multiple consistent readings before acting and hard dosing limits enforced downstream by the safety MCU.

**Can do:**
- pulse the pH-up dosing pump
- pulse the pH-down dosing pump
- pulse the nutrient concentrate dosing pump

**Tracks/produces:**
- pH reading history
- EC reading history
- dosing event log (what was dosed, when, why)

**Limits:** Targets: pH 6.6-7.2, EC 800-1500. Requires 3 consistent readings before dosing. Never auto-dilutes high EC (requires manual water change). Freezes dosing entirely if sensors are stale or missing, rather than guessing.

**Proof this actually works:**
- scenarios.py::scenario_ph_crash_response — confirmed dosing triggers after 3 consistent readings, closed-loop physics shows pH recovering from the correction
- scenarios.py::scenario_inconsistent_readings — confirmed dosing withheld when readings disagree beyond tolerance
- scenarios.py::scenario_stale_sensor_freeze — confirmed dosing freezes when a sensor is missing/stale
- Live manual test 2026-08-26: confirmed target_overrides changes the live control target with zero restart (cell._current_targets() picked up an experiment change immediately)

*Last updated: 2026-08-31 15:19:37*

---

## Dead-Man's-Switch Escalation (`deadmans_switch`)

Watches how long it's been since a human demonstrably interacted with the system, and escalates in two stages if nobody has: 48h notifies the primary contact, 72h escalates to secondary. Catches the 'something's wrong and nobody's watching' case even absent any other active fault.

**Can do:**
- record a check-in (resets escalation)
- escalate a notification when overdue

**Tracks/produces:**
- escalation level and hours since last check-in

**Limits:** Escalates once per level, not every cycle — won't spam once a level is reached, waits for either a check-in or the next threshold. Never takes control action, purely a notification escalation.

**Proof this actually works:**
- Live manual test 2026-08-26: confirmed all states — no check-in ever escalates immediately to level 2, a fresh check-in resets to level 0, backdating past 48h correctly escalates to level 1, checking again immediately does NOT re-escalate (stays at level 1), and backdating past 72h correctly escalates to level 2

*Last updated: 2026-08-31 15:19:38*

---

## Code Deploy Watch & Auto-Rollback (`deploy_manager`)

The code-level counterpart to core/backup_manager.py's config watch, which explicitly does not touch code: after a deploy, watches for a critical-alert spike and automatically reverts the working tree to the last known-good git commit if one appears, requesting a process restart (via main.py, which then relies on the systemd layer, deploy/mia-homestead.service, to actually come back up) rather than leaving broken code running.

**Can do:**
- mark the current commit as known-good
- start a watch after deploying new code
- check active watches and auto-roll-back on a critical-alert spike

**Tracks/produces:**
- deploy history (marked-good commits)
- deploy watch outcomes

**Limits:** Never silently discards uncommitted work to force a rollback through — a dirty working tree gets stashed (git stash push --include-untracked) before the force-checkout, recoverable later via git stash pop. Only reverts the WORKING TREE — does not restart the running process itself (a Python process already has old code loaded in memory; that decision belongs to main.py's control loop, which relies on the systemd layer to actually bring the process back up running the reverted files). Requires mark_last_known_good() to have been called at least once before a watch can start — refuses to watch toward nothing. mark_last_known_good() and start_deploy_watch() are deliberately NOT exposed as assistant tools — deploying and confirming a deploy healthy are intentional terminal/CLI actions (core/deploy_cli.py), same reasoning this project already applies to never exposing bare dosing pulses conversationally. Only get_status() (read-only) is chat-reachable, via get_deploy_status.

**Proof this actually works:**
- Live manual test 2026-08-31, against a disposable scratch git repo (never the real project repo): start_deploy_watch() with no known-good commit yet correctly raises rather than watching toward nothing; marked a real 'v1 good' commit as known-good, deployed a real 'v2 buggy' commit, started a watch; one critical alert (below threshold=2) correctly produced no rollback; a second critical alert correctly triggered auto-rollback — confirmed the actual file content on disk reverted to v1's real content, not just a DB status change. Separately confirmed the stash-safety path: seeded real uncommitted changes (a modified tracked file + a new untracked file) at rollback time, confirmed both were stashed (recoverable via git stash pop, visible in git stash list) rather than destroyed, and the rollback still correctly completed. Separately confirmed the confirmed_good path: backdated a watch's applied_at past its validation window with no critical alerts, confirmed it resolved to confirmed_good and recorded a genuine new last-known-good commit (code_deploys count incremented by exactly 1).
- The systemd layer (deploy/mia-homestead.service, deploy/mia-homestead-rollback.service) was separately verified for real against disposable test units in this machine's actual systemd --user session (cleaned up immediately after, never touching this repo's own unit namespace) — see deploy/README.md for the two real design bugs that testing caught and fixed, and the final clean end-to-end result.

*Last updated: 2026-08-31 15:19:38*

---

## Device Registry (Plug-and-Play MCUs) (`device_registry`)

Recognizes and pairs physical MCU controllers by role (watering, fertilizer dosing, pH dosing, etc), driven by human-readable config files rather than code. Auto-pairs when a device announces a known, unclaimed role; queues anything ambiguous for a human to resolve.

**Can do:**
- pair a device to a role
- give plain-language setup instructions for a role
- auto-create the actuators a newly paired device controls

**Tracks/produces:**
- paired device list
- unpaired/needs-attention device list

**Limits:** Never auto-pairs an ambiguous or role-conflicting device — always defers to a human. Pairing doesn't grant a device any control authority beyond what the safety MCU/dosing limits already allow.

**Proof this actually works:**
- Live manual test 2026-08-26: confirmed a device announcing a known unclaimed role auto-pairs and its actuators get created automatically; confirmed an ambiguous/unlabeled device correctly queues for a human instead of guessing

*Last updated: 2026-08-31 15:19:38*

---

## Diagnostic Engine (`diagnostics`)

Cross-references alerts against the infrastructure map (wiring, plumbing) to produce specific repair guidance — which MCU, which port, which pipe segment — instead of generic troubleshooting steps.

**Can do:**
- diagnose an alert
- optionally file a maintenance task with the diagnosis attached

**Tracks/produces:**
- diagnosis: likely cause + specific physical location + guidance

**Limits:** Pattern-matches against known fault shapes only — a novel failure mode it hasn't been told about falls through to a generic 'manual investigation needed' response rather than a confident wrong guess. Never attempts an autonomous fix, only points a human at the right place.

**Proof this actually works:**
- Live manual test 2026-08-26: full real-code-path proof — backdated a real sensor reading, ran the actual control cycle, let the base contract raise a genuine staleness alert, then confirmed the diagnosis correctly traced it to the exact MCU (pH Dosing Controller, PORT 2, relay channel 1) and physical mounting location, and auto-filed a maintenance task with that diagnosis attached

*Last updated: 2026-08-31 15:19:38*

---

## Experiment Manager (Aquaponics Scientist) (`experiment_manager`)

Proposes and runs controlled changes to one cell's dosing targets, tracks yield outcomes during the window, and recommends evidence-based permanent changes — through the same human-approval pattern as the inventory reorder queue. Also proactively proposes an experiment itself when a planting's yield is significantly behind pace, rather than waiting for a human to notice.

**Can do:**
- propose an experiment (change one target variable for a duration)
- start an approved experiment (applies live via target_overrides, no restart)
- complete an experiment and generate a result summary
- propose a permanent parameter change for human approval
- scan active plantings for a significant yield shortfall and proactively propose an experiment nudging EC toward the species' own documented midpoint

**Tracks/produces:**
- experiment history with before/after yield comparisons

**Limits:** NEVER applies a permanent target change without human approval. Comparisons are single before/after means, not statistically rigorous controlled trials — presented as suggestive evidence, explicitly not overstated as proof. Only changes pH/EC targets within a cell, never dosing hard limits, which remain enforced independently by the safety MCU regardless of any experiment. The proactive proposal path is deliberately conservative — at least 50% through the expected time to harvest, actual yield under half of pace, never proposes a second experiment for a cell that already has one live, and only ever proposes moving toward a value already recorded in the species knowledge base, never an invented number. It still only PROPOSES — start_experiment() still requires a human, same gate as every other experiment.

**Proof this actually works:**
- Live manual test 2026-08-26: full lifecycle proven end to end — proposed a target change, confirmed live effect on the control loop with zero restart, logged before/after yield data, completed the experiment, got a correct evidence-based +32.3% adopt recommendation, approved it, and confirmed the change promoted from set_by='experiment' to set_by='manual'
- Live manual test 2026-08-30 (proactive proposals): seeded a real planting 60% through its time to harvest with yield at 20% of expected-by-now pace and a config EC target away from the species' documented midpoint — confirmed exactly one experiment proposed, correctly attributing baseline_value to the REAL config-read current target and test_value to the species' real recorded midpoint. Confirmed 3 negative cases produce zero proposals: a planting on pace, a planting only 30% through its cycle (too early to judge), and a cell that already has a live (non-terminal) experiment — no duplicate proposal.

*Last updated: 2026-08-31 15:19:38*

---

## Power Monitor (greenhouse_array) (`greenhouse_power`)

Monitors solar/battery telemetry for greenhouse_array, sheds non-critical loads (dosing pumps first) when battery state of charge drops below threshold, and proactively forecasts SOC depletion (linear projection off the recent drain rate) so a human can see a low-battery situation coming hours before the reactive load-shed would actually trigger.

**Can do:**
- shut off dosing pumps to shed load under low SOC
- forecast when SOC will cross the load-shed threshold at the current drain rate

**Tracks/produces:**
- battery SOC %
- watts (solar/battery/generator/grid)
- SOC depletion forecast: current SOC, drain rate, hours to threshold

**Limits:** Load-shed threshold: 20% SOC. Raises a critical alert and freezes non-critical actuation if no telemetry is available at all, rather than assuming power is fine. The SOC forecast is a plain linear projection off recent readings, not a physical discharge-curve model — treat it as an early warning worth a look, not a guaranteed prediction, and it only ever raises a WARNING (never critical) since the threshold hasn't actually been crossed.

**Proof this actually works:**
- scenarios.py::scenario_power_loss_load_shed — confirmed critical alert and load-shed behavior fire correctly when telemetry is missing entirely
- Live manual test 2026-08-30: seeded 4 real battery-drain scenarios directly into power_telemetry — under 12 readings (correctly None, insufficient history), flat/non-draining SOC (correctly None), a genuine 9%/hr drain landing 3.72h from the 20% threshold (correctly forecast AND correctly raised exactly one WARNING alert via check_soc_forecast()), and a slow 0.3%/hr drain landing 231.5h out (correctly forecast a distant threshold time but correctly raised NO alert, outside the 12h warning window). Also verified the get_power_forecast assistant tool end-to-end against the real config/modules.yaml threshold (20%), not a hardcoded stand-in.

*Last updated: 2026-08-31 15:19:37*

---

## Self-Preservation / Help Request (`greenhouse_self_preservation`)

Watches for a human presence near the greenhouse while any critical alert is open, and actively signals for help via a physical beacon rather than waiting to be checked on. Not a diagnosis or repair system — it makes an existing critical state impossible to miss when someone's there.

**Can do:**
- turn on the help beacon (light/speaker)
- turn off the help beacon
- re-nudge every 5 minutes while unacknowledged and someone's present

**Tracks/produces:**
- human presence sensor reading
- help request log

**Limits:** Never attempts an autonomous fix — purely a signaling layer on top of the existing critical alert state. Auto-resolves and silences itself the moment the underlying critical condition clears, with or without human intervention.

**Proof this actually works:**
- Live manual test 2026-08-26: confirmed all three states — silent while critical and alone, beacon on the moment presence is detected, auto-resolved and beacon off once the critical condition cleared

*Last updated: 2026-08-31 15:19:37*

---

## Infrastructure Registry (Wiring & Plumbing) (`infrastructure_registry`)

Knows the physical wiring (which relay channel, which MCU, why) and plumbing (which pipe segment, what size, why routed that way) for every actuator in the system. Source of truth is human-authored config files, not inferred — this reflects the actual build, kept current by editing config/devices/roles/*.yaml and config/infrastructure/plumbing.yaml.

**Can do:**
- look up wiring for a specific actuator
- look up plumbing segments for a cell or actuator

**Tracks/produces:**
- wiring map (actuator -> MCU/port/relay channel + rationale)
- plumbing map (pipe segments, sizes, flow direction + rationale)

**Limits:** Read-only knowledge — never alters wiring or plumbing itself, only reports what the config files say is true. Accuracy depends entirely on those files being kept up to date when the physical build changes.

**Proof this actually works:**
- Live manual test 2026-08-26: confirmed wiring/plumbing queries return correct, specific data (relay channel, port, mount location, pipe segments) for a real actuator and cell

*Last updated: 2026-08-31 15:19:38*

---

## Inventory Manager (`inventory`)

Tracks stock of dosing chemicals, spare sensors, and spare parts. Auto-proposes reorders when stock drops to the reorder threshold, and queues them for approval rather than placing anything automatically.

**Can do:**
- adjust stock on hand
- propose a reorder
- record an order you placed yourself
- mark an order received

**Tracks/produces:**
- stock levels per item
- consumption history
- order history (proposed/approved/denied/ordered/received)

**Limits:** NEVER places a real order or spends money — 'approve' only confirms intent to buy; the human still executes the purchase. No live supplier API integration exists.

**Proof this actually works:**
- Live manual test 2026-08-26: confirmed low-stock alert fires at threshold, and order->receive cycle produces correct final stock totals
- Live manual test 2026-08-26: confirmed auto-propose/approve/deny/skip flow works correctly via both assistant tools and the standalone CLI
- Live manual test 2026-08-26: confirmed consumption-rate forecasting correctly projects days-until-threshold (21.43ml/day -> 18.7 days), correctly withholds an early proposal when outside the warning window, and correctly proposes one with the right rationale when the window is widened to include it

*Last updated: 2026-08-31 15:19:37*

---

## Maintenance Manager (`maintenance`)

Tracks repair/replacement/calibration tasks — created manually (e.g. 'swap the MCU') or automatically from sensor calibration due-dates and recurring schedules (e.g. replace dosing tubing every 180 days).

**Can do:**
- create a task
- assign a task
- mark a task done
- auto-generate overdue calibration tasks
- auto-generate recurring maintenance tasks

**Tracks/produces:**
- open task list with priority and assignment

**Limits:** Creating a task doesn't perform the repair — it's a tracking/reminder layer. High/critical priority tasks trigger a notification the same way safety alerts do.

**Proof this actually works:**
- Live manual test 2026-08-26: confirmed manual task creation with priority-based alerting, and auto-generated calibration task correctly created from an overdue sensor calibration_due date
- Live manual test 2026-08-26: diagnostic engine successfully auto-filed a maintenance task from a real diagnosed alert

*Last updated: 2026-08-31 15:19:37*

---

## Notification Dispatch (`notifications`)

Escalates alerts to a human: info is logged only, warnings go to email, critical alerts go to primary + secondary contact via email and SMS (once a phone+carrier are configured).

**Can do:**
- send email
- send SMS (not configured yet)

**Limits:** SMS goes via a free carrier email-to-SMS gateway (CARRIER_SMS_GATEWAYS — corrected 2026-08-30 from an original Twilio-shaped stub, per this project's own no-outside-vendor-dependency stance), not a paid API — lower delivery assurance than a dedicated SMS provider (depends on the carrier's gateway staying up, no delivery receipts), traded for zero new account/cost beyond the SMTP email already configured. An unconfigured or unrecognized carrier logs 'not sent' rather than silently failing, same honesty stance as before.

**Proof this actually works:**
- Live manual test 2026-08-26: email dispatch path exercised throughout session logs (no real SMTP credentials configured, so delivery itself unverified — the code path and severity routing are).
- Live manual test 2026-08-31 (SMS gateway): confirmed _sms_gateway_address() correctly builds e.g. '5551234567@vtext.com' for a real phone+carrier pair, strips non-digit formatting from the phone number, returns None for a missing phone/carrier and for an unrecognized carrier name (with the unrecognized case logging a distinct warning naming the known carriers, not a silent skip), and correctly truncates a body over SMS_MAX_LENGTH. Real SMTP delivery itself is unverified here for the same reason email's is — no real account configured in this dev sandbox — but the address-construction and routing logic, the part unique to this change, is verified directly.

*Last updated: 2026-08-31 15:19:38*

---

## Aquaponics Cell Control (`pilot_cell`)

Monitors pH and EC in one aquaponics cell and issues dosing corrections to keep both within target range, using multiple consistent readings before acting and hard dosing limits enforced downstream by the safety MCU.

**Can do:**
- pulse the pH-up dosing pump
- pulse the pH-down dosing pump
- pulse the nutrient concentrate dosing pump

**Tracks/produces:**
- pH reading history
- EC reading history
- dosing event log (what was dosed, when, why)

**Limits:** Targets: pH 6.6-7.2, EC 800-1500. Requires 3 consistent readings before dosing. Never auto-dilutes high EC (requires manual water change). Freezes dosing entirely if sensors are stale or missing, rather than guessing.

**Proof this actually works:**
- scenarios.py::scenario_ph_crash_response — confirmed dosing triggers after 3 consistent readings, closed-loop physics shows pH recovering from the correction
- scenarios.py::scenario_inconsistent_readings — confirmed dosing withheld when readings disagree beyond tolerance
- scenarios.py::scenario_stale_sensor_freeze — confirmed dosing freezes when a sensor is missing/stale
- Live manual test 2026-08-26: confirmed target_overrides changes the live control target with zero restart (cell._current_targets() picked up an experiment change immediately)

*Last updated: 2026-08-31 15:19:37*

---

## Periodic Self-Report (`report_generator`)

Compiles a state-of-the-greenhouse digest — yields, dosing pattern, open alerts, pending approvals, maintenance, running experiments — into one report instead of requiring several separate questions. The automated push notification (generate_and_send(), no args) rewrites that digest as natural-language prose via the local Ollama model before sending, so what actually lands in a human's inbox reads like a briefing, not a bullet-list dump — with an always-safe fallback to the plain structured digest if the model isn't reachable.

**Can do:**
- generate a report on demand
- generate and send via notification
- generate a natural-language narrative version of the report via the local model

**Tracks/produces:**
- report history (narrative prose by default, or the raw structured digest as a fallback)

**Limits:** Purely a summarization/composition layer over existing data — never takes action, never makes a decision, just makes the existing picture easier to see at once. The narrative rewrite is explicitly told to use ONLY facts already in the structured digest and never raises on failure — an unreachable/slow model (bounded to a 30s timeout, deliberately shorter than the assistant's own 120s interactive-chat timeout, since this runs inline in main.py's control loop, not a chat someone is actively waiting on) silently falls back to the plain digest rather than skipping the report entirely.

**Proof this actually works:**
- Live manual test 2026-08-26: confirmed the report correctly compiles real yield, dosing, and alert data into one digest, and hours_since_last_report() correctly transitions from None (never sent) to a real elapsed time after generate_and_send()
- Live manual test 2026-08-30 (narrative rewrite): confirmed generate_narrative_report() against a real Ollama call produces genuine natural-language prose (not the raw digest verbatim) that still contains the real underlying numbers; confirmed pointing at an unreachable host (a closed port) falls back to the exact structured digest with a logged warning, not an exception or a missing report.

*Last updated: 2026-08-31 15:19:38*

---

## Species Knowledge Base (`species_registry`)

Tracks ideal pH/EC/temperature ranges per plant and fish species, seeded from baseline horticultural data and refined over time as experiments produce real evidence.

**Can do:**
- add a new species profile
- refine an existing one from experiment evidence

**Tracks/produces:**
- species profiles with ideal ranges, sourced as baseline or experiment-derived

**Limits:** Baseline values are commonly-cited ranges, not guaranteed correct for your specific system — treat as a starting point. Never directly controls dosing; informs target_overrides, which is what the control loop actually reads.

**Proof this actually works:**
- Live manual test 2026-08-26: confirmed baseline seeding produces 3 correct species profiles (lettuce, basil, tilapia) with real horticultural ranges

*Last updated: 2026-08-31 15:19:38*

---

## Sensor Trend Analyzer (`trend_analyzer`)

Catches a sensor slowly drifting toward trouble before it crosses a hard threshold — every other check in this project is reactive (alert once already out of range); this one is proactive, comparing a short recent window against each sensor's own longer rolling baseline.

**Can do:**
- scan all active sensors for drift
- look up current drift status for a cell

**Tracks/produces:**
- drift finding: sensor, baseline mean/stdev, recent mean, z-score, direction

**Limits:** Strictly read-only and separate from the control loop — never touches dosing logic, target ranges, or actuators, and only ever raises a WARNING (never critical) since this is an early-warning trend signal, not a confirmed problem. Requires at least 20 baseline readings per sensor before evaluating it at all, specifically to avoid flagging a freshly-added sensor's first few readings as 'drift' against no real history.

**Proof this actually works:**
- Live manual test 2026-08-30: seeded a real pH sensor with 20 baseline readings (mean 6.404, real noise, stdev 0.015) + 6 readings shifted to exactly +5 baseline-stdevs, confirmed check_all_sensors() correctly flagged it (z-score 5.0, direction 'up') and raised exactly one WARNING alert; confirmed a perfectly flat 26-reading series produces zero findings; confirmed fewer than 26 total readings produces zero findings (insufficient baseline, not a false positive from too little data); confirmed calling check_all_sensors() again immediately bumps the existing alert's occurrence_count (2) rather than inserting a second row — the dedup fix in contracts.mia_homestead_contract.raise_alert() composes correctly with this module, its second real caller.

*Last updated: 2026-08-31 15:19:38*

---
