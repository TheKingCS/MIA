# MIA — Multifunctional Intelligent Assistant

MIA is an offline-first, modular field operating environment built
on Linux. Rather than a single-purpose application, MIA is designed
to feel like a custom desktop environment: a unified interface for
engineering, survival, robotics, networking, local AI, and personal
knowledge management.

**Status: v0.1 — Core Framework.** This release does *not* include AI.
It establishes the application shell, first-run setup, and the module
architecture that every future feature will plug into.

## Core principles

- Offline first
- Modular architecture
- Cross-platform during development (Windows + Ubuntu/WSL), Linux is the primary deployment target
- Python as the primary language
- Clean, documented, scalable code over clever shortcuts
- Every feature is a module whenever practical

## What's in v0.1

- Application startup sequence with an animated splash screen (pulsing
  core graphic, "INITIALIZING CORE SYSTEMS..." status text)
- First-time setup wizard (name, date, time confirmation)
- Persistent configuration (`config/config.json`, seeded from `config/default_config.json`)
- Main menu with placeholder module buttons: Assistant, Files, Knowledge,
  Maps, Music, Notes, Diagnostics, Modules, Settings
- A reserved panel for the future animated character (`gui/character_panel.py`)
- Automatic module discovery — drop a folder in `modules/` and it appears
  on the menu, no registry file to edit
- A standalone module test harness for fast module development

## Project layout

```
assets/     Icons, images, fonts (placeholders for now)
config/     default_config.json (versioned) + config.json (user, gitignored)
core/       The kernel: config, logging, event bus, module discovery, boot sequencing
data/       User/application data (gitignored)
docs/       Architecture notes and the "how to add a module" guide
gui/        Presentation layer — splash, wizard, main window, widgets
logs/       Rotating log files (gitignored)
modules/    One folder per feature module
tests/      Unit tests + tests/run_module.py (single-module dev harness)
main.py     Two-line entry point
```

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the reasoning
behind these decisions, and [`docs/ADDING_MODULES.md`](docs/ADDING_MODULES.md)
for how to add a new module.

## Getting started (Ubuntu / WSL)

```bash
git clone <your-fork-url> mia
cd mia
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

On first run, MIA will walk you through the setup wizard (name, date,
time) before showing the main menu.

## Developing a module

```bash
python tests/run_module.py --list       # see all discovered modules
python tests/run_module.py notes        # open just the Notes module, standalone
```

Full guide: [`docs/ADDING_MODULES.md`](docs/ADDING_MODULES.md).

## Running the test suite

```bash
pytest
```

## Roadmap (not yet built — noted here so scope is explicit)

- Real functionality inside the stub modules (Notes, Files, Diagnostics
  are natural first candidates)
- Local AI / Assistant module
- Animated character implementation behind `gui/character_panel.py`
- Robotics and networking modules
- Settings module UI for editing config live

## License

Not yet decided — add your preferred open-source license here before
your first public release.
