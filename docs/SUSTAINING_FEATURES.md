# MIA Homestead — Sustaining Features Brainstorm

Config backup/rollback answers "can it undo a bad change." The
categories below are the other ways a system like this earns the right
to be trusted unattended for long stretches. Not all of these are
worth building now — flagged with rough effort and what problem each
one actually solves, so you can pick.

## 1. Predictive consumable forecasting — DONE
Built as `core/inventory.py`'s `check_forecasted_shortages()`, called
from `main.py`'s periodic block. Rest of this entry kept for context on
the original problem statement.

**Problem it solves:** the to-order queue reacts to low stock; it
doesn't warn you a week ahead that you're trending toward it.
**What it'd do:** look at `inventory_transactions` consumption rate
over the last N days, project forward, and flag "at current usage,
pH-up runs out in 6 days" — before it crosses the reorder threshold,
not at it. Cheap to build — it's a linear projection over data
already being collected.
**Effort:** small.

## 2. Sensor drift detection (not just failure detection) — DONE (different mechanism)
Built as `core/trend_analyzer.py`'s `check_all_sensors()` — a real
statistical baseline-vs-recent-window z-score comparison per sensor,
not the `dosing_events.reading_after` approach originally sketched
below, but it solves the same stated problem (catches drift while
still "plausible," not just an outright breach). Kept for context.
**Problem it solves:** the system currently catches sensors that go
stale or return implausible values — it doesn't catch a probe that's
slowly drifting while still returning "plausible" numbers, which is
the actual common failure mode for pH probes specifically (they drift
for weeks before failing outright).
**What it'd do:** compare a probe's readings against expected behavior
— e.g., pH should correct back toward target after a dose; if dosing
events stop producing the expected reading_after change over time,
that's drift, not a control problem. Ties directly into
`dosing_events.reading_after`, which already exists but isn't being
used for this.
**Effort:** medium — needs a real statistical baseline from actual
operation before it's trustworthy, so this is a pilot-hardware-data
feature, not a build-now one.

## 3. Anomaly detection via rate-of-change, not just thresholds — DONE (same mechanism as #2)
`core/trend_analyzer.py`'s recent-vs-baseline z-score comparison covers
this too — a recent-window mean shifted far from the baseline mean IS
a rate-of-change signal, inside the normal band or not. Kept for context.
**Problem it solves:** current dosing logic reacts to a value being
out of range. It doesn't react to a value changing unusually FAST even
while still in range — which is often the earlier, more useful signal
(a slow pH crash and a sudden pH crash have very different causes).
**What it'd do:** track rate-of-change per sensor type, alert on an
unusual rate even inside the normal band. This is a genuinely "gets
smarter over time" feature if the baseline rate is learned from your
own system's history rather than hard-coded.
**Effort:** medium.

## 4. Seasonal/environmental awareness
**Problem it solves:** targets are currently static (or
experiment-adjusted) regardless of season — but a greenhouse's thermal
and light environment genuinely shifts across the year, and what's
"correct" for water temp or dosing frequency in July isn't the same as
January.
**What it'd do:** could be as simple as logging month-over-month
baselines and flagging when a reading is unusual FOR THE SEASON rather
than unusual in absolute terms; more ambitious would tie target
adjustments to it. Given you're not building the greenhouse yet, this
is naturally a later-phase feature — flagging it now so `species_profiles`
and `target_overrides` schemas don't need rework when it's time.
**Effort:** large, and genuinely gated on having a full seasonal cycle
of real data first.

## 5. "Confidence" on every reading and decision — DONE (2026-08-31)
Built as `core/sensor_confidence.py`. Purely informational, exactly as
originally scoped below — never changes dosing/control-loop behavior;
`modules/aquaponics_cell.py`'s "3 consistent readings" rule and the
recovery ladder's retry logic stay unconditional safety gates, not
tunable by a soft trust score. Synthesizes two signals that already
alert on their own (`sensors.calibration_due` via
`core/maintenance.py`, drift via `core/trend_analyzer.py`, its #2
dependency) into one high/medium/low level with the real factors
behind it, rather than adding new detection. New assistant tool
`get_sensor_confidence` (`status` domain, matches `get_sensor_trends`'
placement). Verified via `scenarios.py::scenario_sensor_confidence` (4
checks: no-signal defaults to high, calibration-due-soon reports
medium with a real factor string, overdue calibration reports low,
active drift reports low regardless of calibration status with the
real z-score cited) and a live smoke test against the real running
system (all 6 real sensors correctly and honestly report 'high' —
no calibration schedule exists yet, matching reality). Closes out
every item in the roadmap the user originally picked through. Original
brainstorm text kept below for context.

**Problem it solves:** right now a sensor reading is either used or
discarded (stale/out-of-range) — there's no middle ground for "this
reading is probably fine but the sensor is overdue for calibration, so
weight it a little less."
**What it'd do:** a lightweight confidence score per reading, informed
by `sensors.calibration_due` proximity and recent drift patterns (see
#2). Dosing decisions could factor confidence in, not just raw value.
**Effort:** medium — depends on #2 existing first to be worth much.

## 6. Multi-cell correlation for diagnosis — DONE (2026-08-31)
Built as `core/diagnostics.py`'s `_check_multi_cell_correlation()`,
checked before the normal per-sensor diagnosis inside
`diagnose_alert()`/`auto_diagnose_new_alerts()`. Verified live via
`scenarios.py::scenario_multi_cell_fault_correlation` — cell_a and
pilot_cell both losing their pH sensor at once now correctly produces
one "shared infrastructure" diagnosis referencing both cells instead of
two independent per-sensor diagnoses. Kept for context.
**Problem it solves:** the diagnostic engine currently reasons about
one alert in isolation. Once you have 2+ cells (pilot + full scale,
per `PILOT_VS_SCALE.md`), a fault that shows up on BOTH cells
simultaneously is almost certainly a shared-infrastructure problem
(power, Pi itself, network) — not two coincidental probe failures.
**What it'd do:** cross-reference simultaneous alerts across cells
before diagnosing each independently; "both cells lost pH readings at
the same time" is a much stronger, more specific diagnosis than two
separate "pH sensor stale" alerts.
**Effort:** small once there are 2+ cells to correlate — not useful
before then.

## 7. Dead-man's-switch escalation ladder — DONE
Built as `core/deadmans_switch.py`'s `check_escalation()`, called from
`main.py`'s periodic block. Kept for context.
**Problem it solves:** `human_checkins` and the 72h dead-man's-switch
concept already exist in the schema/spec but the actual escalation
logic (who gets contacted, in what order, after how long) isn't built.
**What it'd do:** a real implementation — after N hours unacknowledged,
notify primary; after more, notify secondary; tie into
`self_preservation.py`'s beacon if someone's physically present but
hasn't engaged with the system remotely.
**Effort:** small — mostly wiring existing pieces together.

## 8. Firmware update safety, mirroring config rollback
**Problem it solves:** `backup_manager.py` handles config rollback;
it explicitly does NOT touch code. Once the Safety MCU firmware is
real and gets updated over time, a bad firmware push is a much scarier
failure mode than a bad config value — and OTA firmware updates are
exactly the kind of thing that benefits from the same "watch, then
roll back if it goes wrong" pattern.
**What it'd do:** version-tag firmware builds, keep the previous
known-good binary on the MCU (or recoverable from the Pi), and apply
the same critical-alert-spike-triggers-rollback logic to firmware
pushes specifically. This is meaningfully harder than config rollback
since it involves re-flashing a physical device, not just files/DB rows.
**Effort:** large, and gated on the MCU firmware actually being
deployed and iterated on first.

## 9. Explain-yourself mode for every autonomous action — DONE
Dosing (`dosing_events.rationale`), load-shedding
(`modules/power_monitor.py` via `core/action_log.py`), inventory
transactions/orders (`reason`/rationale params throughout
`core/inventory.py`), and the whole recovery ladder
(`recovery_log_fn` -> `automated_action_log`) all carry a real
rationale now — surfaced together in `core/activity_journal.py` /
`viewer/journal.html`. Kept for context.
**Problem it solves:** dosing events now have a rationale
(`dosing_events.rationale`), but that's currently the only place this
pattern lives. Extending "why did you do that" to load-shedding,
maintenance task auto-creation, and inventory reorder proposals would
make the whole system's autonomous behavior uniformly explainable, not
just dosing.
**What it'd do:** mostly a consistency pass — add a `rationale` field
anywhere an automated action happens and doesn't already have one.
**Effort:** small, mechanical, high value for trust.

## 10. Periodic self-report ("state of the greenhouse") — DONE
Built as `core/report_generator.py`'s `generate_and_send()`, called
from `main.py`'s periodic block once every 24h. Kept for context.
**Problem it solves:** right now getting a full picture means asking
several separate questions. A once-daily or once-weekly generated
summary — yields, dosing pattern, any anomalies, hardware needs,
pending approvals — read by you rather than pulled by you, closes the
loop on genuinely not having to check in constantly.
**What it'd do:** a scheduled job that compiles the equivalent of
asking the assistant six different questions into one digest, sent via
the existing notification path. Almost entirely a matter of composing
existing data sources — the hard infrastructure work is already done.
**Effort:** small.

## 11. Closed-loop experiment learning across cells — DONE (2026-08-31)
`core/species_registry.py::refine_from_experiment()` already existed
(unused) before this — a confirmed, human-approved experiment result
now actually flows into it via `core/experiment_manager.py`'s
`approve_parameter_change()`, extending the species' own known range
(never narrowing it — self-gating, real evidence only) and flipping
`species_profiles.source` to `'experiment_derived'`. Because
`propose_experiments_for_underperformance()` already read
`species_registry.get_profile()` fresh every call, the cross-cell
propagation to OTHER cells growing the same species happens for free
once the feedback loop exists — no separate mechanism needed. Verified
live end-to-end via `scenarios.py::scenario_closed_loop_species_learning`:
a confirmed +40% yield result on `cell_a_aquaponics` extends lettuce's
species-wide `ec_max`, and a separately-seeded underperforming lettuce
planting on `pilot_cell` then gets proactively proposed the NEWLY
refined value, not the stale baseline one, with a hypothesis explicitly
citing the confirmed evidence.

## 12. Digital biofilter / nitrogen-cycle model — DONE (2026-08-31)
Built as `core/biofilter_model.py`. Real finding that reframed the
original brainstorm below: no ammonia/nitrite/nitrate sensor exists
anywhere in `sensors.type`, and real aquaponics testing is a periodic
manual liquid/strip test kit (e.g. API Freshwater Master Test Kit,
~$38.99, confirmed live 2026-08-31), not something a cheap continuous
probe exists for. Built around a new `water_quality_tests` table (real
logged manual readings, `source` column forward-compatible for a real
automated probe later) rather than pretending continuous sensor data
exists. Tracks cycle stage (`not_started` / `insufficient_data` /
`ammonia_phase` / `nitrite_phase` / `cycled`) from real logged tests —
`cycled` requires 2 CONSECUTIVE clean tests, not one lucky reading
(same overclaiming guard as `MIN_CONSISTENT_READINGS_FOR_DOSE` and the
closed-loop learning work). `check_livestock_readiness()` warns if fish
are already stocked on an uncycled cell; `check_overdue_water_tests()`
(wired into `main.py`'s periodic block) nudges when a stocked, uncycled
cell hasn't had a fresh test logged in 14+ days. Two new assistant
tools (`record_water_quality_test`, `get_biofilter_cycle_status`, new
`water_quality` domain). Verified via
`scenarios.py::scenario_biofilter_cycle_tracking` (9 checks: stage
transitions, the overclaiming guard, all 3 livestock-readiness
outcomes, the overdue reminder firing/staying silent correctly) and a
live smoke test against the real running system. Original brainstorm
text kept below for context — the "predict a spike before it happens"
framing wasn't realistic without continuous sensor data, which doesn't
exist; the livestock-readiness/cycle-stage-from-real-tests framing that
shipped is the honest version of the same underlying goal.

**Problem it solves:** the system is entirely threshold/drift-reactive
about water chemistry — it has no model of the actual nitrogen cycle
(ammonia→nitrite→nitrate) that governs whether a cell is even safely
cycled for livestock yet, or how much bioload a cycled biofilter can
currently handle before a spike.
**What it'd do:** a proactive model built from existing sensor history
(pH, temp, feeding-implied bioload) predicting cycling completion and
warning before a spike shows up as a bad reading, instead of only
reacting after the fact — the most on-brand "aquaponics scientist"
feature not yet built. Needs explicit uncertainty bands, not a single
confident number, matching the experiment system's own honesty
discipline about not overclaiming precision without real calibration
data.
**Effort:** medium-large, software-only (no hardware blocker).

## 13. Optional cloud-escalation for hard questions — DONE (2026-08-31)
Built as `GreenhouseAssistant.ask_with_cloud_escalation()` in
`assistant/greenhouse_assistant.py` — exactly the existing-sibling-class
wiring this entry predicted, not new cloud-calling code. Human-triggered
only (a `/cloud <question>` prefix in the REPL); constructs a fresh,
short `AnthropicGreenhouseAssistant` conversation for just that one
question (same db, no shared history — merging two backends'
conversation state was a real correctness trap not worth taking for a
rarely-used escape hatch). Fails honestly if `ANTHROPIC_API_KEY` isn't
set or the call itself fails — verified both live, neither one silently
substituting a local answer. Confirmed the local Ollama path is
unaffected by re-running a real question against it after the change.
Resolves `docs/OFFLINE_ASSISTANT_PLAN.md`'s own flagged open question
(see that doc's "Open questions" section, now marked resolved). Kept
below for context.

**Problem it solves:** directly resolves `docs/OFFLINE_ASSISTANT_PLAN.md`'s
own flagged, deliberately-undecided open question — the local model
(now the real default, see that doc) has no path to a bigger model for
a genuinely hard diagnostic question, even when connectivity happens to
be available.
**What it'd do:** local stays the unconditional default for everything;
a human could explicitly opt in to routing ONE hard question to
`AnthropicGreenhouseAssistant` (already exists, already the `--cloud`
opt-in path) when online — never automatic, never required.
**Effort:** small-medium — mostly wiring an existing sibling class in,
not new cloud-calling code.

## 14. Fish health, mortality, and feeding tracking — DONE (2026-08-31)
Built as `core/fish_health.py`, two new tables (`feeding_events`,
`fish_health_events`) plus a small honest addition to an existing one
(`tanks.quantity_stocked`, nullable — makes mortality alerting a real
population-relative percentage when known, an explicit absolute-count
fallback when it isn't, never silently assuming a population size).
`get_feeding_trend()` gives `core/biofilter_model.py` a real
recent-vs-baseline feeding-rate signal — explicitly a rate signal, not
a precise bioload calculation, which would need real fish weight/count
data this system doesn't have. `check_mortality_spike()` wired into
`main.py`'s periodic block, same real-deduplicated-alert pattern as
every other periodic check. 4 new assistant tools (`record_feeding`,
`record_fish_mortality`, `record_fish_health_observation`,
`get_fish_health_summary`), new `fish_health` domain. Verified via
`scenarios.py::scenario_fish_health_tracking` (8 checks: feeding
history/trend including the honest 'insufficient_data' case, both
mortality-alert paths — percentage-based and absolute-count fallback —
correctly firing and staying silent, health observations logged
separately from mortality) and a live smoke test against the real
running system. A real bug caught during scenario testing, not assumed
correct from code review: `get_health_events()` originally returned
EVERY fish_health_events row regardless of type, duplicating
`get_mortality_history()`'s data instead of complementing it — fixed
to filter to observations only, matching its actual role in
`get_fish_health_summary`. Original brainstorm text kept below for
context.

**Problem it solves:** this is called an aquaponics manager, but almost
everything built so far is water-chemistry/plant-centric — there's no
fish mortality tracking, no feeding log, no fish health observations
anywhere. That's not just a completeness gap: bioload (how much waste
the fish are actually producing) is exactly what drives the nitrogen
cycle, and `core/biofilter_model.py` currently has no real signal for
it beyond test-kit readings after the fact — a feeding/mortality log
would give it one.
**What it'd do:** a manual log (same shape as `water_quality_tests` —
periodic real entries, not fabricated continuous sensing, since there's
no cheap way to continuously weigh/count fish either) for feeding
events (amount, frequency) and mortality/health observations per tank.
Feeds a real bioload estimate into the biofilter model, and gives the
assistant something real to answer "how are the fish doing" with,
instead of nothing.
**Effort:** small-medium — same pattern as the biofilter model, mostly
a new table + a service + an assistant tool.

## 15. Fast water-loss / leak detection — DONE (2026-08-31)
Built as `core/leak_detector.py`, called every control-loop cycle from
`main.py` — deliberately NOT gated to the 60-cycle periodic block every
other periodic check uses, since detecting within one cycle (not up to
60 cycles later) is the entire point. Computes rate from real
wall-clock timestamps between the two most recent `level` readings, not
a reading-count/tick basis — correct regardless of poll cadence, and
deliberately decoupled from `drivers/physics_sim.py`'s own evaporation
simulation, which is a compressed-for-testing rate (~0.24 in/min in
simulated time), not a real physical one. Threshold (0.02 in/min, ~30x
a realistic real-world evaporation upper bound) is a real,
physically-grounded starting point, honestly not yet calibrated
against real tank geometry, same as `dosing_limits`' own placeholder
values. Raises CRITICAL (not WARNING) per `SAFETY_SPEC.md`'s own
explicit framing of water level as a critical-tier condition. New
`get_leak_status` assistant tool (`status` domain, always-on). Verified
via `scenarios.py::scenario_leak_detection` (4 checks: a slow
evaporation-plausible drop over a real 10-minute gap stays silent, a
fast drop over a real 2-minute gap raises a real CRITICAL alert, a
level RISE never falsely triggers regardless of magnitude) and a live
smoke test against the real running system. Original brainstorm text
kept below for context.

**Problem it solves:** `core/trend_analyzer.py` catches SLOW drift
against a rolling baseline — it's not built to catch a sudden leak (a
level sensor dropping fast, right now, not over a multi-reading
window). A major leak is one of the most common real aquaponics
failure modes, and today it's only as protected as "eventually the
level looks weird enough to flag as drift," not "a leak was detected
within one cycle."
**What it'd do:** a dedicated rate-of-change check on `level` readings
specifically — compare the most recent 2-3 readings' actual drop
against a real, physically-implausible-for-evaporation threshold, and
raise a CRITICAL alert (not just a WARNING drift signal) fast. Small,
focused, safety-relevant in the same category as the stale-sensor
freeze logic already in `contracts/mia_homestead_contract.py`.
**Effort:** small — a focused addition, not a new architecture.

## 16. Pest / disease observation log + knowledge base — DONE (2026-08-31)
Built as `core/pest_disease.py`, same two-part shape as
`core/species_registry.py` — a knowledge base
(`pest_disease_knowledge`, seeded with 6 real, commonly-documented
aquaponics/aquarium entries: aphids, powdery mildew, and root rot for
plants; ich, fin rot, and columnaris for fish, each with real symptoms
and guidance, not fabricated) plus a log of real observations
(`pest_disease_observations`) that can link to a known knowledge entry
or stand alone as something novel. Deliberately NOT an automatic
closed-loop refinement the way `species_registry.refine_from_experiment()`
works — a species' pH/EC range is a clean number an experiment can
confirm or extend, "was this symptom description accurate" is fuzzy
and textual, so knowledge entries stay a manual `add_knowledge()`
action, not an automated one, an honest scope decision stated in the
module's own docstring. Camera-based visual detection remains a real,
much larger future step (ties into the AI HAT/NPU hardware
`docs/OFFLINE_ASSISTANT_PLAN.md` already flags as unproven), not this
version — this is the manual log + lookup half only, as originally
scoped below. 3 new assistant tools (`get_pest_disease_info`,
`record_pest_disease_observation`, `get_pest_disease_history`), new
`pest_disease` domain. Verified via
`scenarios.py::scenario_pest_disease_tracking` (6 checks: baseline
seeding with the real entry count and no duplicate re-seeding,
knowledge lookup/add round-tripping correctly, an observation linking
to known knowledge vs. a genuinely novel unlinked one both retrieving
correctly) and a live smoke test against the real running system.
Original brainstorm text kept below for context.

**Problem it solves:** nothing logs or reasons about plant pests,
disease symptoms, or fish illness anywhere in this system.
**What it'd do:** a manual observation log (what was seen, on what
plant/tank, when) plus a symptom knowledge base in the same shape as
`core/species_registry.py` — common pest/disease symptoms per species,
with guidance, refined over time the same way species ranges are.
Camera-based visual detection is a real, much bigger stretch goal
(ties into the AI HAT/NPU hardware `docs/OFFLINE_ASSISTANT_PLAN.md`
already flags as unproven) — not v1.
**Effort:** medium for the manual log + knowledge base; large (and
hardware-gated) for any vision-based version.

## 17. Weather-aware alerts — DONE (2026-08-31)
Built as `core/weather_awareness.py` + `config/location.yaml`
(optional, unset by default — nothing else reads it). Uses Open-Meteo
(free, keyless, no account), matching this project's established
no-vendor-dependency stance. Two real, physically-grounded signals, not
invented thresholds: a real 32F frost threshold, and a comparison
against whatever's ACTUALLY currently planted's real documented
`temp_air_min`/`temp_air_max` (`species_profiles`, the same ground
truth `core/experiment_manager.py` and `core/biofilter_model.py` treat
as real). Deliberately opportunistic — the control loop never depends
on it; honestly skips (no fabricated forecast, no alert) if no location
is configured or Open-Meteo isn't reachable, same "nice when connected,
never required" posture as SMS delivery and cloud escalation. Checked
periodically (`should_check_now()`, default every 6h), same
gate-by-elapsed-time pattern `core/report_generator.py`'s
`hours_since_last_report()` already established. New `get_weather_status`
tool, new `weather` domain. Verified two ways, matching this feature's
own real-vs-simulated distinction: a live test against the real
Open-Meteo API (confirmed real current data for a real coordinate
pair) and `scenarios.py::scenario_weather_awareness` (5 checks, with
the network call stubbed at exactly its own boundary so the scenario
stays fast/deterministic while every other real code path — frost
math, species-range comparison, alert raising, `weather_checks`
logging — runs unmocked). Live smoke test against the real running
system confirmed it honestly reports no check on file, since no real
location has been configured yet — correct, not a bug; nobody's real
greenhouse coordinates were guessed. Original brainstorm text kept
below for context.

**Problem it solves:** the whole system reacts to what's happening
INSIDE the tank/cell — nothing looks outside. A frost or heat wave
warning, even a day ahead, is the difference between a proactive fix
and a dead crop.
**What it'd do:** an opportunistic online check (same "nice when
connected, never required" posture as SMS delivery and cloud
escalation — this system's core control loop must never depend on it)
against a free weather API for the greenhouse's real location, alerting
on frost/heat-wave conditions relevant to the currently-planted
species' documented temp ranges.
**Effort:** small-medium — mostly one new integration point, reuses the
existing notification path.

## 18. Cost / profitability accounting — DONE (2026-08-31)
Built as `core/finance_tracker.py`. Real gap found while building this,
fixed alongside it: `revenue_transactions` had a full schema and was
already READ by `viewer/export_dashboard_state.py`/`export_home_snapshot.py`,
but nothing anywhere WROTE to it — no `record_revenue()` existed, and
it had zero capability registration (never in `main.py`'s
`all_describables`, despite CLAUDE.md's own rule 2 that every service
needs one). Fixed: `record_revenue()` is now the first real write path,
`_tool_get_revenue_summary` moved from inline SQL in the assistant file
into this proper backing service, and `finance_tracker` is now
registered like everything else.

Real, honestly-stated limitation, not glossed over: cost is
SYSTEM-WIDE, not per-cell — `inventory_transactions` has no `cell_id`
in this schema, so no per-cell cost breakdown is claimed, even though
revenue IS cell-attributed. Only counts consumption of items with a
real known `unit_cost`; items without one are excluded from the total
and listed separately, never silently treated as $0 (which would
understate cost, not just omit unknown data). Feeding cost
(`core/fish_health.py`'s `feeding_events`) is deliberately NOT
cross-referenced in — `food_type` is free text, not a real foreign key
into `inventory_items`, and guessing a unit conversion would be a
fragile estimate dressed up as a real number; stated as a known gap
in the module's own docstring rather than faked.

3 new assistant tools (`record_revenue`, `get_cost_summary`,
`get_profitability_summary`), `revenue` domain keywords expanded
(cost/profit/margin/expenses). Verified via
`scenarios.py::scenario_cost_profitability` (4 checks: revenue
computes and records correctly; cost of a known-unit-cost item
computes correctly from real seeded consumption; an unknown-cost item
is correctly excluded from the total rather than counted as $0;
profitability nets real revenue minus real cost correctly) and a live
smoke test against the real running system. Original brainstorm text
kept below for context.

**Problem it solves:** yield is tracked; the actual economics (feed,
nutrient, electricity cost per harvest) aren't. Matters much more once
this is more than a hobby system.
**What it'd do:** tie real costs (inventory consumption already tracked
by `core/inventory.py`, power draw already tracked by
`modules/power_monitor.py`) to yield events to compute a real
cost-per-harvest and margin, not just revenue.
**Effort:** medium — mostly composing data that already exists across
modules, not new tracking.

## 2026-09-03 — brainstorm round 2: what commercial ag-tech advertises that this doesn't have yet

User's framing: build toward "the most advanced, useful, self-sustaining,
knowledgeable, and perfect system for agricultural production... the
brain behind revolutionary smart agricultural technology," explicitly
drawing on what real competing products advertise. Researched current
(2026) commercial greenhouse/aquaponics/precision-ag platforms — Priva,
Argus, Autogrow, IUNU LUNA, Root AI, and the broader precision-ag/
vertical-farming/traceability literature — before brainstorming, same
"ground it, don't invent blind" discipline as every prior round in this
doc. Sorted into three honest tiers: buildable now (software, no new
hardware), real but correctly hardware-gated, and out-of-scope-for-now
(named so nothing gets silently forgotten, not proposed to build blind).

### Tier 1 — buildable now, software-only, genuinely new

## 19. Succession/rotation planning — DONE (2026-09-03)
Built as `core/succession_planner.py`. Scoped as succession (what/when
to plant next), not true crop-family rotation science — see the
module's own docstring for why that distinction matters. Verified via
`scenarios.py::scenario_succession_planning` (9 checks, including a
real exclusion case reusing the documented Cucumber/Spinach
zero-temp-overlap pair) and a live smoke test. Original brainstorm
kept below for context.

**Problem it solves:** `core/bed_planting.py` tracks current and planned
plantings but never proactively suggests what comes next — a bed
approaching its `expected_harvest_date` just... becomes empty, with no
forward-looking suggestion, unlike commercial platforms' "crop
intelligence" scheduling.
**What it'd do:** watch `get_current_plantings()`'s harvest dates; as one
approaches, propose a next planting for that bed via the same
`_check_cell_compatibility()` logic `record_planting()` already
enforces, informed by `species_registry`'s real known-good ranges and
(once #22 exists) recent profitability by species. Proposal only — goes
through the same human-approval-adjacent pattern as
`propose_experiments_for_underperformance()`, never auto-plants.
**Effort:** small-medium — composes `bed_planting.py` +
`species_registry.py`, no new architecture.

## 20. Resource-efficiency / sustainability reporting — DONE (2026-09-03)
Built as `core/sustainability_report.py`, water-only (see the module's
own docstring for why energy is honestly excluded — no real load
telemetry exists, only solar generation and battery SOC). Real bug
caught by a live smoke test, not just scenarios: real yield with ZERO
water logged computed a literal 0.0 ratio, misleadingly reading as
"perfect efficiency" — fixed to report unavailable, same as the
zero-yield case. Verified via
`scenarios.py::scenario_water_efficiency_reporting` (4 checks) and a
live smoke test, twice (before and after the fix). Original brainstorm
kept below for context.

**Problem it solves:** water usage is already logged
(`bed_planting.record_water_usage()`/`get_water_usage()`) and power
draw is already tracked (`modules/power_monitor.py`), but nothing
computes efficiency from either — no gallons-per-lb-yield, no
kWh-per-harvest, no trend on either. Every commercial sustainability/
traceability platform researched (TraceX, Farmonaut) leads with exactly
this kind of resource-efficiency metric.
**What it'd do:** a new `core/sustainability_report.py` composing
existing `water_usage`, `power_telemetry`, and `yield_events` data into
a real efficiency report (gallons/lb, kWh/lb, trend over time) — no
carbon-accounting or emissions-factor guessing, which would be a
fabricated number dressed as real (same discipline `finance_tracker.py`
already holds cost estimates to).
**Effort:** small — same "compose data that already exists" pattern as
`finance_tracker.py`.

## 21. Harvest-to-sale lot traceability ledger — DONE (2026-09-03)
Built as `core/traceability.py`. Real gap found while scoping this:
`yield_events` had a full schema and was read everywhere but nothing
ever wrote to it, same shape as the `revenue_transactions` bug fixed
earlier — `record_yield()` is the first real write path. Also fixed
`_tool_mark_planting_harvested` bypassing `BedPlantingManager.
mark_harvested()` via raw SQL (same bug class caught 3 times before).
Verified via `scenarios.py::scenario_yield_recording_and_lot_
traceability` (9 checks including real tamper detection on the hash
chain) and a live smoke test against the real dev DB (migrated
non-destructively). Original brainstorm kept below for context.

**Problem it solves:** commercial ag-tech increasingly advertises
blockchain-based farm-to-fork traceability (TraceX, Transgenie) — "which
batch was this, what was it dosed with, when was it harvested, who
bought it." This system has all the underlying data (`dosing_events`,
`bed_plantings`, `yield_events`, `revenue_transactions`) but nothing
links them into one queryable lot record.
**What it'd do:** NOT a real blockchain — this project's own established
no-vendor-dependency stance (`CLAUDE.md`, the SMS/ordering corrections
earlier this project) argues against taking on an external chain/wallet
dependency for what's fundamentally a local record-linking problem.
Real equivalent: a `harvest_lots` table tying a `yield_event` back to
its originating `bed_planting_id` (and therefore every `dosing_event`/
`water_quality_test`/`pest_disease_observation` during that planting's
life) plus forward to any `revenue_transaction` it was sold in, with
each lot record hash-chained to the previous one (each row's hash
includes the prior row's hash) for local tamper-evidence — genuinely
useful if a customer or inspector ever asks "where did this batch come
from," without an external chain, gas fees, or vendor account.
**Effort:** medium — mostly a new linking table + query methods; the
hash-chaining is a small, well-understood pattern (same idea
`core/deploy_manager.py`'s rollback-history already uses informally).

## 22. Multi-week yield forecasting — DONE (2026-09-03)
Built as `core/yield_forecaster.py`. Real, explicit uncertainty bands
(never a single fabricated date) widened by real signals
(`sensor_confidence`, real stress alerts), capped rather than
unbounded. Real bug caught before the scenario even ran: the first
draft queried a nonexistent `alerts.cell_id` — fixed with a real
module-id-to-cell mapping read from `config/modules.yaml`. Verified
via `scenarios.py::scenario_yield_forecasting` (6 checks) and a live
smoke test (correctly capped a 21-day band from 177 real accumulated
alerts in the dev DB). Original brainstorm kept below for context.

**Problem it solves:** commercial "crop intelligence" platforms (IUNU
LUNA, Root AI) advertise multi-week-ahead yield forecasting from sensor
+ growth data. This system currently only compares expected vs. actual
AFTER harvest (`get_expected_vs_actual()`) — nothing projects forward.
**What it'd do:** a real statistical projection (not a fabricated
confident number) from `species_profiles.days_to_maturity` combined
with actual real-time growth signals this system already has (dosing
consistency, sensor confidence, water-quality-test cycle status) to
widen or narrow the harvest-date estimate as a planting progresses —
explicit uncertainty bands, same honesty discipline
`core/biofilter_model.py` already established for exactly this reason.
**Effort:** medium — genuinely needs real historical yield-vs-conditions
data to calibrate against, so this is a build-the-framework-now,
trust-it-once-the-pilot/first-real-harvests-exist feature, same
sequencing as drift detection was.

## 23. Data-driven dosing/climate recommendation layer — DONE (2026-09-03)
Built as `core/dosing_recommendations.py`. Advisory-only by
construction — composes `trend_analyzer`'s real drift signal and
`weather_awareness`'s real forecast, never touches `dosing_limits` or
`target_overrides`. Verified via
`scenarios.py::scenario_dosing_recommendations` (5 checks, including
proving those two tables are provably untouched by calling it) and a
live smoke test (honestly empty — no location configured, no current
drift). Original brainstorm kept below for context.

**Problem it solves:** Priva's own marketing leads with "AI-automated
irrigation... data-driven recommendations" layered on top of climate
computers. This system's control loop is real but purely
reactive/threshold-based (dose when out of range, hold when
inconsistent) — there's no layer that looks at trend + weather forecast
+ season and suggests a proactive adjustment before a threshold is even
crossed.
**What it'd do:** a new advisory layer reading `trend_analyzer.py`'s
existing drift signal, `weather_awareness.py`'s forecast, and time of
season, to generate a real suggestion ("pH trending toward the low end
and a cold front is forecast — consider an earlier proactive dose") —
surfaced via the assistant and the daily report, but explicitly
suggestion-only. **Never auto-executes** — dosing targets changing is
already gated behind `approve_parameter_change()`/experiments by this
project's own non-negotiable rules, and this stays inside that gate,
not around it.
**Effort:** medium — a genuine new reasoning layer, but composes three
already-built signal sources rather than adding new sensing.

## 24. Per-crop (not just system-wide) profitability — DONE (2026-09-03)
The one real schema change on this list:
`inventory_transactions.cell_id`, traced through `dosing_events` for
the one consumption path that's genuinely per-cell. `get_cost_summary()`/
`get_profitability_summary()` gained an optional `cell_id`, honestly
scoped to dosing consumption only (a restock or repair part has no
`cell_id` and is correctly excluded). Verified via
`scenarios.py::scenario_per_crop_profitability` (4 checks) and a live
smoke test against the real dev DB (migrated non-destructively).
Original brainstorm kept below for context.

**Problem it solves:** `finance_tracker.py`'s own docstring already
names this gap honestly — cost is system-wide only because
`inventory_transactions` has no `cell_id`, so margin can't be broken out
per species/crop the way commercial farm-management software
(KhetiBuddy, Farmonaut) advertises.
**What it'd do:** add `cell_id` to `inventory_transactions` (a real,
additive schema change — `schema/mia_homestead_schema.sql`'s own
convention is additive-never-destructive migrations), backfill nothing
(historical rows honestly stay unattributed rather than guessed), and
extend `get_profitability_summary()` to break out by cell/species once
the data exists to support it.
**Effort:** medium-large — the one item here that's a real schema
change, not just composing existing columns.

## 25. Spoken daily briefing at the beacon — DONE (2026-09-03)
Built as `core/voice_briefing.py`, using Piper (fully offline TTS,
matching this project's local-first stance) — confirmed installable
and working in this environment before building around it, not
assumed. Config-gated the same null-safe way as `location.yaml`/
`mia_home_sync.yaml`. Stops at producing a real audio file — actual
playback needs the beacon hardware (punch-list #5), not bought yet.
Verified via `scenarios.py::scenario_voice_briefing` (3 checks,
including real end-to-end synthesis when Piper is actually present)
and a live smoke test (a real 1.8MB `.wav` from a real report).
Original brainstorm kept below for context.

**Problem it solves:** `report_generator.py` already writes a real
natural-language daily report via the local model
(`generate_and_send()`); `self_preservation.py`'s beacon is real
hardware-adjacent (light/speaker) but only ever driven as an on/off
relay — the two have never been connected, even though "the AI speaks
the state of the greenhouse aloud" is exactly the kind of thing
"revolutionary" ag-tech marketing leads with.
**What it'd do:** pipe the already-generated report text through a
local TTS engine (e.g. Piper — small, fully offline, matches this
project's whole local-first assistant stance) out to the beacon's
speaker channel when someone's physically present
(`self_preservation.py` already knows this).
**Effort:** small-medium for the software (TTS pipeline + wiring) —
genuinely gated on the beacon hardware existing to hear it on, same as
punch-list item #5.

### Tier 2 — real, valuable, correctly gated on camera/NPU hardware

## 26. Computer-vision plant health / disease detection
Every 2026 precision-ag source researched leads with this — EfficientNetB0-class
disease classifiers reporting >99% test accuracy in the literature. This
project's own `pest_disease.py` docstring already names this as the
deliberate v2 step, tied to the AI HAT/NPU hardware
`docs/OFFLINE_ASSISTANT_PLAN.md` already flags as unproven in this
project's own environment. Not proposing to build blind — flagging that
the manual log/knowledge-base half (already done) is the correct v1,
and the camera half is real future work once NPU inference is proven,
not before.

## 27. Computer-vision fish health, behavior, and appetite-based feeding
Commercial aquaponics/aquaculture tech (per the research above) uses
camera modules + CV to detect fish disease symptoms and auto-adjust
feeding to observed appetite. This project's `fish_health.py` is
real but manual-log-only by design (same "no cheap way to continuously
weigh/count fish" reasoning already in that module's docstring). Same
NPU-hardware gate as #26 — naming it so it's not forgotten, not
proposing to fake camera data.

## 28. Camera-based ripeness/yield estimation
Vertical-farming platforms researched (IUNU, Root AI-class systems) use
computer vision to estimate ripeness/yield per plant, ahead of harvest.
Same NPU-hardware gate as #26/#27 — a real, named future capability
once vision inference is proven on this project's actual hardware
target, not before.

### Named but out of scope for now — flagged so they're not silently forgotten, not proposed to build blind

- **Robotic harvesting / autonomous guided vehicles.** Real 2026
  vertical-farming platforms researched (Octinion Rubion, Agrobot
  E-Series) deploy purpose-built harvesting robots costing far more than
  this entire pilot/full-scale BOM combined — genuinely a different
  capital-equipment category than a control/monitoring "brain" software
  system, not something to scope here without an explicit decision that
  this project should grow into hardware manufacturing/integration at
  that scale.
- **CSA / customer order management / storefront.** Revenue recording
  exists (`finance_tracker.py`) but nothing tracks customers, CSA
  shares, or order fulfillment — that's a farm-business/CRM layer
  adjacent to this project's actual scope (growing food with near-zero
  intervention), not core ag-intelligence. Worth a real scoping
  conversation before starting, not assumed wanted.
- **Regulatory/certification compliance documentation** (organic
  certification, food-safety audit logs). Real feature in commercial
  farm software, but genuinely speculative to build without knowing
  which certification (if any) is actually being pursued — the
  requirements differ by program and jurisdiction.
- **True multi-facility cloud sync** (Priva's cross-site Azure
  migration). This project already has single-site-to-MIA-Home sync
  (punch-list #7, done) — a second Homestead site to sync would need
  this project's own multi-site version of that, not relevant unless a
  second physical location is real.

## Status as of 2026-09-03

**All 7 Tier-1 items from round 2 (#19, #20, #21, #22, #23, #24, #25)
are now DONE** — see each entry above for what actually implements it,
what real bug it caught along the way, and how it was verified. Every
one shipped with a new scenario, a clean `self_audit.py` run, and a
live smoke test against the real dev DB, not just unit-level scenario
coverage. Tier 2 (camera/NPU-gated) and the explicitly-out-of-scope
items are unchanged — still real, still correctly not built yet.

## Status as of 2026-08-31

**Done:** #1, #2, #3, #5, #6, #7, #9, #10, #11, #12, #13, #14, #15,
#16, #17, #18 — see each entry above for what actually implements it
and how it was verified. Every item in the originally-picked roadmap,
and every item on the expanded "useful and necessary" list from the
2026-08-31 conversation, is now built (#14-18, all 5, in the priority
order that conversation set).

**Still genuinely open — both correctly gated on real hardware/data
that doesn't exist yet, not software gaps:**
- **#4** (seasonal awareness) — needs a full seasonal cycle of real data.
- **#8** (firmware OTA rollback safety) — needs the Safety MCU firmware
  actually deployed and iterated on first.

Nothing else is currently queued. The physical pilot build
(`docs/PILOT_VS_SCALE.md`, pilot kit sitting in `inventory_orders` as
`status='proposed'`, `python3 core/order_queue.py`) is the real
milestone from here — the software side has caught up to it.

## Original recommendation on where to start (historical)

If you want the highest value for the least effort right now: **#9
(explain-yourself consistency), #10 (periodic self-report), and #7
(dead-man's-switch escalation)** are all small, mechanical extensions
of things already built — no new architecture, just filling in gaps
the same way this session caught the dosing_events and hardware
requirement gaps. **#1 (consumable forecasting)** is similarly cheap
and directly useful once real consumption data exists.

**#2, #3, #5** (drift/anomaly/confidence) are the ones that actually
make the system "get smarter" in the way the experiment system does —
but they need real operational data to be worth building well, which
argues for building them once the pilot is running, not before.
