# MIA Homestead — Desktop Setup

Everything below assumes simulation-only work — no real hardware needed.
This is the whole point of the simulation-first approach: full
development on the desktop, hardware only comes in once specs are
validated.

## 1. Get the code onto the desktop

Unzip the project wherever you keep MIA projects, then from inside the
`mia-homestead/` folder:

```bash
git init
git add .
git commit -m "Initial import — full simulation-validated backbone"
```

(If you'd rather start Claude Code directly in this folder, it can run
the commands below for you — just point it at this directory.)

## 2. Environment

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Your desktop's Ryzen/RX 7900 XTX specs are irrelevant to this project
right now — everything here is CPU-bound Python + SQLite, no GPU
workload. That matters once you're doing local LLM inference for other
MIA modules, not this one.

## 3. Initialize the database

```bash
python3 -c "
import sqlite3
conn = sqlite3.connect('mia_homestead.db')
conn.executescript(open('schema/mia_homestead_schema.sql').read())
"
python3 drivers/simulator.py --db mia_homestead.db --setup
```

## 4. Verify everything still works after the move

This is worth running once, right after transfer, before doing any new
development — confirms nothing broke in transit:

```bash
python3 scenarios/scenarios.py
```

Should print roughly 200 passed, 0 failed (the scenario suite has grown
substantially since this doc was first written — the exact count moves
as scenarios are added; what matters is 0 failed). If it doesn't,
something about the environment differs from where this was built and
tested — check the Python version (3.10+ required for the
`list[str] | None` type hints used throughout) before debugging the
logic itself.

## 5. Run it

```bash
# Terminal 1 — feeds simulated sensor data
python3 drivers/simulator.py --db mia_homestead.db --run

# Terminal 2 — the actual control loop
python3 main.py --db mia_homestead.db

# Terminal 3 (optional) — the assistant (local Ollama by default; no API key needed)
python3 assistant/greenhouse_assistant.py

# Digital twin viewer
python3 -m http.server 8000
# open http://localhost:8000/viewer/digital_twin.html
```

## What's safe to develop further here vs. what needs real hardware

Safe to keep building in simulation (per `docs/SIMULATION_STRATEGY.md`):
control logic changes, new modules, scenario tests, the assistant, the
digital twin, inventory/maintenance workflows.

Needs real hardware to actually verify: anything in `docs/MCU_PROTOCOL.md`
(the wire handshake itself), real dosing pulse durations/effects (the
physics sim's numbers are estimates), and real sensor calibration drift
behavior.

## Picking up where this left off

Two things were in progress when this was packaged:
1. A real Atlas Scientific pH driver — see `drivers/atlas_scientific_driver.py`
2. Current hardware pricing — see `docs/HARDWARE_BOM_CURRENT.md`

Both are covered below/attached.
