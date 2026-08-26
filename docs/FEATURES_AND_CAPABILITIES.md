# MIA Homestead — Features & Capabilities

**Auto-generated 2026-08-26T10:04:06.475828Z from `system_capabilities` — never hand-edit this file, it will be overwritten on the next registration pass.**

**Verification coverage: 13/13 modules have actual proof behind their claims, not just a description.**

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

*Last updated: 2026-08-26 10:03:59*

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

*Last updated: 2026-08-26 10:03:59*

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

*Last updated: 2026-08-26 10:03:59*

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

*Last updated: 2026-08-26 10:03:59*

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

*Last updated: 2026-08-26 10:03:59*

---

## Experiment Manager (Aquaponics Scientist) (`experiment_manager`)

Proposes and runs controlled changes to one cell's dosing targets, tracks yield outcomes during the window, and recommends evidence-based permanent changes — through the same human-approval pattern as the inventory reorder queue.

**Can do:**
- propose an experiment (change one target variable for a duration)
- start an approved experiment (applies live via target_overrides, no restart)
- complete an experiment and generate a result summary
- propose a permanent parameter change for human approval

**Tracks/produces:**
- experiment history with before/after yield comparisons

**Limits:** NEVER applies a permanent target change without human approval. Comparisons are single before/after means, not statistically rigorous controlled trials — presented as suggestive evidence, explicitly not overstated as proof. Only changes pH/EC targets within a cell, never dosing hard limits, which remain enforced independently by the safety MCU regardless of any experiment.

**Proof this actually works:**
- Live manual test 2026-08-26: full lifecycle proven end to end — proposed a target change, confirmed live effect on the control loop with zero restart, logged before/after yield data, completed the experiment, got a correct evidence-based +32.3% adopt recommendation, approved it, and confirmed the change promoted from set_by='experiment' to set_by='manual'

*Last updated: 2026-08-26 10:03:59*

---

## Power Monitor (greenhouse_array) (`greenhouse_power`)

Monitors solar/battery telemetry for greenhouse_array and sheds non-critical loads (dosing pumps first) when battery state of charge drops below threshold, to protect aeration and circulation as the last things to lose power.

**Can do:**
- shut off dosing pumps to shed load under low SOC

**Tracks/produces:**
- battery SOC %
- watts (solar/battery/generator/grid)

**Limits:** Load-shed threshold: 20% SOC. Raises a critical alert and freezes non-critical actuation if no telemetry is available at all, rather than assuming power is fine.

**Proof this actually works:**
- scenarios.py::scenario_power_loss_load_shed — confirmed critical alert and load-shed behavior fire correctly when telemetry is missing entirely

*Last updated: 2026-08-26 10:03:59*

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

*Last updated: 2026-08-26 10:03:59*

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

*Last updated: 2026-08-26 10:03:59*

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

*Last updated: 2026-08-26 10:03:59*

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

*Last updated: 2026-08-26 10:03:59*

---

## Notification Dispatch (`notifications`)

Escalates alerts to a human: info is logged only, warnings go to email, critical alerts go to primary + secondary contact via email (and SMS once a provider is configured).

**Can do:**
- send email
- send SMS (not configured yet)

**Limits:** SMS is currently stubbed — it logs 'not sent' rather than silently failing, so a missing provider is never mistaken for a delivered alert.

**Proof this actually works:**
- Live manual test 2026-08-26: email dispatch path exercised throughout session logs (no real SMTP credentials configured, so delivery itself unverified — the code path and severity routing are). SMS explicitly UNVERIFIED: no provider is wired, and the code honestly logs 'not sent' rather than faking success.

*Last updated: 2026-08-26 10:03:59*

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

*Last updated: 2026-08-26 10:03:59*

---
