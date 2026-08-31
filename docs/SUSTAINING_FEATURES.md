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

## 15. Fast water-loss / leak detection — not yet built
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

## 16. Pest / disease observation log + knowledge base — not yet built
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

## 17. Weather-aware alerts — not yet built
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

## 18. Cost / profitability accounting — not yet built
**Problem it solves:** yield is tracked; the actual economics (feed,
nutrient, electricity cost per harvest) aren't. Matters much more once
this is more than a hobby system.
**What it'd do:** tie real costs (inventory consumption already tracked
by `core/inventory.py`, power draw already tracked by
`modules/power_monitor.py`) to yield events to compute a real
cost-per-harvest and margin, not just revenue.
**Effort:** medium — mostly composing data that already exists across
modules, not new tracking.

## Status as of 2026-08-31

**Done:** #1, #2, #3, #5, #6, #7, #9, #10, #11, #12, #13, #14 — see
each entry above for what actually implements it and how it was
verified. Every item in the originally-picked roadmap is now built.

**Newly added 2026-08-31, roughly in priority order** (per a conversation
about what's still missing for this to be genuinely "useful and
necessary," not just more of what's already built): **#14 (fish health/
mortality/feeding tracking) — DONE**, see above. **#15 (fast leak
detection)** is the other item called genuinely necessary — both are
about preventing the kind of loss that erodes trust in an unattended
system, which is the whole premise here. Next up. **#16 (pest/disease
log)** and **#17 (weather-aware alerts)** are strong seconds. **#18
(cost accounting)** matters more once selling commercially than for a
homestead.

**Still genuinely open from the original roadmap — both correctly
gated on real hardware/data that doesn't exist yet, not software
gaps:**
- **#4** (seasonal awareness) — needs a full seasonal cycle of real data.
- **#8** (firmware OTA rollback safety) — needs the Safety MCU firmware
  actually deployed and iterated on first.

The physical pilot build (`docs/PILOT_VS_SCALE.md`, pilot kit sitting
in `inventory_orders` as `status='proposed'`,
`python3 core/order_queue.py`) remains the real milestone once the
software side settles, alongside whatever's built from #14-18.

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
