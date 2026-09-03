# MIA Homestead — Features & Capabilities

**Auto-generated 2026-09-03T03:05:05.671698Z from `system_capabilities` — never hand-edit this file, it will be overwritten on the next registration pass.**

**Verification coverage: 37/37 modules have actual proof behind their claims, not just a description.**

---

## Activity Journal (`activity_journal`)

Aggregates every domain that already records a real rationale (dosing, alerts, experiments, maintenance, yield, general automated actions) into one chronological narrative, plus a synthesized 'right now' status and 'what's next' forecast — all read-only, all from data other modules already produce for their own reasons.

**Can do:**
- view the journal
- check current status
- check what's planned next

**Tracks/produces:**
- unified activity journal
- current control-loop status
- upcoming scheduled/planned items

**Limits:** Purely a read/aggregation layer — never takes action, never writes anything. get_whats_next() only ever reports a real time already computed/stored elsewhere (a maintenance schedule's next_due_at, an experiment's planned_end_date, an active watch's window) — it does not guess or invent a plan the system doesn't actually have; an empty result honestly means nothing is currently scheduled.

**Proof this actually works:**
- 2026-08-31: manually seeded real rows via the actual service methods (MaintenanceManager.create_task/update_status, ExperimentManager.propose_experiment/start_experiment, plus a real dosing_event and yield_event) against mia_homestead.db, then ran viewer/export_journal_state.py and confirmed all 9 resulting journal entries appeared correctly categorized (dosing/experiment/yield/maintenance/alert) and correctly ordered newest-first; confirmed get_current_status() correctly reported control_loop_alive=false with an honest last_heartbeat when no live main.py process was running, and correctly flipped to the real most-recent dose once one was inserted; confirmed get_whats_next() correctly surfaced the started experiment's real planned_end_date and stayed empty before it existed — never fabricated a plan.
- 2026-08-31: rendered viewer/journal.html via headless Chromium (Playwright) against the live exported journal_state.json, zero console/page errors, confirmed the Right Now / What's Next / Journal feed sections all render the real data correctly.

*Last updated: 2026-09-03 03:05:05*

---

## Alert Lifecycle Manager (`alert_manager`)

Closes the alert lifecycle that raise_alert() only ever opened: acknowledge or resolve a specific alert (human-driven, precise), and auto-resolve alerts that haven't recurred in a while (periodic, heuristic) — so unresolved alerts don't just accumulate forever once their real condition has cleared.

**Can do:**
- acknowledge a specific alert
- resolve a specific alert
- auto-resolve alerts not re-raised in a configurable window

**Tracks/produces:**
- alert history over a real time window, optionally by source

**Limits:** resolve_alert() refuses an already-resolved alert rather than silently re-writing resolved_at. The automatic sweep is an honest HEURISTIC, not a guarantee — an alert not re-raised in the window usually means its condition cleared, but a crashed or stopped module would look identical; auto-resolved alerts are logged distinguishably from human-resolved ones so this is never mistaken for a confirmed fix. A genuinely recurring condition raises a real, fresh alert after resolution (raise_alert()'s dedup only matches unresolved rows) — resolving never permanently suppresses anything.

**Proof this actually works:**
- scenarios.py::scenario_alert_manager_resolve — confirmed resolve_alert() sets resolved/resolved_at on a real alert, and refuses an already-resolved one
- scenarios.py::scenario_alert_manager_acknowledge — confirmed acknowledge_alert() sets acknowledged/acknowledged_at on a real alert
- scenarios.py::scenario_alert_manager_stale_sweep — confirmed check_stale_alerts() resolves a real alert whose last_seen is past the window, and leaves a recently-seen one alone
- scenarios.py::scenario_alert_manager_recurrence_after_resolution — confirmed a genuinely recurring (source, message) condition raises a real NEW alert after the prior one was resolved, rather than being silently suppressed forever

*Last updated: 2026-09-03 03:05:05*

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

*Last updated: 2026-09-03 03:05:05*

---

## Bed Planting Tracker (`bed_planting`)

Tracks what species is planted in each grow bed, expected vs actual yield, water usage with the reason behind each use, and flags when two plantings sharing the same cell's water want genuinely incompatible pH/EC ranges — since a cell has one water chemistry for every bed on it. Also supports real PLANNING: stage a future planting (bed + species + target date) before it's physically done, then convert it to active once it actually happens.

**Can do:**
- record a new planting that's already happened
- stage a planned future planting (not yet real)
- convert a planned planting to active once it actually happens
- mark harvested or failed
- record water usage with a reason
- check whether current ACTIVE plantings in a cell are chemically compatible

**Tracks/produces:**
- current plantings per bed, with species/variety/planted date
- planned (not-yet-planted) plantings, staged ahead of time
- every real grow bed with its planned/active/recent plantings grouped, for the planting-planner visual
- expected vs actual yield comparisons
- water usage log with rationale

**Limits:** Warns, does not block — planting something incompatible is allowed, you just get told about it. Compatibility check is a plausibility check against known ranges, not a guarantee of real-world outcome. The live compatibility check only ever runs against ACTIVE plantings — a planned planting doesn't yet compete for the cell's real water chemistry, so it's never checked there (a false alarm about a condition that doesn't exist yet); the planting-planner visual still surfaces a planned species' documented range so an incompatibility can be seen before it's staged for real. convert_to_active() refuses (raises) on anything that isn't currently 'planned' — it can't be used to silently rewrite already-real history.

**Proof this actually works:**
- Live manual test 2026-08-26: confirmed compatible plantings (lettuce+basil, overlapping ranges) produce no warning; a fabricated incompatible species correctly triggered the warning
- scenarios.py::scenario_bed_planting_plan_and_convert — confirmed plan() creates a real 'planned' row with planted_date left NULL, convert_to_active() correctly flips it to 'active' with a real planted_date set, and the compatibility check only fires on the ACTIVE result, not while it was still planned
- scenarios.py::scenario_bed_planting_convert_guards_real_history — confirmed convert_to_active() refuses (raises ValueError) on an already-active planting, rather than silently rewriting its real planted_date
- scenarios.py::scenario_bed_planting_get_bed_layout — confirmed get_bed_layout() correctly groups a real bed's planned AND active plantings together, by bed name

*Last updated: 2026-09-03 03:05:05*

---

## Digital Biofilter / Nitrogen-Cycle Model (`biofilter_model`)

Tracks the classic aquaponics nitrogen cycle (ammonia -> nitrite -> nitrate) from periodically logged manual water test results, and warns if livestock is present on a cell that isn't confirmed cycled yet — the most on-brand 'aquaponics scientist' gap that wasn't built yet.

**Can do:**
- log a water test result (ammonia/nitrite/nitrate ppm)
- classify current cycle stage from real logged tests
- check whether a cell is safe to stock livestock, or already at risk if stocked early
- remind (via a real, deduplicated alert) when a stocked, uncycled cell is overdue for a test

**Tracks/produces:**
- water quality test history
- cycle stage classification
- livestock readiness

**Limits:** Built entirely on PERIODIC MANUAL test-kit readings, never a continuous sensor — none exists in this system's sensor types. Never invents a cycle stage from elapsed time alone; only classifies from real logged values, with an honest 'insufficient_data' state when there aren't enough tests yet. Requires 2 CONSECUTIVE clean tests before declaring 'cycled', not one lucky reading. Purely read/log/alert — never touches dosing, never blocks or approves anything; a human decides when to actually add fish.

**Proof this actually works:**
- scenarios.py::scenario_biofilter_cycle_tracking — confirmed the classic ammonia-phase -> nitrite-phase -> cycled progression classifies correctly as real tests are logged in sequence; confirmed a single clean test alone does NOT yet report 'cycled' (the consecutive-tests overclaiming guard); confirmed check_livestock_readiness() correctly warns when fish are stocked on an uncycled cell and reports safe once cycled; confirmed check_overdue_water_tests() raises a real alert for a stocked, uncycled, test-overdue cell and stays silent for a cell with a recent test.

*Last updated: 2026-09-03 03:05:05*

---

## Aquaponics Cell Control (`cell_a_aquaponics`)

Monitors pH and EC in one aquaponics cell and issues dosing corrections to keep both within target range, using multiple consistent readings before acting and hard dosing limits enforced downstream by the safety MCU. Also monitors dissolved oxygen (DO), alert-only, if a DO sensor is configured for this cell, and water temp against the actually-stocked species' documented range — driving a real water heater for a low reading if one is configured, alert-only for a high reading (no chiller is built).

**Can do:**
- pulse the pH-up dosing pump
- pulse the pH-down dosing pump
- pulse the nutrient concentrate dosing pump
- before alerting on a stale/missing sensor reading: retry via a forced immediate reread, then a healthy redundant sensor of the same type if one exists, over up to MAX_CONSECUTIVE_FAILURES_BEFORE_ALERT consecutive cycles
- raise a warning/critical alert on low dissolved oxygen — no automated correction exists beyond the aerator, which is already always running
- turn a real water heater on/off when water temp falls below the stocked species' documented range, if one is configured for this cell
- raise a warning when water temp is above the stocked species' documented max — never attempts to cool (no chiller is built)

**Tracks/produces:**
- pH reading history
- EC reading history
- DO reading history (if configured)
- water temp reading history
- dosing event log (what was dosed, when, why)

**Limits:** Targets: pH 6.6-7.2, EC 800-1500. Requires 3 consistent readings before dosing. Never auto-dilutes high EC (requires manual water change). Freezes dosing entirely if sensors are stale or missing, rather than guessing — the recovery ladder (contracts.MiaHomesteadModule) only changes how fast a GOOD reading gets produced before this logic runs; it never loosens what counts as safe to dose on, and dosing stays frozen for the entire retry window exactly as if no retry existed at all. DO: warns below 5.0 mg/L, critical below 3.0 mg/L — but ONLY if a DO sensor is actually registered for this cell; DO is optional hardware and a cell without one stays completely silent rather than alerting on hardware that was never installed. Water temp check requires BOTH a real stocked tank (tanks.species set) AND that species existing in species_profiles — an empty tank or an unrecognized species name stays silent, never guesses a target range. Water heater ('water_heater' actuator type, distinct from climate_control.py's air 'heater') is opt-in — a cell without one still alerts on a low reading (nothing else can correct it), it just doesn't actuate. Never attempts to cool a high reading regardless of hardware — no chiller is built, and forcing the heater off in that case prevents it from making an already-hot tank worse. On total sensor loss, the water heater is explicitly forced off (stuck-on fire/fish-boil hazard).

**Proof this actually works:**
- scenarios.py::scenario_ph_crash_response — confirmed dosing triggers after 3 consistent readings, closed-loop physics shows pH recovering from the correction
- scenarios.py::scenario_inconsistent_readings — confirmed dosing withheld when readings disagree beyond tolerance
- scenarios.py::scenario_stale_sensor_freeze — confirmed dosing freezes when a sensor is missing/stale
- Live manual test 2026-08-26: confirmed target_overrides changes the live control target with zero restart (cell._current_targets() picked up an experiment change immediately)
- scenarios.py::scenario_sensor_recovery_ladder_recovers — confirmed a forced immediate reread recovers a stale-but-still-alive sensor with zero alert raised
- scenarios.py::scenario_sensor_recovery_exhausted_escalates — confirmed no alert fires during the retry window, the same alert fires once retries genuinely exhaust, and dosing stays frozen throughout (0 doses issued) either way
- Honest gap: the redundant-sensor-substitution step is implemented but genuinely untested — confirmed against the real dev DB that no cell currently configures two sensors of the same type (SELECT cell_id, type, count(*) FROM sensors GROUP BY cell_id, type HAVING count(*) > 1 returns zero rows), so this path has never actually executed against real data.
- scenarios.py::scenario_do_no_sensor_silent — confirmed a cell with no DO sensor configured raises zero DO-related alerts, ever (optional hardware, not noise)
- scenarios.py::scenario_do_critical_alert — confirmed a critically low DO reading (2.0 mg/L) raises a real critical alert citing the actual reading, once a DO sensor is configured
- scenarios.py::scenario_do_healthy_no_alert — confirmed a healthy DO reading (7.0 mg/L) raises nothing
- scenarios.py::scenario_temp_water_species_range — confirmed a water temp reading outside the real stocked species' documented range raises a real warning citing the actual reading and range
- scenarios.py::scenario_temp_water_no_species_silent — confirmed an unstocked tank raises zero species-range alerts, ever (never guesses a target)
- scenarios.py::scenario_temp_water_in_range_no_alert — confirmed a healthy water temp reading raises nothing
- scenarios.py::scenario_temp_water_heater_engages — confirmed a configured water heater turns on for a low reading, with NO alert (being handled), and settles with no repeat commands once corrected
- scenarios.py::scenario_temp_water_no_cooling_above_max — confirmed a high reading raises a real 'no chiller' warning and forces a configured heater off, never on
- scenarios.py::scenario_temp_water_heater_safety_fallback — confirmed total sensor loss forces a configured water heater off

*Last updated: 2026-09-03 03:05:05*

---

## Climate Control (`cell_a_climate`)

Monitors greenhouse air temperature and humidity for one cell/zone and drives a heater and exhaust fan to keep both within target range — heater for low temp, fan for high temp or high humidity, using multiple consistent readings before acting, same as pH/EC dosing. Also drives supplemental grow lighting and CO2 enrichment injection, opt-in per cell, if those sensors exist.

**Can do:**
- turn the heater on/off
- turn the exhaust fan on/off (temperature- or humidity-driven)
- turn supplemental grow lighting on/off
- pulse a CO2 injector valve, cooldown-limited, when CO2 reads low and isn't already at a dangerous level

**Tracks/produces:**
- air temp reading history
- humidity reading history
- light reading history (if configured)
- CO2 reading history (if configured)

**Limits:** Targets: temp 65-85°F, humidity below 75%RH, light above 5000 lux, CO2 above 800 ppm. Requires 3 consistent readings before acting on any sensor. Holds current actuator state (never guesses) when readings are missing, inconsistent, or insufficient. On totally stale/missing sensor data: forces heater OFF (stuck-on fire/scorch risk, same category as a stuck-open dosing pump), fan ON (safe if stuck on, same category as aeration), and grow light OFF (no hazard either way, just a conservative no-op) — never left in whatever state they happened to be in before data was lost. CO2 is genuinely different: a reading at/above 5000 ppm (OSHA's 8-hr PEL) raises a critical alert and refuses to inject regardless of any prior low trend; injection is a 30s pulse, never continuous, cooldown-limited to once per 15 minutes; and on total sensor loss, CO2 injection is deliberately withheld entirely (not forced to any state) since injecting blind risks pushing an already-elevated reading into danger unseen. Light/CO2 are both opt-in per cell — a cell with neither sensor configured raises nothing about either, ever.

**Proof this actually works:**
- scenarios.py::scenario_climate_control_heater_trigger — confirmed heater turns on after 3 consistent below-range temp readings, fan stays off
- scenarios.py::scenario_climate_control_fan_trigger_temp — confirmed fan turns on after 3 consistent above-range temp readings, heater stays off
- scenarios.py::scenario_climate_control_fan_trigger_humidity — confirmed fan turns on from high humidity alone even with in-range temperature
- scenarios.py::scenario_climate_control_no_repeat_commands — confirmed a steady in-range state emits zero repeat commands across multiple cycles (only a real state change produces a command)
- scenarios.py::scenario_climate_control_safety_fallback — confirmed all-stale sensor data forces heater off, fan on, and light off unconditionally, every cycle the fault persists
- scenarios.py::scenario_climate_control_light_no_sensor_silent — confirmed a cell with no light sensor configured raises nothing about light, ever
- scenarios.py::scenario_climate_control_light_trigger — confirmed the grow light turns on after 3 consistent below-target lux readings
- scenarios.py::scenario_climate_control_co2_injection — confirmed a low, consistent CO2 reading triggers exactly one injection pulse, not one per cycle (cooldown enforced)
- scenarios.py::scenario_climate_control_co2_danger_no_inject — confirmed a reading at/above the OSHA PEL raises a critical alert and never injects

*Last updated: 2026-09-03 03:05:05*

---

## Circulation Flow Monitor (`circulation_monitor`)

Detects a circulation pump that's commanded on but not actually moving water — a seized impeller or clogged filter that power/level monitoring alone would miss. Distinct from leak_detector.py: this catches stalled-but-sealed circulation, not water loss.

**Can do:**
- raise a critical alert when a commanded-on pump reads near-zero flow

**Tracks/produces:**
- flow reading history (if a flow sensor is configured)

**Limits:** Opt-in per cell — silent entirely if no flow sensor is configured (not in any tier's hardware BOM yet). Requires 2 consecutive readings at or below 1.0 before alerting — avoids a single sensor glitch. Never alerts when the pump is deliberately off (e.g. load-shed). Alert-only — no 'restart the pump' actuator exists, and software self-restarting a mechanically-failed pump would be unsafe; a human response is correct here.

**Proof this actually works:**
- scenarios.py::scenario_circulation_stall_detected — confirmed a pump commanded on with 2 consecutive near-zero flow readings raises a real critical alert
- scenarios.py::scenario_circulation_off_no_alert — confirmed a deliberately-off pump with zero flow raises nothing
- scenarios.py::scenario_circulation_no_sensor_silent — confirmed a cell with no flow sensor configured raises zero circulation alerts

*Last updated: 2026-09-03 03:05:05*

---

## Data Retention (`data_retention`)

Periodically prunes the four unbounded, append-only, high-frequency tables (sensor_readings, actuator_events, power_telemetry, system_heartbeat) — nothing else in this codebase ever cleaned these up, and they'd otherwise grow forever on a system meant to run for weeks/months unattended.

**Can do:**
- delete rows older than a configurable window (default 90 days)

**Tracks/produces:**
- current row count per retained table, for real visibility into growth

**Limits:** Deletes are permanent — this trades old raw telemetry for bounded disk/query cost, on the confirmed basis that nothing currently built (trend_analyzer, leak_detector, power forecasting, every history tool) looks back further than a few weeks. 90 days is a real, deliberate choice, not a calibrated one — widen it if a future feature needs longer history. Only prunes the four tables confirmed to have no other lifecycle management; never touches alerts (core/alert_manager.py), maintenance_tasks, or any other real record.

**Proof this actually works:**
- scenarios.py::scenario_data_retention_prunes_old_rows — confirmed a real row older than the retention window is deleted, a recent one is kept
- scenarios.py::scenario_data_retention_noop_when_nothing_old — confirmed a run with nothing past the window deletes nothing and logs nothing

*Last updated: 2026-09-03 03:05:05*

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

*Last updated: 2026-09-03 03:05:05*

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

*Last updated: 2026-09-03 03:05:05*

---

## Device Registry (Plug-and-Play MCUs) (`device_registry`)

Recognizes and pairs physical MCU controllers by role (watering, fertilizer dosing, pH dosing, etc), driven by human-readable config files rather than code. Auto-pairs when a device announces a known, unclaimed role; queues anything ambiguous for a human to resolve.

**Can do:**
- pair a device to a role
- give plain-language setup instructions for a role
- auto-create the actuators a newly paired device controls
- build the real pair_confirm wire payload for a role/cell, carrying each actuator's real DB id (not a placeholder/index) so firmware can map actuator_id to the correct physical pin

**Tracks/produces:**
- paired device list
- unpaired/needs-attention device list

**Limits:** Never auto-pairs an ambiguous or role-conflicting device — always defers to a human. Pairing doesn't grant a device any control authority beyond what the safety MCU/dosing limits already allow.

**Proof this actually works:**
- Live manual test 2026-08-26: confirmed a device announcing a known unclaimed role auto-pairs and its actuators get created automatically; confirmed an ambiguous/unlabeled device correctly queues for a human instead of guessing
- scenarios.py::scenario_pair_confirm_payload_real_ids (2026-08-31): deliberately inserted actuators out of order (7 padding rows before the real ones) and confirmed build_pair_confirm_payload() returns the REAL DB actuator ids (>3, not a coincidental 0/1 match) — proves the fix to firmware's findActuatorSlotById() (formerly an index-assumption placeholder, see firmware/safety_mcu/README.md) is fed correct data, not just correct in theory. Real serial transmission of this payload remains untested — no MCU hardware exists yet to send it to.

*Last updated: 2026-09-03 03:05:05*

---

## Diagnostic Engine (`diagnostics`)

Cross-references alerts against the infrastructure map (wiring, plumbing) to produce specific repair guidance — which MCU, which port, which pipe segment — instead of generic troubleshooting steps.

**Can do:**
- diagnose an alert
- optionally file a maintenance task with the diagnosis attached
- auto-diagnose every unresolved alert automatically, every control-loop cycle, the moment it survives the recovery ladder — not only when asked
- correlate the same fault type appearing on 2+ different cells within a short window as one likely shared-infrastructure cause, instead of diagnosing each cell's alert in isolation

**Tracks/produces:**
- diagnosis: likely cause + specific physical location + guidance

**Limits:** Pattern-matches against known fault shapes only — a novel failure mode it hasn't been told about falls through to a generic 'manual investigation needed' response rather than a confident wrong guess. Never attempts an autonomous fix, only points a human at the right place — the only side effect of automatic invocation is filing a maintenance task, exactly what diagnose_alert(create_task=True) already does on request; never touches dosing targets, orders, or config rollback.

**Proof this actually works:**
- Live manual test 2026-08-26: full real-code-path proof — backdated a real sensor reading, ran the actual control cycle, let the base contract raise a genuine staleness alert, then confirmed the diagnosis correctly traced it to the exact MCU (pH Dosing Controller, PORT 2, relay channel 1) and physical mounting location, and auto-filed a maintenance task with that diagnosis attached
- scenarios.py::scenario_sensor_recovery_exhausted_escalates — confirmed auto_diagnose_new_alerts(), called automatically from the control loop with zero manual trigger, produces a real diagnosis (not the generic fallback) and auto-files a system-created maintenance task the same cycle the alert survives the recovery ladder
- scenarios.py::scenario_multi_cell_fault_correlation — confirmed a pH sensor failing simultaneously on two independent cells (cell_a_aquaponics + pilot_cell) produces a 'shared infrastructure' diagnosis referencing both cells rather than two independent per-sensor diagnoses

*Last updated: 2026-09-03 03:05:05*

---

## Experiment Manager (Aquaponics Scientist) (`experiment_manager`)

Proposes and runs controlled changes to one cell's dosing targets, tracks yield outcomes during the window, and recommends evidence-based permanent changes — through the same human-approval pattern as the inventory reorder queue. Also proactively proposes an experiment itself when a planting's yield is significantly behind pace, rather than waiting for a human to notice.

**Can do:**
- propose an experiment (change one target variable for a duration)
- start an approved experiment (applies live via target_overrides, no restart)
- complete an experiment and generate a result summary
- propose a permanent parameter change for human approval
- scan active plantings for a significant yield shortfall and proactively propose an experiment nudging EC toward the species' own documented midpoint (or, once refined by a confirmed result elsewhere, its evidence-derived midpoint instead)
- when a human approves a parameter change, offer it as evidence to the species knowledge base itself (SpeciesRegistry.refine_from_experiment) — closing the loop so a confirmed result on one cell can inform every other cell/species planting in the future, not just the one cell it ran on

**Tracks/produces:**
- experiment history with before/after yield comparisons

**Limits:** NEVER applies a permanent target change without human approval. Comparisons are single before/after means, not statistically rigorous controlled trials — presented as suggestive evidence, explicitly not overstated as proof. Only changes pH/EC targets within a cell, never dosing hard limits, which remain enforced independently by the safety MCU regardless of any experiment. The proactive proposal path is deliberately conservative — at least 50% through the expected time to harvest, actual yield under half of pace, never proposes a second experiment for a cell that already has one live, and only ever proposes moving toward a value already recorded in the species knowledge base, never an invented number. It still only PROPOSES — start_experiment() still requires a human, same gate as every other experiment. The species-knowledge-base feedback loop only ever fires as a side effect of an ALREADY human-approved parameter change (approve_parameter_change()) — no new autonomous-approval path exists, and SpeciesRegistry.refine_from_experiment() itself only ever extends a species' known range from real evidence, never narrows it based on one result.

**Proof this actually works:**
- Live manual test 2026-08-26: full lifecycle proven end to end — proposed a target change, confirmed live effect on the control loop with zero restart, logged before/after yield data, completed the experiment, got a correct evidence-based +32.3% adopt recommendation, approved it, and confirmed the change promoted from set_by='experiment' to set_by='manual'
- Live manual test 2026-08-30 (proactive proposals): seeded a real planting 60% through its time to harvest with yield at 20% of expected-by-now pace and a config EC target away from the species' documented midpoint — confirmed exactly one experiment proposed, correctly attributing baseline_value to the REAL config-read current target and test_value to the species' real recorded midpoint. Confirmed 3 negative cases produce zero proposals: a planting on pace, a planting only 30% through its cycle (too early to judge), and a cell that already has a live (non-terminal) experiment — no duplicate proposal.
- scenarios.py::scenario_closed_loop_species_learning (2026-08-31): proved the full closed loop end to end across two independent cells — a confirmed +40% yield result on cell_a_aquaponics (real seeded before/after yield data) got approved, which extended lettuce's species-wide ec_max and flipped its source to 'experiment_derived'; a separately-seeded underperforming lettuce planting on pilot_cell then got proactively proposed an experiment whose test_value matches the NEWLY refined midpoint (not the stale baseline one), with a hypothesis that explicitly cites the confirmed evidence rather than a generic lookup.

*Last updated: 2026-09-03 03:05:05*

---

## Cost / Profitability Accounting (`finance_tracker`)

Ties real inventory consumption cost to real recorded revenue for a genuine profitability picture, not just yield or revenue in isolation. Also the first real write path for revenue_transactions — that table existed and was already read by the dashboard/home-snapshot exporters, but nothing ever wrote to it.

**Can do:**
- record a real revenue transaction
- get revenue for a window (system-wide or per-cell)
- get consumable cost for a window (system-wide or per-cell, by category)
- get a combined profitability summary (revenue - cost) for a window, system-wide or per-cell

**Tracks/produces:**
- revenue transactions
- consumable cost by category (system-wide or per-cell)
- net margin over a window

**Limits:** Purely a logging/reasoning layer — never touches dosing, actuators, or any control-loop decision. Per-cell cost (v0.2) is honestly scoped to dosing consumption only — inventory_transactions.cell_id is real for dosing (traced through dosing_events) but NULL for a restock, repair part, or pre-migration historical row, all correctly excluded from a per-cell total rather than silently folded in. Items consumed without a known unit_cost are excluded from the total and listed separately, never silently counted as $0. Feeding costs are deliberately not included — no reliable link from feeding_events' free-text food_type to a real inventory_items unit cost exists yet.

**Proof this actually works:**
- scenarios.py::scenario_cost_profitability — confirmed record_revenue() computes total_amount correctly and get_revenue_summary() reflects it; confirmed get_cost_summary() correctly sums real seeded consumption cost for items with a known unit_cost, correctly EXCLUDES an item with no known unit_cost from the total while listing it separately (not silently treated as $0); confirmed get_profitability_summary() nets real revenue minus real cost correctly. scenarios.py::scenario_per_crop_profitability — confirmed a per-cell cost/profitability breakdown correctly isolates one cell's real dosing consumption from another's, and correctly excludes a non-cell-attributed transaction (e.g. a restock) from a per-cell total.

*Last updated: 2026-09-03 03:05:05*

---

## Fish Health, Feeding, and Mortality Tracking (`fish_health`)

Tracks the fish themselves — feeding events, mortality, and health observations — closing the biggest gap in an otherwise water-chemistry/plant-centric system, and giving core/biofilter_model.py a real feeding-rate signal instead of none.

**Can do:**
- log a feeding event
- log fish mortality
- log a fish health observation
- get the feeding trend for a cell (recent vs. baseline rate)
- remind (via a real, deduplicated alert) when recent mortality crosses a real threshold — population-relative when tanks.quantity_stocked is known, an honest absolute-count fallback when it isn't

**Tracks/produces:**
- feeding history
- feeding trend
- mortality history
- health observations

**Limits:** Purely a logging/reasoning layer — never touches dosing, actuators, or any control-loop decision. get_feeding_trend() is a rate signal (recent vs. baseline average), explicitly not a precise bioload calculation, which would need real fish weight/count data this system doesn't have. Mortality alerting never invents a population size — it uses the real percentage when quantity_stocked is set, and says so plainly when it falls back to an absolute count instead.

**Proof this actually works:**
- scenarios.py::scenario_fish_health_tracking — confirmed feeding events log and summarize correctly; confirmed get_feeding_trend() correctly reports 'increasing' from a real seeded rate change and 'insufficient_data' honestly when too few feedings are logged; confirmed check_mortality_spike() alerts on a real percentage when quantity_stocked is set, alerts on the absolute-count fallback when it isn't, and stays silent below both thresholds; confirmed health observations log and retrieve correctly.

*Last updated: 2026-09-03 03:05:05*

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
- scenarios.py::scenario_power_monitor_sensor_id_no_collision — confirmed read_sensors() never reports a real sensors.id, even when a power_telemetry row's id numerically coincides with one (real bug, live 2026-09-01: a stale power-telemetry alert incorrectly named the pilot cell's real temp_water sensor because the two ids happened to collide).

*Last updated: 2026-09-03 03:05:05*

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
- scenarios.py::scenario_self_preservation_no_presence_sensor_silent — confirmed a cell with no presence sensor stays silent (no false CRITICAL, no help request) even with a real critical alert open, fixing a bug that had fired 21,000+ times live before this
- scenarios.py::scenario_self_preservation_signals_with_presence — confirmed the fix didn't break the actual signal path: a real presence reading plus an open critical alert still creates a help request and turns the beacon on

*Last updated: 2026-09-03 03:05:05*

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

*Last updated: 2026-09-03 03:05:05*

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

*Last updated: 2026-09-03 03:05:05*

---

## Irrigation Scheduler (`irrigation_scheduler`)

Pulses a flood/drain grow bed's irrigation valve on a fixed schedule — closes the gap where config/devices/roles/watering_mcu.yaml described scheduled watering but no code ever implemented it. Only for beds configured to need it; a DWC/NFT bed's continuous circulation never needs a separate flood cycle.

**Can do:**
- pulse a configured irrigation valve when its interval is due

**Tracks/produces:**
- scheduled watering log (activity journal, via action_log)

**Limits:** Schedule-driven, not sensor-reactive — deliberately NOT a MiaHomesteadModule (see this file's own docstring for why). 'Moisture-triggered' watering (also described in watering_mcu.yaml) is NOT implemented — no moisture sensor type exists in sensors.type yet; only the scheduled half is real. Which beds get scheduled irrigation is config-driven (config/irrigation_schedules.yaml), never inferred from grow_beds.media_type. A schedule referencing an actuator that doesn't exist is skipped with a logged warning, never a crash.

**Proof this actually works:**
- scenarios.py::scenario_irrigation_scheduled_pulse — confirmed a due bed gets pulsed and logged, citing the real interval and actuator
- scenarios.py::scenario_irrigation_not_yet_due — confirmed a recently-pulsed bed is correctly skipped until its interval elapses
- scenarios.py::scenario_irrigation_missing_actuator — confirmed a misconfigured schedule (actuator that doesn't exist) is skipped with a logged warning, not a crash

*Last updated: 2026-09-03 03:05:05*

---

## Fast Water-Loss / Leak Detection (`leak_detector`)

Catches a water level dropping far faster than evaporation could explain — within one control cycle, not the up-to-60-cycle delay every other periodic check tolerates — since SAFETY_SPEC.md names water level critical as a CRITICAL-tier alert explicitly, and a real leak is one of the most common aquaponics failure modes.

**Can do:**
- scan all level sensors for a leak-implausible drop rate every cycle
- look up current level-drop rate for a cell

**Tracks/produces:**
- real-time level drop rate per cell, and whether it crosses the leak threshold

**Limits:** Strictly read-only — never touches dosing, actuators, or any control-loop decision; no 'shut off water inflow' actuator even exists in this system's model, a real physical response stays a human action. Computes rate from real wall-clock timestamps between the two most recent readings, never simulator tick counts, so it's correct regardless of poll cadence. The threshold (0.02 in/min, ~30x a realistic evaporation upper bound) is a real, physically-grounded starting point, not yet calibrated against real tank geometry — same honesty as dosing_limits' own placeholder values.

**Proof this actually works:**
- scenarios.py::scenario_leak_detection — confirmed a slow, evaporation-plausible drop over a real 10-minute gap does NOT trigger; confirmed a fast drop over a real 2-minute gap (well past the threshold) DOES raise a real CRITICAL alert; confirmed a level RISE (e.g. after a refill) never falsely triggers regardless of magnitude.

*Last updated: 2026-09-03 03:05:05*

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

*Last updated: 2026-09-03 03:05:05*

---

## MCU Transport (`mcu_transport`)

Real serial transport between the Pi and paired Safety MCUs (docs/MCU_PROTOCOL.md) — scans for and pairs new devices, sends heartbeats, dispatches real actuator commands over the correct MCU's link, and reacts to a paired MCU reporting it has fallen back to hard-coded safe defaults.

**Can do:**
- scan available serial ports for a new device and pair it
- send a real actuator command over an MCU's link
- detect and alert on a real fallback_active report

**Tracks/produces:**
- which MCUs are currently paired and linked
- each link's last reported fallback state

**Limits:** Always safely does nothing when no serial hardware is present — list_available_ports() returns [] with zero devices plugged in, exactly today's real environment, and every actuator command falls back to main.py's existing simulated-log behavior. A real fallback_active report raises a real, deduplicated CRITICAL alert rather than silently logging — matches SAFETY_SPEC.md's own critical-severity example for this exact condition.

**Proof this actually works:**
- scenarios.py::scenario_mcu_transport_pairs_over_a_real_link — confirmed a real announce message on a fake link results in a real pairing and a real pair_confirm sent back
- scenarios.py::scenario_mcu_transport_dispatches_real_command — confirmed a command for a paired actuator is sent over its real link, and an unpaired actuator correctly falls back (returns False) for the caller's existing simulated path
- scenarios.py::scenario_mcu_transport_fallback_raises_critical — confirmed a real fallback_active:true status message raises a real, deduplicated CRITICAL alert
- scenarios.py::scenario_mcu_transport_scan_paces_by_interval — confirmed scan pacing is real and enforced, same pattern as core/mia_home_sync.py's is_due()

*Last updated: 2026-09-03 03:05:05*

---

## MIA Home Sync (`mia_home_sync`)

Automatically pushes this system's summarized state export (viewer/home_snapshot.json) to MIA Home's watched-folder ingestion (core/homestead_manager.py in ~/Projects/MIA), on a configurable interval — closes the one manual step docs/MIA_HOME_SYNC_PLAN.md's own transport design deliberately left for a human to do by hand.

**Can do:**
- push the current snapshot to the configured destination via rsync

**Tracks/produces:**
- a system_heartbeat row per sync attempt, for real staleness visibility

**Limits:** Does nothing at all when config/mia_home_sync.yaml's destination is unset — honestly skipped, never guessed. A push failure (host unreachable, SSH key not provisioned, destination full) raises a real, deduplicated warning alert and is retried on the next interval — never crashes the control loop over a transport problem. Read-only on the Homestead side: only ever reads viewer/home_snapshot.json, never writes to it or to anything on the remote end beyond the one file rsync pushes.

**Proof this actually works:**
- scenarios.py::scenario_mia_home_sync_honest_skip_when_unconfigured — confirmed maybe_sync() does nothing at all with no destination configured
- scenarios.py::scenario_mia_home_sync_pushes_via_rsync — confirmed a real rsync push to a real local destination actually delivers the file
- scenarios.py::scenario_mia_home_sync_paces_by_interval — confirmed is_due() correctly gates on interval_minutes using the real heartbeat row
- scenarios.py::scenario_mia_home_sync_failure_raises_alert — confirmed a real failed push (unreachable destination) raises a real warning alert rather than crashing
- Live-verified 2026-09-02 against the real running system and the real MIA repo — see CLAUDE.md's current-state entry for this fix.

*Last updated: 2026-09-03 03:05:05*

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

*Last updated: 2026-09-03 03:05:05*

---

## Pest / Disease Observation Log and Knowledge Base (`pest_disease`)

Tracks plant pest/disease and fish illness observations against a real, seeded knowledge base of common symptoms and guidance — a gap nothing else in this system covers.

**Can do:**
- look up known pest/disease symptoms and guidance by name or organism type
- add a new knowledge entry
- log a real observation for a cell
- get observation history for a cell

**Tracks/produces:**
- pest/disease knowledge entries
- observation history per cell

**Limits:** Purely a logging/knowledge-lookup layer — never touches dosing, actuators, or any control-loop decision. Knowledge entries are added manually (add_knowledge, same pattern as species_registry.add_species), never automatically refined from observations — unlike a species' numeric pH/EC range, 'was this symptom description accurate' doesn't have a clean confirm/extend signal, so this stays a deliberate human action, not an automated one. Camera-based visual detection is a real, much larger future step, not this version — this is the manual log + lookup half only.

**Proof this actually works:**
- scenarios.py::scenario_pest_disease_tracking — confirmed baseline knowledge seeds with 6 real entries (3 plant, 3 fish) and no duplicate seeding on a second construction; confirmed find_knowledge_by_name() and add_knowledge() work correctly; confirmed an observation can log linked to a known knowledge entry OR as a novel unlinked observation, and both retrieve correctly via get_observation_history().

*Last updated: 2026-09-03 03:05:05*

---

## Aquaponics Cell Control (`pilot_cell`)

Monitors pH and EC in one aquaponics cell and issues dosing corrections to keep both within target range, using multiple consistent readings before acting and hard dosing limits enforced downstream by the safety MCU. Also monitors dissolved oxygen (DO), alert-only, if a DO sensor is configured for this cell, and water temp against the actually-stocked species' documented range — driving a real water heater for a low reading if one is configured, alert-only for a high reading (no chiller is built).

**Can do:**
- pulse the pH-up dosing pump
- pulse the pH-down dosing pump
- pulse the nutrient concentrate dosing pump
- before alerting on a stale/missing sensor reading: retry via a forced immediate reread, then a healthy redundant sensor of the same type if one exists, over up to MAX_CONSECUTIVE_FAILURES_BEFORE_ALERT consecutive cycles
- raise a warning/critical alert on low dissolved oxygen — no automated correction exists beyond the aerator, which is already always running
- turn a real water heater on/off when water temp falls below the stocked species' documented range, if one is configured for this cell
- raise a warning when water temp is above the stocked species' documented max — never attempts to cool (no chiller is built)

**Tracks/produces:**
- pH reading history
- EC reading history
- DO reading history (if configured)
- water temp reading history
- dosing event log (what was dosed, when, why)

**Limits:** Targets: pH 6.6-7.2, EC 800-1500. Requires 3 consistent readings before dosing. Never auto-dilutes high EC (requires manual water change). Freezes dosing entirely if sensors are stale or missing, rather than guessing — the recovery ladder (contracts.MiaHomesteadModule) only changes how fast a GOOD reading gets produced before this logic runs; it never loosens what counts as safe to dose on, and dosing stays frozen for the entire retry window exactly as if no retry existed at all. DO: warns below 5.0 mg/L, critical below 3.0 mg/L — but ONLY if a DO sensor is actually registered for this cell; DO is optional hardware and a cell without one stays completely silent rather than alerting on hardware that was never installed. Water temp check requires BOTH a real stocked tank (tanks.species set) AND that species existing in species_profiles — an empty tank or an unrecognized species name stays silent, never guesses a target range. Water heater ('water_heater' actuator type, distinct from climate_control.py's air 'heater') is opt-in — a cell without one still alerts on a low reading (nothing else can correct it), it just doesn't actuate. Never attempts to cool a high reading regardless of hardware — no chiller is built, and forcing the heater off in that case prevents it from making an already-hot tank worse. On total sensor loss, the water heater is explicitly forced off (stuck-on fire/fish-boil hazard).

**Proof this actually works:**
- scenarios.py::scenario_ph_crash_response — confirmed dosing triggers after 3 consistent readings, closed-loop physics shows pH recovering from the correction
- scenarios.py::scenario_inconsistent_readings — confirmed dosing withheld when readings disagree beyond tolerance
- scenarios.py::scenario_stale_sensor_freeze — confirmed dosing freezes when a sensor is missing/stale
- Live manual test 2026-08-26: confirmed target_overrides changes the live control target with zero restart (cell._current_targets() picked up an experiment change immediately)
- scenarios.py::scenario_sensor_recovery_ladder_recovers — confirmed a forced immediate reread recovers a stale-but-still-alive sensor with zero alert raised
- scenarios.py::scenario_sensor_recovery_exhausted_escalates — confirmed no alert fires during the retry window, the same alert fires once retries genuinely exhaust, and dosing stays frozen throughout (0 doses issued) either way
- Honest gap: the redundant-sensor-substitution step is implemented but genuinely untested — confirmed against the real dev DB that no cell currently configures two sensors of the same type (SELECT cell_id, type, count(*) FROM sensors GROUP BY cell_id, type HAVING count(*) > 1 returns zero rows), so this path has never actually executed against real data.
- scenarios.py::scenario_do_no_sensor_silent — confirmed a cell with no DO sensor configured raises zero DO-related alerts, ever (optional hardware, not noise)
- scenarios.py::scenario_do_critical_alert — confirmed a critically low DO reading (2.0 mg/L) raises a real critical alert citing the actual reading, once a DO sensor is configured
- scenarios.py::scenario_do_healthy_no_alert — confirmed a healthy DO reading (7.0 mg/L) raises nothing
- scenarios.py::scenario_temp_water_species_range — confirmed a water temp reading outside the real stocked species' documented range raises a real warning citing the actual reading and range
- scenarios.py::scenario_temp_water_no_species_silent — confirmed an unstocked tank raises zero species-range alerts, ever (never guesses a target)
- scenarios.py::scenario_temp_water_in_range_no_alert — confirmed a healthy water temp reading raises nothing
- scenarios.py::scenario_temp_water_heater_engages — confirmed a configured water heater turns on for a low reading, with NO alert (being handled), and settles with no repeat commands once corrected
- scenarios.py::scenario_temp_water_no_cooling_above_max — confirmed a high reading raises a real 'no chiller' warning and forces a configured heater off, never on
- scenarios.py::scenario_temp_water_heater_safety_fallback — confirmed total sensor loss forces a configured water heater off

*Last updated: 2026-09-03 03:05:05*

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

*Last updated: 2026-09-03 03:05:05*

---

## Sensor Confidence (`sensor_confidence`)

Combines a sensor's calibration-due proximity and current drift status (both already tracked/alerted elsewhere) into one high/medium/low trust signal per sensor, instead of treating every currently-valid reading as equally trustworthy.

**Can do:**
- get confidence for one sensor
- get confidence for every active sensor in a cell

**Tracks/produces:**
- per-sensor confidence level with the real factors behind it

**Limits:** Purely informational — NEVER changes dosing or control-loop behavior. The 'never dose on a single reading, require 3 consistent readings' rule and the recovery ladder's retry logic are unconditional safety gates, not tunable by this score. Synthesizes two signals that already alert on their own (calibration_due via core/maintenance.py, drift via core/trend_analyzer.py) rather than introducing new detection — this doesn't decide anything a human or the control loop wasn't already going to be told about, it just answers 'how much should I trust this reading right now' in one place.

**Proof this actually works:**
- scenarios.py::scenario_sensor_confidence — confirmed a sensor with no calibration_due set and no drift flagged reports 'high'; a sensor with calibration_due within 7 days reports 'medium' with a real factor string; a sensor with calibration_due already past reports 'low'; a sensor currently flagged by trend_analyzer as drifting reports 'low' regardless of its calibration status, with the real z-score cited in its factors.

*Last updated: 2026-09-03 03:05:05*

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
- Correction 2026-08-31: refine_from_experiment() itself had NO real verification evidence despite being named in actions_possible since it was written — the entry above only ever proved baseline seeding. It also existed unwired (never called from anywhere) until this date. Real evidence now: scenarios.py::scenario_closed_loop_species_learning confirms a genuinely range-extending value updates ec_max and flips source to 'experiment_derived', and confirms the self-gating gate correctly REFUSES a value that doesn't extend the range (returns False, no update) — the never-narrow guarantee this method's own docstring promises.

*Last updated: 2026-09-03 03:05:05*

---

## Succession Planning (`succession_planner`)

Proactively suggests what to plant next in a bed as its current planting nears harvest, instead of the bed just becoming empty with no forward-looking suggestion. Reuses the real pH/water-temp compatibility check already enforced elsewhere so any suggested species genuinely fits the cell's shared water.

**Can do:**
- list active plantings nearing (or past) their expected harvest date
- suggest replanting the same species (a proven-compatible default)
- suggest other species genuinely compatible with the cell's remaining shared water

**Tracks/produces:**
- succession suggestions — what to plant next, per bed nearing harvest

**Limits:** Read/suggest only — never plants, converts, or approves anything on its own; a human acts on a suggestion via the existing plan()/convert_to_active() path. Deliberately NOT true crop-family rotation science (avoiding the same plant family to break pest/nutrient cycles) — species_profiles has no plant-family taxonomy to base that on; conflating the two would be overclaimed sophistication this project doesn't actually have.

**Proof this actually works:**
- scenarios.py::scenario_succession_planning

*Last updated: 2026-09-03 03:05:05*

---

## Resource-Efficiency Reporting (`sustainability_report`)

Computes real water-use efficiency (gallons per lb yielded) from data already logged elsewhere (water_usage_events, yield_events) — neither had anything computing efficiency from it before this.

**Can do:**
- get a real water-use efficiency figure for a cell or the whole system, over a real window

**Tracks/produces:**
- water-use efficiency (gallons per lb yielded), per cell or system-wide

**Limits:** Read-only, purely informational — never touches irrigation or control logic. Deliberately does NOT report an energy-per-yield figure: power_telemetry only logs solar generation and battery SOC, never real load/consumption, and battery capacity isn't sized yet (SAFETY_SPEC.md's own open item) — a kWh figure would have to guess a number that doesn't exist. Non-lb-unit yield (count/oz) is listed separately, never silently converted or dropped from the ratio.

**Proof this actually works:**
- scenarios.py::scenario_water_efficiency_reporting

*Last updated: 2026-09-03 03:05:05*

---

## Harvest-to-Sale Lot Traceability (`traceability`)

Records real yield events (the write path yield_events never had before this) and links a harvest back to its originating planting and cell history — dosing, water-quality tests, feeding, pest/disease observations, and any revenue it was sold in — into one queryable lot record. Finalized records are hash-chained locally for tamper-evidence, deliberately without an external blockchain/vendor dependency.

**Can do:**
- record a real harvest (produce or fish)
- assemble a full lot record for one harvest — dosing/water-quality/feeding/pest history and revenue during that planting's life
- finalize a lot record into the local hash-chained ledger
- verify the ledger's integrity end to end

**Tracks/produces:**
- yield event history
- assembled lot records
- a local tamper-evident ledger

**Limits:** Read/log only — never touches dosing, control, or approval logic. Cell-wide history is honestly labeled non-isolated when multiple plantings share a cell's water during the same window, never silently presented as exclusive. Not a real blockchain — a local, verifiable hash chain, matching this project's stated no-external-vendor-dependency stance.

**Proof this actually works:**
- scenarios.py::scenario_yield_recording_and_lot_traceability

*Last updated: 2026-09-03 03:05:05*

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

*Last updated: 2026-09-03 03:05:05*

---

## Weather Awareness (`weather_awareness`)

Checks a real, free weather forecast for frost or heat-wave risk relevant to what's currently planted — the only thing in this system that looks outside the tank/cell instead of only reacting to internal sensor data.

**Can do:**
- check the weather forecast for frost/heat risk
- get the last weather check performed

**Tracks/produces:**
- logged forecast checks: low/high temp, frost risk, species-range violations

**Limits:** Deliberately opportunistic — the control loop never depends on this succeeding. Honestly skips (returns None, no fabricated forecast, no alert) if config/location.yaml has no coordinates set, or Open-Meteo isn't reachable. Uses a free, keyless weather API (Open-Meteo) — no account, no vendor dependency, same stance as core/notifications.py's carrier email-to-SMS gateway. Frost threshold (32F) is a real physical fact, not invented; species-range comparisons use only real, currently-active plantings' documented temp_air ranges, never a guessed range.

**Proof this actually works:**
- Live test 2026-08-31: confirmed a real call to Open-Meteo's public forecast API (no key) returns real current data for a real coordinate pair.
- scenarios.py::scenario_weather_awareness — confirmed check_weather() honestly returns None with no config/location.yaml coordinates set (no fabricated forecast, no alert); confirmed a real forecast with a low at/below 32F raises a real frost-risk WARNING; confirmed a forecast within every active planting's documented temp_air range raises nothing; confirmed a forecast outside the coldest active planting's real documented range raises a real, correctly-worded species-range-violation WARNING citing the actual numbers.

*Last updated: 2026-09-03 03:05:05*

---

## Multi-Week Yield Forecasting (`yield_forecaster`)

Projects a real, uncertainty-banded harvest-date estimate for an active planting, widened by real signals (sensor confidence, stress alerts) rather than a single fabricated confident date — nothing previously projected forward while a planting was still growing, only compared expected vs actual after the fact.

**Can do:**
- forecast when an active planting is likely to be ready to harvest, with a real uncertainty range

**Tracks/produces:**
- a real harvest-date estimate with an explicit earliest/latest range for one active planting

**Limits:** Read-only, purely informational — never touches planting/harvest/dosing logic. Never claims single-day precision (a minimum real band is always applied) and explicitly reports insufficient_data rather than guessing when no days_to_maturity or planted_date exists. The band widens from real signals already produced elsewhere (sensor_confidence, real alerts), never from a fabricated statistical model this project has no real historical data to calibrate yet.

**Proof this actually works:**
- scenarios.py::scenario_yield_forecasting

*Last updated: 2026-09-03 03:05:05*

---
