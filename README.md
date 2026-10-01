# MIA — Multifunctional Intelligent Assistant

MIA is an offline-first, modular field operating environment built
on Linux. Rather than a single-purpose application, MIA is designed
to feel like a custom desktop environment: a unified interface for
engineering, survival, robotics, networking, local AI, and personal
knowledge management.

**Status: actively developed.** The core framework has grown into a
working system: 33 implemented modules, a local-first AI assistant
(Ollama/llama3.2, ~175 tools), hold-to-talk voice, a phone web server
with an Android companion app, and a headless voice-first runtime for
Pi-class hardware.

## Core principles

- Offline first
- Local-first AI — your data stays on your machines
- Modular architecture
- Cross-platform during development (Windows + Ubuntu/WSL), Linux is the primary deployment target
- Python as the primary language
- Clean, documented, scalable code over clever shortcuts
- Every feature is a module whenever practical

## What's implemented

- **33 feature modules, zero placeholders** — greenhouse, garage,
  kitchen, workout, real estate, maintenance, missions, skills
  ("My Hero's Path" skill tree), budget with Plaid bank sync,
  notes/journal, knowledge (offline ZIM packs), maps (offline tiles),
  music, navigation, and more
- **Local-first assistant** — Ollama/llama3.2 with ~175 tools and
  hold-to-talk voice, grounded in live system state. Unprompted
  communication is gated (max 5/day); the assistant drafts email but
  the human presses Send
- **Phone access** — web server (default port 8765) plus an Android
  companion app (CI-built APK)
- **Headless runtime** — `core_main.py`, a voice-first runtime for
  Pi-class deployment that never touches the GUI layer
- **Strict layering** — `core` → `modules` → `gui` with an event bus
  and explicit `AppContext` (no global singletons); broken modules are
  logged and skipped at boot, never crash it
- Application startup sequence with animated splash screen and
  first-run setup wizard (name, date, time confirmation)
- Persistent configuration (`config/config.json`, seeded from
  `config/default_config.json`)
- Automatic module discovery — drop a folder in `modules/` and it
  appears on the menu, no registry file to edit
- A standalone module test harness for fast module development
  (`tests/run_module.py`)
- A functional character panel (`gui/character_panel.py`; final
  animated character artwork still to come)
- Thousands of automated checks (`pytest`)

## Project layout

```
android/      Kotlin/Gradle companion app (CI-built APK)
assets/       Icons, images, fonts
config/       default_config.json (versioned) + config.json (user, gitignored)
core/         The kernel: config, logging, event bus, module discovery, boot sequencing
core_main.py  Headless voice-first runtime for Pi-class hardware
data/         User/application data (gitignored)
docs/         Vision, architecture, roadmap, and the "how to add a module" guide
gui/          Presentation layer — splash, wizard, main window, widgets
logs/         Rotating log files (gitignored)
modules/      One folder per feature module (33 implemented)
server/       Phone web app (default port 8765)
tests/        Unit tests + tests/run_module.py (single-module dev harness)
main.py       Desktop entry point (MIAApplication)
```

See [`docs/VISION.md`](docs/VISION.md) for the vision,
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the reasoning behind
these decisions, [`docs/ADDING_MODULES.md`](docs/ADDING_MODULES.md) for
how to add a new module, and
[`docs/ASSISTANT_CAPABILITIES.md`](docs/ASSISTANT_CAPABILITIES.md) for
what the local assistant can do.

## Getting started

**Setting MIA up on a new computer?** Follow
[`docs/SETUP_GUIDE.md`](docs/SETUP_GUIDE.md): install, the local AI and
voice, the Private Journal, bank sync, and phone access, step by step.

### Install (the easy way)

Download MIA (GitHub → Code → Download ZIP, unzip it; or `git clone`), then:

- **Linux / Raspberry Pi:** open a terminal in the MIA folder and run
  `bash install.sh` (add `--kiosk` on a Pi that should boot straight into
  MIA).
- **Windows:** double-click **install.bat**.

The installer asks before each big step and is safe to run again: system
tools, MIA's brain (Ollama and its model), MIA's packages, the voices, a
"MIA" shortcut, and a setup check that lists anything left to do.

### Quick start for developers (Ubuntu / WSL)

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

## Roadmap

See [`docs/ROADMAP.md`](docs/ROADMAP.md) for the full plan. Open items
include final animated character artwork for `gui/character_panel.py`
(the panel itself is functional) and the Meta glasses interface track —
glanceable cards and voice on current Display hardware, building toward
AR.

## License

Not yet decided — add your preferred open-source license here before
your first public release.
