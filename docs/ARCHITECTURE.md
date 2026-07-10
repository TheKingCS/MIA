# M.I.A. Architecture

This document explains the *why* behind the v0.1 foundation, so future
contributors (including future-you) don't have to reverse-engineer the
reasoning from the code.

## Guiding constraint

M.I.A. is meant to be developed on and off for years, by potentially
more than one person, often offline, and it needs to keep growing new
modules (robotics, networking, local AI, etc.) without the core ever
needing a rewrite. Every decision below optimizes for that, sometimes
at the cost of a little extra structure up front.

## Layering

```
core/     <- knows about nothing else in the project
modules/  <- knows about core/ only (via ModuleBase + AppContext)
gui/      <- knows about core/ only, and talks to modules/ only through
             ModuleBase.get_widget()
```

This is a strict one-directional dependency graph. `core/` never imports
`gui/` or `modules/`. Modules never import GUI toolkit internals into
their logic (only inside their own `get_widget()`/widget-building code,
which is itself presentation). GUI code never reaches into a module's
internal attributes beyond the `ModuleBase` contract.

**Why it matters:** without this rule, a project like this tends to
accrete circular imports within a year or two — the Notes module starts
importing something from Maps, the GUI starts special-casing individual
modules, and eventually nothing can be tested or replaced in isolation.
Enforcing the layering now, while there are only 9 modules and all of
them are stubs, costs almost nothing. Retrofitting it after 30 modules
exist would be a painful rewrite.

## AppContext — the one shared object

`core/app_context.py` defines a small dataclass bundling the services
every module and GUI screen might need: `config` and `events` for now.
It's passed explicitly into every `ModuleBase` and every GUI class that
needs it — nothing reaches for a global singleton.

**Why:** explicit dependencies keep the system testable (you can build a
module with a fake `AppContext` in a unit test, no GUI event loop
required) and keep it obvious, from a class's constructor signature
alone, what it depends on.

When a new core-level service is needed (e.g. a future `hardware`
service for robotics I/O, or a `local_ai` service once the Assistant
module is built), add it as a field on `AppContext` and construct it in
`core/application.py`. Resist the temptation to reach for a global
`import core.state` instead.

## Automatic module discovery

`core/module_manager.py` scans `modules/` for subpackages containing a
`module.py` with a `ModuleBase` subclass, and instantiates them
automatically. There's no central list of "installed modules" to edit.

**Why:** the project brief explicitly asks for it to be "convenient to
add and test new modules." A hand-maintained registry file is exactly
the kind of friction (one more file to remember to touch, one more
place for merge conflicts) that discourages people from adding modules
over a multi-year project. See `docs/ADDING_MODULES.md` for the
resulting (very short) process to add one.

The trade-off is a bit more "magic" via `importlib`/`pkgutil`. We accept
that consciously — see the docstring in `module_manager.py` for the
escape hatch if this ever becomes a real problem.

## Event bus

`core/event_bus.py` is a minimal synchronous pub/sub system. It exists
so modules can react to things happening elsewhere in the system without
importing each other directly (which would violate the layering rule
above). It is deliberately *not* thread-safe or async — v0.1 is a
single-threaded desktop GUI app, and adding that complexity now would be
premature optimization. Revisit only when a real background-thread use
case (e.g. a robotics/networking daemon) appears.

## Why PySide6 for the GUI

- **License:** LGPL, safe for an open-source project without the
  GPL/commercial split that PyQt6 has.
- **Custom styling (QSS):** needed to make M.I.A. feel like an "OS shell"
  rather than a stock desktop app.
- **Widget + animation system:** the eventual animated character panel
  needs real animation primitives (QMovie, QPropertyAnimation, or a
  QML view) that Tkinter doesn't provide well.
- **Cross-platform:** works the same in Windows dev and Ubuntu/WSL
  deployment.

## Startup sequencing lives in one place

`core/application.py`'s `MIAApplication` class owns the entire boot
order: create Qt app -> show splash -> init config/logging -> discover
modules -> decide first-run vs. normal boot -> show the right window.
`main.py` never contains this logic — it only constructs and runs
`MIAApplication`. This keeps `main.py` a 2-line file forever, which
matters because it's the first file any new contributor opens.

## Config: defaults + user overrides

`config/default_config.json` is checked into version control and never
overwritten. `config/config.json` is the user's actual, gitignored
config, seeded from and merged with the defaults on load (see
`ConfigManager._merge_defaults`). This means:

- Upgrading M.I.A. can introduce new config keys without wiping a user's
  existing settings.
- A user can delete `config/config.json` to factory-reset.
- Nothing sensitive/personal ever accidentally gets committed to git.

## Known simplifications in v0.1 (intentional, not oversights)

- No AI/assistant logic — explicitly out of scope per the project brief.
- No plugin sandboxing — all modules run in-process. Fine for a
  single-user offline tool; would need revisiting if M.I.A. ever loads
  third-party modules it doesn't fully trust.
- No async/threading — fine until a module needs a long-running
  background task (e.g. a network scan). When that happens, introduce
  a small worker-thread pattern in that module, not a system-wide
  rewrite.
- Config is a flat JSON blob, not a schema-validated structure. Fine
  while the config surface is small; if it grows unwieldy, consider a
  `modules.<module_id>.*` namespace convention before reaching for a
  validation library.
