# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

MIA (Multifunctional Intelligent Assistant) is an offline-first, modular
personal assistant, built with Python + PySide6. Where it runs, in order
(DEC-0015, 2026-10-05): the owner's new computer (the engine and the
desktop), their phone, Meta Display glasses (soon), and eventually
their own Raspberry Pi devices. The Pi/kiosk material below is that
later step, not the current target. It has a core framework, many feature modules, and a
local-model Assistant with ~175 tools (`docs/ASSISTANT_CAPABILITIES.md`);
`docs/COGNITIVE_EXTENSION_PROPOSAL.md` is the current direction for it.
See `docs/VISION.md` for the long-term four-project mission and
`docs/ROADMAP.md` for the actual near-term phase plan — read `ROADMAP.md`
before assuming a feature is in scope for "now."

## Start of every session

Read `docs/NEXT_SESSION.md` first. It's the running to-do list between
sessions (the owner's pending hands-on steps, the build queue, parked
ideas, loose ends); cloud sessions keep no memory of earlier chats.
Update it before ending a session.

MIA is built by a team (2026-10-05): Zac (owner), ChatGPT (vision),
Muse (design) and Claude (engine), sharing memory through files in this
repo (`docs/COLLABORATION.md`). Also read `docs/CURRENT_STATE.md`, and
check `docs/QUESTIONS.md` and `docs/HANDOFFS/` for anything addressed to
Claude. At the end of a session, rewrite `docs/CURRENT_STATE.md` and log
new decisions in `docs/DECISIONS.md`. Only Zac approves a decision.

## Commands

```bash
# Setup
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Run the full app
python main.py

# Run the test suite
pytest
pytest tests/test_module_manager.py            # single file
pytest tests/test_module_manager.py::test_name # single test

# Develop/test a single module in isolation (no splash/wizard/menu)
python tests/run_module.py --list
python tests/run_module.py <module_id>          # e.g. notes
```

There is no lint/format command configured in this repo yet.

## Architecture

### Strict one-directional layering

```
core/     <- knows about nothing else in the project
modules/  <- knows about core/ only (via ModuleBase + AppContext)
gui/      <- knows about core/ only, and talks to modules/ only through
             ModuleBase.get_widget()
```

`core/` never imports `gui/` or `modules/`. Modules never import another
module directly — cross-module reaction goes through the event bus
(`self.context.events.subscribe(...)` / `.publish(...)`, see
`core/event_bus.py`). GUI code never reaches into a module's internals
beyond the `ModuleBase` contract. This is deliberate and enforced by
convention, not tooling — preserve it when adding code. Full reasoning in
`docs/ARCHITECTURE.md`.

### AppContext — the one shared object

`core/app_context.py` is a dataclass bundling shared services
(`config`, `events`, `profiles`, `notifications`, `search`) passed
explicitly into every `ModuleBase` and GUI class that needs it. No global
singletons. When adding a new core-level service, add it as a field on
`AppContext` and construct it in `core/application.py` — don't reach for
an ad-hoc import instead.

### Boot sequencing lives in one place

`core/application.py`'s `MIAApplication` owns the entire startup order:
create Qt app → splash → init core services → discover modules → decide
first-run vs. normal boot (setup wizard / profile selector / lock screen /
main window) → show it. `main.py` is intentionally a ~2-line entry point
and should never gain startup logic or PySide6 imports directly — this is
a hard convention (`main.py` is the first file any contributor opens).
`MIAApplication._display()` is the single place kiosk-mode
(fullscreen-vs-window) behavior lives; every top-level screen transition
must route through it or fullscreen persistence silently breaks (see
`docs/KNOWN_ISSUES.md` for the historical bug this fixed).

### Automatic module discovery

`core/module_manager.py` scans `modules/` via `pkgutil`/`importlib` for
subpackages containing a `module.py` with exactly one `ModuleBase`
subclass, and instantiates each one — no central registry file to edit.
Key behavioral rules baked into `ModuleManager`:

- A broken module (import error, bad `__init__`, missing `get_widget`) is
  logged and skipped, never crashes the app.
- `__init__` runs for *every* discovered module at *every* boot, even
  disabled ones and ones the user never opens — it must be cheap
  (attribute assignment only). Expensive setup belongs in `on_load()`
  (called lazily on first activation) or inside `get_widget()` itself.
- `module_browser` (the Modules screen) can never be disabled — enforced
  in code, since disabling it would remove the only way back in.
- `rescan()` only detects newly added module folders while the app is
  running; it does not hot-reload code in an already-loaded module and
  does not detect removed folders (both require a restart).
- Installing a module from the "Add Module" UI goes through
  `core/module_validator.py`, which enforces every rule in
  `docs/MODULE_SPEC.md` (folder structure, exactly-one-`ModuleBase`-class,
  `module_id` format/uniqueness, instantiability) before anything is
  copied into `modules/`. There is no code sandboxing — installing a
  module runs its code with full app privileges.

### Writing a module

See `docs/ADDING_MODULES.md` for the full walkthrough and
`docs/MODULE_SPEC.md` for the precise, checklist-form contract. Summary:
one `ModuleBase` subclass per `modules/<name>/module.py`, unique
snake_case `module_id`, implement `get_widget()`. Use
`self.context.config.get("modules.<module_id>.*")` for settings (never a
separate config file), log via `core.logger.get_logger(__name__)` (never
`print()`), and optionally register a search provider in `on_load()` via
`self.context.search.register_provider(...)` to make module content
reachable from Ctrl+K.

### Config: defaults + user overrides

`config/default_config.json` is versioned and never overwritten.
`config/config.json` is the user's actual config (gitignored), seeded
from and merged with the defaults on load
(`ConfigManager._merge_defaults`) — this lets upgrades add new config
keys without wiping user settings, and lets a user factory-reset by
deleting `config/config.json`.

### Built for anyone; each person's data is their own

MIA is perfected for personal use but designed for any person or
household, not one owner (2026-10-01 decision; the youth/school idea is
parked in `docs/future/MIA_YOUTH_INITIATIVE.md`). People sign in with an
email (`core/profile_manager.py`); nothing is shared unless they join a
household with a member's approval (`core/household_manager.py`).
Personal stores live in each profile's folder, `data/profiles/<id>/`
(`core/personal_data.py`, `PERSONAL_STORES`): conversations, memories,
private journal, notes, reasons, MIA's message log, online reminders,
workouts, Classroom, notifications. Household stores
(`HOUSEHOLD_STORES`: maintenance, kitchen, builds, rentals, inventory,
inbox, calendar, budget...) are shared within a household; the device's
first household keeps `data/`, others use `data/households/<id>/`. A new
store takes an optional `data_dir` in its constructor and goes in one of
those two lists (or stays device-level, like the model and voice).
Settings that belong to a person go through `core/person_settings.py`.
Tools always use the `context` they're given, never a global, because the
phone runs a turn on the signed-in person's own view (`view_for()`).
Never hardcode the owner's names, places or things in code or prompts.
A child account (`core/child_accounts.py`) sees only `CHILD_APPS` and is
never offered `CHILD_BLOCKED_DOMAINS` tools; give a new module or tool
domain a place in one of those lists when it's clearly for (or not for)
children.

### Other core services

- **Event bus** (`core/event_bus.py`) — synchronous pub/sub, deliberately
  not thread-safe or async (v0.1/v0.2 is single-threaded). Don't add
  threading/async here speculatively; introduce a scoped worker-thread
  pattern in the specific module that needs it when that need actually
  arrives.
- **Profiles** (`core/profile_manager.py`) — multi-user support; drives
  whether boot shows the setup wizard, profile selector, or lock screen.
- **Notifications** (`core/notification_manager.py`) — any module can
  raise a toast/persisted notification.
- **Communication gate** (`core/communication_gate.py`) — every
  *unprompted* message (daily checks, insights, suggestions, missions MIA
  assigns) goes through `context.communication.offer(Candidate(...))`,
  never straight to `notifications.notify()`: it merges, rate-limits
  (owner's limit: 5/day), drops repeats and logs every decision. Replies
  to something the user just did, alarms and low battery stay direct.
- **Email** (`core/email_drafts.py`, `core/mail_send.py`) — the Assistant
  only drafts; an email is sent only when a person presses Send (desktop
  dialog or phone). Never add a tool that sends.
- **Undo** (`core/undo_log.py`) — Assistant changes are undoable because
  stores write through `core.atomic_write.atomic_write_text`; keep new
  stores on it (and give them `_load()` or a `data_dir` constructor) so
  "undo that" can restore and reload them.
- **Engine read model** (2026-10-05, `docs/ENGINE_PHASE1_PLAN.md`) —
  stores are the current state; `core/life_events.py` is the history
  beside them (a store calls `life_events.record(self, ...)` after a
  meaningful change; never rewrite it); `core/links.py` holds how things
  relate (by `kind:id` ref, stated or derived, never a copy of a record);
  `assemble_life_state_v2()` in `core/context_assembler.py` is the
  derived picture, served as `/api/state` and
  `python -m tools.export_state`, shaped by
  `docs/schema/life_state.schema.json` (update the schema with the
  code; `tests/test_state_export.py` checks it). Every section carries a
  REAL/DERIVED/SIMULATED/STATIC/PLANNED status. New proposals go through
  the plan's section 9 checklist.
- **Phase 2 front end** (2026-10-05, DEC-0012/0013) — `web/` is MIA's
  one web front end (Muse's; `web/README.md`), served at `/web/` by
  `server/app.py` and shown on the desktop by `modules/web_home`. It
  only talks to the engine through `web/mia.js`: `/api/state` to read,
  `/api/actions` to change things (`core/actions.py`: Propose → Approve
  → Execute → Record → Undo; add new action kinds there, never logic
  in `web/`), `/api/live` to know when to re-read (`core/live.py`,
  bumped by every `atomic_write_text`). Due items carry their suggested
  `action`. An approved action runs as the person who approved it
  (`core.profile_manager.crediting`), so XP and rewards earned from the
  phone are theirs, not whoever is signed in on the PC.
  DEC-0017 (2026-10-06): the web becomes *all* of MIA, function first,
  in Zac's concept look. Claude builds each module's working screen on
  the shared frame (`web/shell.js`: sidebar from `/api/shell`, Talk,
  `MIAShell.act`), with the screen's data assembled in core (Home:
  `core/web_surfaces.py`); Muse owns the look. `docs/WEB_PARITY.md`
  tracks every Qt screen until its web version does everything it does.
  DEC-0018 (2026-10-06): the target look is the mobile concept set
  (`docs/design/MOBILE_CONCEPT.md`), built by Claude in `web/concept.css`;
  photos live in `web/img/` (`docs/design/IMAGE_REQUESTS.md`), never
  anything personal.
- **Search** (`core/search_manager.py`) — providers register a callback;
  `MainWindow._on_search_result_activated` dispatches by `action_type`
  (`"open_module"`, `"switch_profile"`, ...) — new action types need a
  branch there.

### Why PySide6

LGPL-licensed (unlike PyQt6's GPL/commercial split), supports custom QSS
styling for the "OS shell" look, has real animation primitives for the
planned character panel, and is cross-platform for Windows dev /
Ubuntu-WSL deployment.

## Known intentional simplifications (don't "fix" these without cause)

- Assistant runs on a small local model (llama3.2:3b via Ollama); facts
  are assembled in code and the model only phrases them. Crisis handling
  (`core/safety_floor.py`) never depends on the model, and its numbers
  follow the person's country (`core/region.py`). Format money with
  `core.region.money()`, never a literal "$".
- No plugin sandboxing for modules — acceptable for a single-user offline
  tool; would need revisiting before loading untrusted third-party
  modules.
- No async/threading anywhere in core — add only when a concrete
  long-running task (e.g. a network scan) needs it, scoped to that module.
- Config is a flat JSON blob, not schema-validated — fine while the
  config surface is small; prefer a `modules.<module_id>.*` namespace
  convention over reaching for a validation library.

## Deployment notes

*Later step (DEC-0015): the Pi is priority 4, after the new computer,
the phone and the glasses.* Kiosk deployment (Raspberry Pi 5) uses a systemd **user** service (not
system-level — GUI apps need the logged-in graphical session), installed
via `deploy/install_kiosk.sh` from the `deploy/mia.service` template.
Don't hand-edit the `__MIA_*__` placeholders in that template — edit the
install script instead so re-running it stays reproducible. See
`docs/HARDWARE.md` for the target hardware assumptions (Pi 5, AI HAT+ 2,
storage split) this software is being built against.

The repo has a private GitHub remote (`github.com/TheKingCS/MIA`). This
checkout's `.git/hooks/post-commit` auto-pushes every commit on the
current branch to `origin` — since git hooks aren't version-controlled,
a fresh clone won't have this behavior until the hook is recreated.
