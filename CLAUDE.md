# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

M.I.A. (Multifunctional Intelligent Assistant) is an offline-first, modular
desktop shell for Linux (target: kiosk mode on a Raspberry Pi 5), built with
Python + PySide6. It is currently v0.1/v0.2 — a core framework and system
layer with mostly stub feature modules; no AI/assistant logic exists yet.
See `docs/VISION.md` for the long-term four-project mission and
`docs/ROADMAP.md` for the actual near-term phase plan — read `ROADMAP.md`
before assuming a feature is in scope for "now."

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

- No AI/assistant logic yet — out of scope until roadmap phase v0.5.
- No plugin sandboxing for modules — acceptable for a single-user offline
  tool; would need revisiting before loading untrusted third-party
  modules.
- No async/threading anywhere in core — add only when a concrete
  long-running task (e.g. a network scan) needs it, scoped to that module.
- Config is a flat JSON blob, not schema-validated — fine while the
  config surface is small; prefer a `modules.<module_id>.*` namespace
  convention over reaching for a validation library.

## Deployment notes

Kiosk deployment (Raspberry Pi 5) uses a systemd **user** service (not
system-level — GUI apps need the logged-in graphical session), installed
via `deploy/install_kiosk.sh` from the `deploy/mia.service` template.
Don't hand-edit the `__MIA_*__` placeholders in that template — edit the
install script instead so re-running it stays reproducible. See
`docs/HARDWARE.md` for the target hardware assumptions (Pi 5, AI HAT+ 2,
storage split) this software is being built against.
