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
python3 scenarios/scenarios.py        # must print 200 passed, 0 failed
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

**A real bug found by actually looking at the rendered dashboard, found
and closed 2026-09-02:** the user asked for a visual/dashboard polish
pass; getting Playwright rendering working (the user installed the
missing `libnspr4`/`libnss3` system libs) surfaced something a pure DB
query never would have: `viewer/journal.html`'s most recent 100
entries were ALL "Dosed ph_down" for pilot_cell, ~5 real seconds apart,
668 in the last hour alone. Root cause: `docs/PILOT_VS_SCALE.md`'s own
trimmed pilot scope deliberately has no ph-down pump ("pH-up only to
start" — confirmed live, pilot's only dosing actuator is `pilot_ph_up_
pump`), but `modules/aquaponics_cell.py`'s `_dose_command()` never
checked whether a real actuator existed before proposing a correction
— it logged a real `dosing_events` row and issued a real
`ActuatorCommand(actuator_id=-1, ...)` every single cycle, completely
unconstrained, because `_within_dosing_interval()`'s old "no
`dosing_limits` row configured" fallback returned `True` ("nothing to
enforce yet") instead of blocking. Two fixes: (1) `_dose_command()` now
checks actuator existence FIRST — no real pump means a real, honest
warning alert instead of a fake dose, same "opt-in hardware, alert
instead of faking it" discipline already used for
`_evaluate_temp_water()`'s water_heater check and `_evaluate_ec()`'s
"no auto-correction for EC too high"; (2) `_within_dosing_interval()`'s
missing-limit fallback now fails CLOSED (blocks + warns) instead of
open — confirmed live that every real actuator in this system already
has a real configured `dosing_limits` row, so this is now only ever a
genuine configuration-error case, not a normal missing-hardware one.

**Caught immediately, before shipping**: the first version of fix #1's
warning message embedded the live pH value (from `rationale`),
defeating `raise_alert()`'s dedup exactly like the already-documented
"dose blocked" regression from earlier this session — 5-7 distinct
rows had already accumulated in the few minutes before this was
caught by re-reading the journal export. Fixed to static text before
it could spread further, and the scenario strengthened to explicitly
assert dedup (`occurrence_count` bumps, not new rows) so this specific
regression class can't slip through unnoticed again.

Verified: 2 new scenarios (`dosing_no_actuator_alerts_instead_of_
faking`, `dosing_no_limit_configured_blocks_and_alerts`) — 200 passed,
0 failed overall, self_audit clean. Live-verified in full: restarted
`main.py`, confirmed the fake-dosing counter froze completely (was
climbing every ~5s, now static across 15+ real seconds), confirmed the
real warning alert fires and dedups to one row with `occurrence_count`
climbing (not new rows), cleaned up 9,997 fictional `dosing_events` +
9,997 fictional `actuator_events` (`actuator_id=-1`) rows accumulated
since 03:16 that morning, and the 7-row alert backlog from the
self-caught regression, both through the real `AlertManager`/direct
cleanup with a logged rationale — not silently deleted.

**Day-one hardware readiness — all 4 items done (2026-09-02, user
request, see `docs/DAY_ONE_READINESS.md`):** #4 (override switch),
#1 (notification config), #2 (serial transport, below) and finally
**#3 — firmware's blocking pulse, fixed.**
`firmware/safety_mcu/safety_mcu.ino`'s `executePulse()` used to block
the whole `loop()` for up to 3 seconds via `delay()` — the firmware
README's own former gap #2, directly in tension with `SAFETY_SPEC.md`'s
manual-override requirement, since `readIncomingSerial()` (and, once
wired, a physical override switch's GPIO read) went unchecked that
whole window. Rewritten as a per-slot, non-blocking `millis()`-based
state machine: `executePulse()` starts the pulse and returns
immediately; a new `checkPulseCompletion()`, called every `loop()`
iteration, turns it back off and sends the real `"executed":true` ack
once the actual elapsed time is up — per-slot (not one global flag) so
two different actuators can legitimately pulse concurrently, and a
second command for a slot already mid-pulse is correctly rejected
(`"pulse_already_in_progress"`) rather than starting an overlapping
pulse on the same relay. `enterFallback()` now also cleanly aborts any
in-progress pulse rather than leaving a misleading ack pending.
Re-verified with a real `pio run` (`.venv/bin/platformio`, found after
`which pio` initially failed — it just wasn't on bare `PATH`): compiles
clean, RAM 21988/327680 bytes, Flash 281613/1310720 bytes,
near-identical footprint to the prior baseline as expected. This is the
one item of the four that couldn't be exercised beyond "compiles
clean" — no real board exists yet to flash it onto, same honest gate
the firmware's own README already holds every other claim to. With all
four done, nothing software-side is left blocking the pilot build.

**Day-one hardware readiness, item #2 — real MCU serial transport
(2026-09-02, user request, see `docs/DAY_ONE_READINESS.md`):** the
biggest of the four day-one gaps. Confirmed by grep before touching
anything: `core/device_registry.py` already built real `pair_confirm`
payloads (`build_pair_confirm_payload()`) but nothing anywhere ever put
a byte on a wire — `announce_device()` was explicitly "manual test call
today," and `main.py`'s `execute_command()` was explicitly a "v0.1
stand-in for real MCU dispatch," logging only. This sat squarely on the
critical path for `docs/PILOT_VS_SCALE.md`'s own Priority #1 (flash and
prove the firmware) and #3 (a real device pairing).

Three new pieces: `drivers/mcu_serial.py` (the wire protocol —
`MCULink` wraps a duck-typed port object, matching `pyserial`'s
interface, rather than always constructing a real `serial.Serial`
itself — same dependency-injection precedent as
`core/deploy_manager.py`'s `repo_path` override — which is what makes
the whole protocol layer testable today against a fake in-memory port,
zero real hardware needed); `core/device_registry.py`'s new
`listen_for_announce(link)` (reads a real message off a real link,
routes a real `announce` through the existing `announce_device()`
pairing logic, sends `pair_confirm` back over that same link once
paired — closing the actual handshake `build_pair_confirm_payload()`'s
own docstring said it was "ready the moment a transport layer is
built" for); `core/mcu_transport.py`'s new `McuTransportManager`
(scans for and pairs new devices — closing
`docs/DEVICE_SETUP_GUIDE.md`'s own promise that "the system checks for
it on its own within a few seconds... within about a minute," which
nothing actually implemented before this — sends heartbeats, dispatches
real actuator commands over the correct paired link, and raises a
real, deduplicated CRITICAL alert on a real `fallback_active:true`
status report, the actual version of `SAFETY_SPEC.md`'s own "safety MCU
failed to hear from Pi" critical example). `main.py`'s
`execute_command()` now tries a real send first, falling back to the
exact same simulated-log line as before when no real MCU is paired for
that actuator — unchanged behavior for every actuator in this
environment today. New `get_mcu_transport_status` assistant tool.

Verified: 4 new scenarios (12 checks) against a real fake in-memory
serial port — a real `announce` message results in real pairing AND a
real `pair_confirm` sent back; a command for a paired actuator is
genuinely sent over its real link while an unpaired one correctly
signals fallback; a real `fallback_active:true` report raises a real
deduplicated CRITICAL; scan pacing is real and enforced (same
`is_due()` pattern `core/mia_home_sync.py` already established). 193
passed, 0 failed overall, self_audit clean (33/33 verification
coverage). Live-verified further than the scenarios: restarted
`main.py` in this actual sandbox, which genuinely has 8 virtual serial
ports (`/dev/ttyS0`-`7`) — the real scan found them, real
`open_port()` attempts correctly failed with a real I/O error (no
functioning UART hardware attached) and logged a warning without
crashing, normal `EXECUTE (simulated): ...` dispatch continued exactly
as before, and the scan didn't re-trigger over 20+ real seconds/
multiple cycles — confirmed the pacing holds under genuine wall-clock
time, not just a scenario's synthetic backdated timestamp.

**Day-one hardware readiness, item #1 (2026-09-02, user request — see
`docs/DAY_ONE_READINESS.md`):** critical alerts were silently inert —
`main.py` constructed `NotificationConfig()` with zero arguments,
every run, with no way to set real SMTP/contact values short of
hand-editing `main.py`'s source, unlike every other configurable
subsystem in this project (`location.yaml`, `irrigation_schedules.yaml`,
`mia_home_sync.yaml`). Fixed with `NotificationConfig.from_config()`
(same `from_config()` pattern `core/irrigation.py` already uses),
reading the new `config/notifications.yaml` — missing/empty values
behave exactly like the old bare constructor (purely additive, nothing
that worked before changes), matching `location.yaml`'s honest-null
precedent. `main.py` now calls `NotificationConfig.from_config()`
instead of the bare constructor. Two new scenarios (honest default
when the file's missing; real values from a real file actually reach
the dataclass, unknown future keys ignored rather than crashing). 181
passed, 0 failed overall, self_audit clean. Live-verified: restarted
`main.py`, confirmed clean startup reading the real (still-empty)
config file, and confirmed a live `dispatch("critical", ...)` call
against it still safely no-ops without raising — real SMTP delivery is
correctly still a day-1 human action (a real account/credentials),
this closes the wiring gap, not that gate.

**Day-one hardware readiness, item #4 (2026-09-02, user request —
see `docs/DAY_ONE_READINESS.md`):** the pilot's own shopping list never included
the `SAFETY_SPEC.md`-required physical override switch, despite the
pilot's whole stated purpose being proving the safety chain end to
end — `docs/HARDWARE_BOM_FULL_TIERS.md` already priced this for full
scale citing the same requirement, it just never made it into the
trimmed pilot list. Added (`drivers/simulator.py`'s
`seed_pilot_shopping_list()`, real sourced price — Heavy-Duty DPST
Toggle Switch, 20A/125V, ~$6.99), pilot total now ~$263 (was ~$256).
Live-verified: ran the seed function against the real `mia_homestead.db`,
confirmed it added exactly the one new item (the other 7 already
existed from earlier in the session) with a real `inventory_orders` row
in `status='proposed'`, same human-approval gate every purchase in this
project goes through.

**MIA Home sync, automated end-to-end (2026-09-02, user request):**
`docs/MIA_HOME_SYNC_PLAN.md`'s transport step was the one thing left
manual — a human had to copy `viewer/home_snapshot.json` onto MIA
Home's watched folder by hand. `core/mia_home_sync.py`'s `MiaHomeSync`
(a plain `Describable`, not a `MiaHomesteadModule` — same "no sensor
reading to go stale" reasoning `core/irrigation.py`'s docstring already
gives for the identical choice) pushes it automatically via `rsync`
once `config/mia_home_sync.yaml`'s `destination` is set (null =
honestly skipped, same precedent as `config/location.yaml`), paced by
a real, enforced `interval_minutes` (backed by one `system_heartbeat`
row per attempt — the same row paces both "was the last successful
sync recent enough" and "did we just try and shouldn't hammer an
unreachable host again yet"). `destination` accepts either a plain
local path (today's reality — both projects on this one machine) or a
`user@host:path` remote (real deployment's reality once Homestead's Pi
and Home's Ryzen/Radeon desktop are physically separate) — the exact
same `rsync` command handles both, so moving from dev to real
deployment is a config change, not a code change. A push failure
(unreachable host, no SSH key yet, destination full) raises a real
deduplicated warning alert and retries next interval — never crashes
the control loop over a transport problem, matching this session's
broader resilience work. New `get_mia_home_sync_status` assistant
tool for visibility. Four new scenarios, including a real (not mocked)
`rsync` push to a real local destination and a real failed push
against an unreachable path. Live-verified further than "the scenario
passes": restarted `main.py` with `config/mia_home_sync.yaml`'s
`destination` actually set to this environment's real MIA path,
watched the very first cycle push for real, confirmed the file landed
on the MIA side, then ran MIA's own real `HomesteadManager.
scan_for_new_snapshots()` and confirmed it picked up the freshly-pushed
file — the whole pipeline, fully automated, proven live in both
directions. Also found the MIA-side integration
(`core/homestead_manager.py` + widget) was already built in a prior
session (MIA commit `08d41f4`) — this repo's own
`docs/MIA_HOME_SYNC_PLAN.md` was just stale about it, corrected
alongside a real small gap the first-ever real transport run exposed:
MIA's `.gitignore` was missing a `homestead_snapshots/*` entry (MIA
commit `b8727e6`).

**The sensor feed died for over an hour with nothing restarting it,
found and closed 2026-09-02:** `drivers/simulator.py --run` crashed
outright on `sqlite3.OperationalError: database is locked` after ~2
real days of continuous operation, and simply stayed dead — found via
`SELECT MAX(timestamp) FROM sensor_readings` showing the last write was
1h41m in the past. Root cause: `main.py` and `drivers/simulator.py
--run` are two independent processes, both writing the same SQLite file
on their own 5-second interval, under SQLite's default rollback-journal
mode (locks the WHOLE file during a write) and default 5-second
busy_timeout — a real, recurring collision risk for two always-on
daemons, not a one-off fluke, and the simulator's tick() loop had zero
retry/resilience, unlike main.py's own already-established "log and
continue" pattern for its 5 export calls. Worse, most of main.py's own
per-cycle body (dosing/control decisions via registry.run_all_cycles()
— though that already has real per-module isolation — plus
diagnostics, leak/circulation checks, and the whole 60-cycle
maintenance/backup/report block) had no exception handling at all
either, meaning main.py itself was one unlucky lock collision away from
the exact same fate.

Fixed with defense in depth, not just a patch on the one thing that
happened to crash: (1) `core/module_registry.py`'s real `__init__` (the
connection main.py actually uses) now opens with `timeout=30.0` and
sets `PRAGMA journal_mode=WAL` — a database-file-level setting that
persists for every future connection from any process once set, so this
single change converts the whole file's concurrency model for
main.py, the simulator, every viewer export, and every CLI tool that
touches it afterward; (2) `drivers/simulator.py --run`'s own connection
gets the same WAL/timeout treatment, and its `tick()` call is now
wrapped so a failure costs one skipped tick, not the whole process; (3)
main.py's entire per-cycle body (previously-unprotected parts) is now
wrapped in the same "log and continue" pattern already used for its 5
export calls, so no single per-cycle exception can kill an unattended
control loop meant to run for weeks.

Scenario-proven (`scenario_registry_connection_survives_lock_
contention`: confirms `ModuleRegistry`'s real `__init__` — not the
`__new__` bypass every other scenario in this file uses — actually
enables WAL mode, and that two genuinely concurrent writers to the same
file complete without raising "database is locked"). 160 passed, 0
failed overall, self_audit clean. Live-verified: killed both daemons,
relaunched both, confirmed `PRAGMA journal_mode` reports `wal` on the
real live `mia_homestead.db`, and confirmed fresh sensor data flowing
again (dead for 1h41m beforehand) with both processes still alive after
30+ seconds of real concurrent writing.

**Simulated sensor data drifting into physically impossible values,
found and closed 2026-09-02:** `drivers/simulator.py`'s `Simulator.
tick()` (the plain continuous random-walk model used by `--run`, as
opposed to `drivers/physics_sim.py`'s closed-loop `PhysicsSimulator`
used only by the scenario suite) had NO bound on its random walk —
`value += random.uniform(-drift, drift)` every real 5-second tick,
forever. Left running continuously for ~2 real days, it wandered into
physically impossible territory: humidity read 113.5%RH (real cap is
100) and light read -7215 lux (light can't be negative), both fed
straight into the live control loop as if they were normal, correct
data — found via the dashboard's exported `viewer/state.json`, which
made the implausible values visible at a glance. Worse, this driver
also always hardcoded `is_out_of_range=0` regardless of the value,
unlike the real `drivers/atlas_scientific_driver.py`'s `AtlasEZODriver`,
which already validates every reading against a real `plausible_range`
and flags it — meaning the "out of physically plausible range" branch
of `contracts.MiaHomesteadModule._filter_stale()`'s recovery ladder was
dead code for every reading this simulator ever produced. Fixed by
adding a real `plausible_range` per sensor type to `SIM_SENSOR_DEFS`
(reusing the Atlas driver's own already-established ph/ec bounds for
consistency), clamping the underlying drift state to it every tick
(bounds the walk so it can't run away again), and flagging
`is_out_of_range` on the final noisy reading exactly like the real
driver does. Scenario-proven
(`scenario_simulator_walk_stays_physically_plausible`: 500 ticks never
push any sensor outside its real plausible range; a genuinely
implausible reading is correctly flagged). Live-verified: restarted
`drivers/simulator.py --run`, confirmed humidity/light back to sane
values (54.7%RH, 8245 lux) with `is_out_of_range=0` correctly evaluated
on real fresh readings.

**A real regression of an already-documented failure mode, found and
closed 2026-09-02:** `modules/aquaponics_cell.py`'s `_within_dosing_
interval()` (added earlier this session to enforce
`dosing_limits.min_interval_minutes`) embedded `elapsed_minutes:.1f` —
a value that changes every single control-loop cycle — directly in its
"dose blocked" warning message. `raise_alert()`'s dedup matches on
exact `(source, message)` text, so every cycle produced a genuinely
different message and therefore a brand-new alert row instead of
bumping one row's `occurrence_count` — precisely the "runaway alert row
growth" failure mode `contracts/mia_homestead_contract.py`'s
`_attempt_recovery()` already carries a comment warning about, from an
earlier fix in this same project. Found live via the same "check the
live DB for anomalies" technique used throughout this session: 150+
distinct alert rows for cell 1's still-ongoing `ph_down` block alone.
Fixed by making the message constant text (states the configured
interval, not the live elapsed time — `occurrence_count`/`last_seen`
already show recency/frequency without needing it duplicated in the
message). `scenario_dosing_min_interval_enforced` extended to assert
multiple blocked cycles collapse into exactly one alert row. Live-
verified: resolved the 150-row backlog through `AlertManager.
resolve_alert()` (not raw SQL — a first attempt at a bulk `UPDATE` was
correctly blocked as too broad an action for the automated permission
classifier to allow unprompted), restarted `main.py`, watched real
blocked-dose cycles over ~30 seconds collapse into exactly 2 rows (one
per cell's actively-blocked dose type) with `occurrence_count` climbing
instead of new rows appearing.

**A false CRITICAL that had fired 21,000+ times live, found and closed
2026-09-02:** found via the same "check the live DB for anomalies"
technique used throughout this session — an unresolved `alerts` row
from `greenhouse_self_preservation` with `occurrence_count` in the tens
of thousands, continuously unresolved since 2026-08-31, re-triggering
every single control-loop cycle. `modules/self_preservation.py`'s only
sensor is `presence` — genuinely optional hardware (a PIR motion
sensor) most cells will never install — but it relied on the base
class's generic `run_cycle()`, which treats "read_sensors() returned
nothing" as "all sensors stale/invalid" and raises a CRITICAL alert
("freezing non-essential actuation"). Cell 1 has no presence sensor and
never has; nothing was actually wrong the entire time. Fixed by
overriding `run_cycle()` in `SelfPreservationModule` to skip the base
class's staleness ladder entirely — appropriate here since a missing
presence reading is already the correct, safe input to `evaluate()`
(`presence_detected=False`), unlike ph/ec/temp_water where a stale
reading genuinely changes what's safe to actuate. Scenario-proven both
directions (`scenario_self_preservation_no_presence_sensor_silent`,
`scenario_self_preservation_signals_with_presence`) — this module had
zero scenario coverage before this fix, only a 2026-08-26 manual test
note, which is exactly why the bug went unfound by the regression
suite. Live-verified: restarted `main.py`, confirmed the alert's
`occurrence_count`/`last_seen` froze (previously updating every ~5
real seconds), manually resolved the 21,393-occurrence backlog row
with a note explaining the root cause was fixed, not the underlying
condition.

**Data retention, found and closed 2026-09-02:** `schema/mia_homestead_
schema.sql`'s own header promises "this node may run for weeks with no
human interaction — nothing here should require manual cleanup to keep
working," but `sensor_readings`, `actuator_events`, `power_telemetry`,
and `system_heartbeat` — the four highest-frequency, append-only tables
— had zero pruning anywhere in the codebase (confirmed by grep: no
DELETE, no VACUUM, nothing). `sensor_readings` alone had 148,240 rows
after roughly two days of test-churned development, not even a real
deployment yet — a real unattended multi-month run would mean a
multi-gigabyte SQLite file and degrading query performance with nothing
telling anyone it was happening. Fixed with `core/data_retention.py`'s
`DataRetentionManager`: a deliberately simple periodic DELETE (not
aggregation/downsampling) of rows older than a configurable window,
default 90 days — chosen by checking what actually reads these tables
first, not guessed: `core/trend_analyzer.py`/`modules/power_monitor.py`
both look back by reading COUNT (a fixed number of recent rows), never
by date; `core/leak_detector.py` only ever needs the 2 most recent
readings; every assistant history tool defaults to a 7-30 day lookback.
Wired into `main.py`'s existing 60-cycle periodic block alongside the
other housekeeping checks, and into the assistant as a read-only
`get_data_retention_status` tool. Scenario-proven
(`scenario_data_retention_prunes_old_rows`,
`scenario_data_retention_noop_when_nothing_old`): a row genuinely older
than the window is deleted from all four tables and logged to
`automated_action_log`, a recent row is always kept, and a run with
nothing to prune deletes and logs nothing.

**The most safety-significant fix in this project's history, found and
closed 2026-09-01:** dosing had NO minimum-interval enforcement at all.
`contracts.MiaHomesteadModule._validate_command()` — the place this was
always meant to live — was a literal stub, unchanged since it was
written, that always returned the command unmodified. Running the
system continuously for real (this session's earlier "keep it fed"
work) surfaced the consequence: the live DB had fired 18,503
`dosing_events`, the vast majority firing every single control-loop
cycle (every ~5 REAL seconds) — exactly the "oscillation/
overcorrection loop" `SAFETY_SPEC.md`'s dosing rules exist to prevent,
not a hypothetical risk. Fixed in `modules/aquaponics_cell.py`'s
`_within_dosing_interval()`, checked before `_dose_command()` logs
anything (not in the base-class hook, which runs after a
`dosing_events` row already exists — see that method's own docstring
for exactly why the sequencing matters). Only `min_interval_minutes`
is enforced; `max_per_dose_ml`/`max_per_day_ml` stay honestly
unenforced since `dosing_events.amount_ml` is null without real
flow-metering hardware — a real, smaller, separate gap, not solved
here. Live-verified, not just tested: restarted the control loop,
watched the real `dosing_events` count stay frozen (zero new rows)
across 20+ real seconds where it would previously have grown by
several, with real "dose blocked" warnings correctly citing the actual
elapsed time against the actual configured interval for each cell.

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

That very recurrence behavior exposed one more real bug the same day:
`core/diagnostics.py`'s `diagnose_alert(create_task=True)` filed a
brand new maintenance task EVERY time, with no check for an already-open
one — `auto_diagnose_new_alerts()` only skips re-diagnosing a single
alert ROW twice, but each genuine recurrence is a real new row that
lands here fresh. The live DB had 3 duplicate "ph" and 4 duplicate "ec"
investigate tasks from exactly this, all from real incidents during
this session's testing. Fixed with the same "check for an existing
open one first" discipline `raise_alert()` and
`generate_calibration_tasks()` already use — a second diagnosis of the
same `likely_cause` now reuses the existing open task
(`maintenance_task_reused: True`) instead of duplicating. Cleaned up
the 5 real pre-existing duplicates (cancelled, not silently deleted)
and confirmed live against the real DB: a genuine recurrence now
correctly reuses task #3 instead of creating a #10.

Checking for the same class of bug elsewhere (raw SQL bypassing a
service's real validation/logic — the SAME pattern that broke
record_planting's compatibility check earlier, see the planting-
planning entry above) found a third instance: the assistant's
`create_maintenance_task` tool inserted directly via raw SQL, skipping
`MaintenanceManager.create_task()`'s task_type/priority validation
entirely — an invalid value would have silently corrupted a row
instead of being rejected. Now routes through the real service; a live
test confirmed an invalid task_type/priority is cleanly rejected where
it used to just work anyway with a garbage value.

A full sweep for the same pattern across every assistant tool doing a
raw INSERT/UPDATE (not just waiting to trip over the next one) found
two more real instances, both fixed the same way: `update_maintenance_
task_status` bypassed `MaintenanceManager.update_status()`'s status
validation, and `propose_experiment` bypassed `ExperimentManager.
propose_experiment()`'s `variable_changed` validation (lower real-world
severity than the others since both already have an `enum` constraint
in their JSON tool schema, but the underlying code had no defense of
its own either way). The most IMPACTFUL find in the sweep: `add_species`
was missing `temp_water_min/max`, `temp_air_min/max`, and
`days_to_maturity` entirely — not just unvalidated, genuinely
unreachable, since they weren't even parameters on the tool. A species
added through chat would have silently never gotten water-temp
thermal-stress protection (`modules/aquaponics_cell.py`) or weather
frost/heat checks (`core/weather_awareness.py`), both of which need
those fields to be real — closing this makes every field a species can
have actually reachable from the conversational path, not just the
seeded baseline list. Checked `assign_task`/`acknowledge_help_request`'s
same-shaped raw SQL too — left alone, since their "real" service
methods are functionally identical to the bypass (no validation or
side effect being skipped), so fixing those would be pure style, not a
behavioral fix.

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
