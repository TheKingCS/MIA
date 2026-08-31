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
python3 scenarios/scenarios.py        # must print 38 passed, 0 failed
python3 core/self_audit.py            # must say "All checks passed"
```

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
config/          modules.yaml, layout.json, device roles, plumbing.yaml
                 (these YAML files ARE the source of truth for physical
                 wiring/plumbing - edit them, not code, for physical changes)
schema/          single schema.sql, additive - never destructive migrations
scenarios/       safety regression suite - run before any control-logic change
drivers/         simulator.py (fake data, incl. simulated power_telemetry),
                 physics_sim.py (closed-loop),
                 atlas_scientific_driver.py (real I2C, untested on hardware)
viewer/          3D digital twin (live "go here" fault locator) and the
                 ops dashboard (dashboard.html) — two separate pages,
                 two separate export scripts/state files, both
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
AND conversational tool coverage.

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

## Git conventions used so far

Commit messages describe what was built AND what was proven live
(specific numbers/results, not just "added feature X"). Look at `git
log` for the established tone before writing new commit messages.
