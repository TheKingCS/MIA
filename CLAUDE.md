# CLAUDE.md — MIA Homestead

This file is loaded automatically by Claude Code. Read it before making
any change. It's dense on purpose — the human-readable versions of
everything here live in `docs/`; this file exists to tell an AI agent
what's mandatory, not to explain why at length.

## What this is

A homestead greenhouse aquaponics control/monitoring system, built
simulation-first. Currently fully proven in software (scenario suite,
live-tested modules) with zero real hardware deployed yet. The next
real milestone is a 5-gallon pilot build — see `docs/PILOT_VS_SCALE.md`.

## Before you touch anything

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 -c "import sqlite3; sqlite3.connect('mia_homestead.db').executescript(open('schema/mia_homestead_schema.sql').read())"
python3 drivers/simulator.py --db mia_homestead.db --setup
python3 scenarios/scenarios.py        # must print 125 passed, 0 failed
python3 core/self_audit.py            # must say "All checks passed"
```

For a live dev session (not just running scenarios): `python3 main.py --db
mia_homestead.db` and `python3 drivers/simulator.py --db mia_homestead.db
--run` are two SEPARATE long-running processes sharing the DB file — the
simulator writes fake sensor data, main.py's control loop reads it. Run
both, or every sensor goes stale within `STALE_THRESHOLD` (10 min) and
every module falls back to its safety state.

If either of those doesn't pass cleanly on a fresh checkout, something
is wrong with the environment, not necessarily the code — check Python
version (3.10+ required, uses `X | None` type hints throughout) before
debugging logic.

## Non-negotiable architectural rules

These are enforced by code, not convention — violating them breaks the
build, not just the spirit of the project:

1. **Every control module** (`modules/*.py`) subclasses
   `MiaHomesteadModule` and MUST implement `read_sensors()`,
   `evaluate()`, `describe_capabilities()`, and
   `describe_hardware_requirements()`. Missing any of the last two
   raises `TypeError` at instantiation — Python's ABC mechanism, not a
   linter. `describe_hardware_requirements()` can validly return `[]`.

2. **Every service** (`core/*.py` that isn't a pure utility) implements
   `Describable` the same way. Pure utilities (no physical hardware, no
   self-description needed) don't need to.

3. **`verification_evidence` on every `Capability` must be real.** Cite
   an actual scenario test name or a specific, dated description of
   what was manually run and confirmed. An empty list is honest for
   something genuinely untested. A vague or fabricated string is not
   acceptable — this field is what makes
   `docs/FEATURES_AND_CAPABILITIES.md` a proof document, not another
   description.

4. **New module checklist** (full version in
   `docs/CAPABILITY_REGISTRATION.md`):
   - Implement the logic.
   - Implement both `describe_*` methods in the same sitting, with real
     verification evidence once you've actually tested it.
   - Register in `config/modules.yaml` (control modules) or add to
     `all_describables` in `main.py` (services).
   - Add a matching assistant tool in
     `assistant/greenhouse_assistant.py` for anything that's a safe,
     commandable action — NOT for things that would bypass safety
     gating (see exception below).
   - Run `python3 core/self_audit.py`. All 5 checks must pass or be an
     understood, intentional exception.

5. **Never expose direct dosing/actuator commands or raw notification
   sends as bare assistant tools.** Dosing happens through the
   automatic control loop or the experiment/approval system
   (`core/experiment_manager.py`); notifications fire automatically
   based on severity. A casual chat command bypassing either would
   defeat the safety architecture. `self_audit.py` step 5 will flag
   these as "gaps" — they're intentional, not something to fix.

6. **Safety-relevant or spend-relevant actions require human approval**
   — mirrors `inventory_orders` (propose then approve/deny) and
   `parameter_change_proposals` (experiment result then propose then
   human approves). Don't add a path that bypasses this pattern for
   anything touching dosing targets, real orders, or config rollback.

7. **`docs/FEATURES_AND_CAPABILITIES.md` and `docs/HARDWARE_BOM_LIVE.md`
   are auto-generated — never hand-edit them.** If you change how
   they're generated, verify by deleting the file and running
   `main.py` for real to confirm it regenerates (this exact bug — a
   generator that only returned a string instead of writing to disk —
   was caught and fixed once already; don't reintroduce it).

## Directory quick reference

```
contracts/       base classes (MiaHomesteadModule, Describable, Capability)
modules/         control-loop modules (aquaponics, power, self-preservation)
core/            services (inventory, maintenance, registries, diagnostics,
                 backup, species/planting/experiments, assistant support)
firmware/        ESP32 Safety MCU firmware - compiles clean (platformio.ini),
                 still never run on real hardware
config/          modules.yaml, layout.json, device roles, plumbing.yaml,
                 irrigation_schedules.yaml (which grow beds get
                 scheduled flood/drain, and how often — see
                 core/irrigation.py),
                 location.yaml (optional — real lat/long for weather
                 awareness only, unset by default, nothing else reads it)
                 (these YAML files ARE the source of truth for physical
                 wiring/plumbing - edit them, not code, for physical changes)
schema/          single schema.sql, additive - never destructive migrations
scenarios/       safety regression suite - run before any control-logic change
drivers/         simulator.py (fake data for --run/setup_demo_cell,
                 incl. simulated power_telemetry — what the LIVE system
                 actually uses),
                 physics_sim.py (closed-loop dosing + climate/DO/CO2
                 dynamics — scenarios/scenarios.py's test harness ONLY,
                 never imported by main.py or simulator.py --run),
                 atlas_scientific_driver.py (real I2C, untested on hardware)
viewer/          3D digital twin (live "go here" fault locator), the
                 ops dashboard (dashboard.html), and the planting
                 planner (planting_planner.html, to-scale grow-bed
                 layout, planned vs. active plantings) — three separate
                 pages, three separate export scripts/state files, all
                 auto-regenerated by main.py every control cycle
deploy/          self-healing deploy/rollback — see deploy/README.md before
                 touching core/deploy_manager.py or the systemd unit files
docs/            everything else - see index below
```

## Docs index — when to read which

- `SAFETY_SPEC.md` — failsafe philosophy, read before touching anything dosing/power-related
- `MCU_PROTOCOL.md` — Pi<->Safety MCU wire format + device pairing handshake
- `SIMULATION_STRATEGY.md` — the four-tier simulate-before-hardware process
- `PILOT_VS_SCALE.md` — 5-gallon pilot plan vs. full build, what carries over
- `CAPABILITY_REGISTRATION.md` — the full new-module checklist (condensed above)
- `DEVICE_SETUP_GUIDE.md` — zero-technical-knowledge physical setup walkthrough
- `HARDWARE_BOM_CURRENT.md` — hand-researched pricing/sourcing (static notes)
- `HARDWARE_BOM_FULL_TIERS.md` — full real sourcing for all three build tiers (test/small/full-scale greenhouse), confirmed-vs-estimated pricing, open sizing/wiring decisions flagged
- `HARDWARE_BOM_LIVE.md` — auto-generated running BOM (never hand-edit)
- `FEATURES_AND_CAPABILITIES.md` — auto-generated proof document (never hand-edit)
- `SUSTAINING_FEATURES.md` — brainstormed features not yet built, with effort sizing
- `OFFLINE_ASSISTANT_PLAN.md` — converting the assistant off the cloud API to a fully local model; the tool-count/gating problem this needs to solve before local rollout
- `MIA_HOME_SYNC_PLAN.md` — scoping for punch-list item #7 (pushing summarized state to MIA Home); what's real on the MIA-repo side, what's genuinely undecided (transport, hardware target), what's buildable here now vs. needs a session in `~/Projects/MIA`
- `deploy/README.md` — the self-healing deploy/rollback mechanism (core/deploy_manager.py + systemd crash-loop layer); two real bugs found by actually testing it, not by reasoning about it — read before touching either the app-level watch or the unit files

## Current state (honest summary)

**Fully built and proven in software:** control loop, safety fallback,
simulation (3 tiers), scenario regression suite, digital twin with
per-object fault locating, inventory/maintenance/revenue tracking,
human-approval order queue, capability + hardware registries with
changelog, config backup/rollback with automatic post-update watch,
species/planting/experiment system with live target overrides,
infrastructure knowledge (wiring/plumbing) feeding real diagnostics,
dead-man's-switch escalation, consumable forecasting, periodic reports,
self-audit covering registration completeness, verification coverage,
AND conversational tool coverage, greenhouse climate control
(fan/heater, temp- and humidity-driven, `modules/climate_control.py` —
closes the gap found during hardware sourcing 2026-08-31 where the
schema anticipated these actuators but nothing implemented them), and
dissolved-oxygen monitoring (`modules/aquaponics_cell.py` — alert-only,
opt-in per cell based on whether a DO sensor is actually registered, so
optional hardware that was never bought never generates noise), and
water-temp thermal-stress monitoring (same file — checks a real reading
against the actually-stocked species' real documented range from
species_profiles, via tanks.species; unstocked or unrecognized species
stays silent rather than guessing a target), and a real tank
water_heater actuator driven off that same check for a low reading (a
new actuators.type, distinct from climate_control.py's air 'heater' —
a high reading still only alerts, since no chiller is built), and real
planting PLANNING (`core/bed_planting.py`'s `plan()`/`convert_to_active()`,
2026-09-01, user request) — stage a future planting before it's
physically done, then convert it once it actually happens; viewer/
planting_planner.html visualizes every real grow bed to scale with its
planned/active/recent plantings, read-only by design (writes go through
the assistant tools, same propose-then-real pattern as everything else
here). Also, `drivers/physics_sim.py`'s closed-loop scenario test
harness (2026-09-01, user request) now models real cause-and-effect for
this session's newer actuators the same way it already did for pH/EC
dosing — heater/fan/water_heater push temp/humidity/CO2 while commanded
on (tracked as ongoing state, not one-shot pulses), air heat-loss and
humidity/CO2 rise without ventilation explain why they're needed at
all, water temp thermally couples to air temp, DO relaxes toward a
temperature-dependent equilibrium, and a CO2 injector pulse raises CO2
proportionally to duration. Scenario proof, matching
scenario_ph_crash_response's existing standard: a cold/CO2-depleted
reading triggers the actuator AND the reading actually recovers over
subsequent ticks, not just that a command was issued.

Also (2026-09-01, user request): the alert LIFECYCLE, closed for the
first time — `alerts.acknowledged`/`resolved` existed in the schema
since the start and `raise_alert()` always read/wrote `resolved=0`,
but nothing anywhere ever marked one resolved (only the separate
`help_requests` table, self_preservation.py's beacon, ever got real
ack/resolve logic). `core/alert_manager.py`: `resolve_alert()`/
`acknowledge_alert()` for precise human-driven resolution, plus
`check_stale_alerts()` — a periodic (60-cycle block), honestly-labeled
HEURISTIC sweep that auto-resolves any alert not re-raised in 30 min,
logged distinguishably from a human resolving it. A genuine recurrence
after resolution creates a real new alert row (raise_alert()'s dedup
only ever matches unresolved rows) — resolving never permanently
suppresses anything. Live-verified against the real accumulated
backlog: 74 unresolved alerts before the sweep, 72 correctly
auto-resolved as genuinely stale (some untouched for many real hours),
the 2 genuinely current conditions correctly left alone; manually
resolving one of those two, then watching the control loop re-raise a
real NEW row for the same still-true condition on its own, confirmed
the recurrence behavior for real, not just in a scenario.

scheduled irrigation (`core/irrigation.py` — a periodic check, NOT
a MiaHomesteadModule, since it's clock-driven with no sensor to go
stale; only the "scheduled" half of watering_mcu.yaml's description is
built, "moisture-triggered" stays honestly unbuilt since no moisture
sensor type exists in sensors.type at all), and circulation-stall
detection (`core/circulation_monitor.py` — a flow sensor reading
near-zero while the circulation_pump is commanded on means a probable
seized pump or clogged filter that power/level monitoring alone can't
see; opt-in per cell like DO, alert-only like leak_detector.py).

While fixing this, found and fixed a real pre-existing bug in
`core/sensor_confidence.py`: it used Python's local `date.today()`
against `calibration_due` values written via SQLite's `date('now',
...)` (UTC) — the two disagree by a day near a UTC/local day boundary,
which is exactly what made `scenario_sensor_confidence` fail live on
2026-08-31. Same failure-mode class as the isoformat/space-separator
bug already documented below, just the UTC-vs-local variant. Fixed by
using `datetime.utcnow().date()`, matching the rest of the codebase's
UTC convention.

Also now built (2026-08-31): supplemental grow-light and CO2
enrichment, folded into `modules/climate_control.py` alongside heater/
fan/humidity — both opt-in per cell like DO. CO2 is treated more
conservatively than everything else in that module: injection is a
short cooldown-limited pulse (never continuous), and a reading at/above
5000ppm (OSHA's 8-hr PEL) raises a critical alert and refuses to inject
regardless of trend — this one is a real human-safety concern, not just
yield optimization. This closes the schema-forward-declared-vs-
implemented audit's last two items — every `sensors.type`/
`actuators.type` value declared in the schema now has real code behind
it.

**Compiles clean, unverified on real hardware:**
`firmware/safety_mcu/safety_mcu.ino` now builds successfully via
PlatformIO (`platformio.ini` in that directory — `pio run`) against
ESP32 + ArduinoJson 6.21.6, verified 2026-08-30 with zero source
changes needed. Still never run on a real board. Known gaps documented
in `firmware/safety_mcu/README.md`, most importantly the
actuator-ID-to-pin mapping placeholder that needs resolving before real
dosing commands should be trusted to it.

**Not started:** anything requiring physical hardware to actually exist
— the pilot build is the real next milestone, not more software.

## Common failure modes to watch for (all previously caught and fixed once)

- A doc "generator" that returns a string but never writes it — always
  verify by deleting the output and re-running, not by reading the code.
- A new `Describable` class that's never added to `main.py`'s
  registration list — `self_audit.py` step 2 catches this.
- A real backend method with no assistant tool exposing it
  conversationally — `self_audit.py` step 5 catches this (heuristic,
  verify hits by hand).
- Timestamp format mismatches between Python's `.isoformat()` (T
  separator) and SQLite's `datetime('now')` (space separator) when
  hand-constructing test data — caused a real test bug once.
- Python's local `date.today()`/`datetime.now()` compared against a
  value written via SQLite's `date('now', ...)`/`datetime('now')`
  (always UTC) — disagree by a day near a UTC/local day boundary.
  Always use `datetime.utcnow()` in Python code that reasons about
  anything SQLite wrote a `now`-based timestamp for. Caught for real in
  `core/sensor_confidence.py`, 2026-08-31.
- A `MiaHomesteadModule.read_sensors()` that doesn't filter by sensor
  `type` pulls every sensor on the cell, not just the ones its own
  `evaluate()` acts on — its inherited staleness/retry ladder then
  independently alerts on types another module already owns, as
  duplicate, misattributed alerts. Caught for real in
  `modules/aquaponics_cell.py` (was alerting on `temp_air`/`humidity`/
  `light`/`co2`/`flow`/`level` staleness — none of which it ever acts
  on), 2026-08-31. Filter `read_sensors()`'s query to exactly the types
  `evaluate()` consumes.
- A `SensorReading.sensor_id` that isn't a real `sensors.id` (e.g.
  `modules/power_monitor.py` synthesizing one from `power_telemetry`'s
  own row id) can numerically collide with a real sensor's id — the
  base class's staleness machinery looks it up in `sensors` and
  misattributes the alert to whatever real sensor happens to share
  that number. Caught for real 2026-09-01 (id 8 collided with the
  pilot cell's real temp_water sensor). Use a fixed value outside the
  real id space (a negative sentinel — `sensors.id` is always a
  positive autoincrement rowid) for any synthetic, non-table-backed
  reading.
- A new `sensors.type` added to `drivers/simulator.py`'s
  `SIM_SENSOR_DEFS` (what `Simulator` — the `--run` real-time driver —
  knows how to drift) is a DIFFERENT question from whether
  `setup_demo_cell()` should auto-create a sensor row of that type.
  Optional hardware (DO/flow/light/co2/water_heater) added this session
  needs the former (so a cell that HAS one stays fed) without the
  latter (so a cell that doesn't have one stays a true "not bought"
  test case) — `BASE_CELL_SENSOR_TYPES` is the explicit list
  `setup_demo_cell()` actually uses, deliberately narrower than
  `SIM_SENSOR_DEFS`. Caught for real 2026-09-01 before it shipped
  (would have silently invalidated every "no sensor configured ->
  stays silent" scenario).
- Sensor noise/drift values tuned for a quick, visible demo (many
  simulated ticks in a short scenario run) can be wildly unrealistic at
  a REAL wall-clock tick interval — `drivers/simulator.py --run`'s
  `Simulator` class produced `level` noise large enough to imply a
  leak-detector-triggering rate of change every few real 5-second
  ticks, with nothing actually wrong. Scenarios never caught this: they
  call `.tick()` directly with no real elapsed time between calls, so
  `core/leak_detector.py`'s real-wall-clock-rate math never engaged.
  Caught for real running `--run` continuously for the first time,
  2026-09-01. When sizing simulated noise for any value a rate-of-
  change check reads, work backward from the real threshold at the
  real tick interval, not from "looks reasonable per-tick."

## Git conventions used so far

Commit messages describe what was built AND what was proven live
(specific numbers/results, not just "added feature X"). Look at `git
log` for the established tone before writing new commit messages.
