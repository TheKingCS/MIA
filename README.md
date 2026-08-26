# MIA Homestead

A standalone, modular homestead monitoring and automation node — starting
with greenhouse aquaponics, built to grow into whole-property automation
without rearchitecting anything already running.

## Design principles (in priority order)

1. **Survives without you.** Local control loop runs independent of the
   dashboard, the network, and MIA Home. See `docs/SAFETY_SPEC.md`.
2. **Two-tier safety.** Pi (brain) proposes actions; a separate Safety MCU
   (spinal cord) is the final authority and falls back to hard-coded safe
   defaults if it stops hearing from the Pi.
3. **Modular by construction, not by promise.** Every subsystem — an
   aquaponics cell, a power array, future poultry/irrigation modules — is
   a class implementing `MiaHomesteadModule`, registered in
   `config/modules.yaml`. Adding a subsystem later means one new file and
   one new config entry. Nothing else changes.
4. **Grounded, not gimmicky, personality.** The assistant layer
   (`assistant/`) answers questions about the system's real state via
   tool calls into the live database — never from assumption. See
   `assistant/PERSONALITY.md`.
5. **The assistant is never taught by hand.** Every module and service
   is required — enforced by Python's ABC mechanism, not convention —
   to declare what it does via `describe_capabilities()`. This gets
   rebuilt into the assistant's self-knowledge every time the system
   starts. See `docs/CAPABILITY_REGISTRATION.md`.
6. **The hardware shopping list is never reconstructed after the
   fact.** Every module also declares `describe_hardware_requirements()`
   — same enforcement — so the running BOM is accurate from day one,
   not assembled from memory once you're ready to buy.

## Layout

```
mia-homestead/
├── contracts/
│   ├── mia_homestead_contract.py   # base class every control module implements
│   └── capability.py               # the self-description requirement (see below)
├── core/
│   ├── module_registry.py          # loads + runs control modules from config
│   ├── notifications.py            # email/SMS alert dispatch
│   ├── inventory.py                # stock tracking, reorder alerts, orders
│   ├── maintenance.py              # task creation/assignment, recurring schedules
│   ├── order_queue.py              # terminal review for the to-order queue
│   ├── capability_registry.py      # aggregates every module's self-description
│   ├── hardware_registry.py        # aggregates every module's hardware needs into a running BOM
│   ├── hardware_bom.py             # CLI to view/export the hardware shopping list
│   ├── device_registry.py          # plug-and-play MCU recognition/pairing
│   └── device_setup_cli.py         # zero-technical-knowledge setup walkthrough
├── modules/
│   ├── aquaponics_cell.py          # pH/EC dosing control loop
│   ├── power_monitor.py            # solar/battery telemetry + load shed
│   └── self_preservation.py        # asks a human for help when critical + present
├── config/
│   └── modules.yaml                # which modules are active, and how
├── schema/
│   └── mia_homestead_schema.sql    # SQLite schema — full data model
├── assistant/
│   ├── PERSONALITY.md              # the greenhouse's voice, grounding rules
│   └── greenhouse_assistant.py     # conversational layer, tool-calling
└── docs/
    ├── SAFETY_SPEC.md               # failsafe behavior, the core of "this
    │                                 # has to work if I'm not around"
    ├── MCU_PROTOCOL.md               # Pi<->Safety MCU wire format + device pairing
    ├── SIMULATION_STRATEGY.md        # the four-tier simulate-before-buying process
    ├── CAPABILITY_REGISTRATION.md    # why the assistant never needs to be "taught"
    └── DEVICE_SETUP_GUIDE.md         # zero-technical-knowledge hardware setup
```

## Current status (v0.2 — runs end-to-end today, in simulation)

**Built and verified working (run live during development):**
- Full safety philosophy and failure-mode spec (`SAFETY_SPEC.md`)
- Pi↔Safety MCU wire protocol spec (`MCU_PROTOCOL.md`)
- Complete data schema — cells, sensors, dosing, power, yield, alerts,
  dead-man's-switch heartbeat, **inventory, orders, revenue, expenses,
  maintenance tasks and recurring schedules**
- Module contract with enforced staleness filtering and DB-backed alerts
- Working aquaponics cell control logic — confirmed via scenario tests
- Working power monitor — confirmed via scenario tests
- Modular registry — proven pattern for adding cells/arrays/subsystems
- Notification dispatch (email working now; SMS stubbed honestly)
- **Sensor simulator + closed-loop physics simulator** — proven via a
  full scenario regression suite (7/7 passing, including a real bug
  found and fixed during testing)
- **3D digital twin viewer** — spatial status view, color-coded by live
  data, runnable before any hardware exists
- **`main.py`** — the control loop orchestrator, now also runs periodic
  maintenance/calibration scans
- **Inventory manager** — confirmed: stock adjustments, low-stock
  alerts, order → receive flow all working correctly against real data
- **To-order approval queue** — low stock auto-proposes an order
  (never places one); confirmed the full approve/deny/skip cycle via
  both the assistant tools and a standalone terminal review tool
  (`core/order_queue.py`) that works without an API key
- **Maintenance manager** — confirmed: manual task creation with
  priority-based alerting, and automatic calibration-task generation
  from sensor `calibration_due` dates, both working correctly
- **Capability registry** — confirmed the enforcement is real: a test
  module missing `describe_capabilities()` raises `TypeError` on
  instantiation, not a silent gap discovered later. Confirmed the full
  flow: every module/service registers at startup, the assistant's
  system prompt is built live from that registry (never hand-written),
  and `get_system_capabilities` gives it full-detail lookup on demand
- **Self-preservation module** — confirmed all three states live:
  silent while a critical alert is open but no one's around, actively
  signals via a beacon the moment a human is detected nearby, and
  auto-resolves/turns the beacon off once the underlying issue clears
- **Hardware needs registry** — confirmed the enforcement is real (same
  test as capabilities: a module missing `describe_hardware_requirements()`
  raises `TypeError`). Ran the full aggregation across every module and
  got a real, correctly-summed shopping list with running cost estimate
  (`core/hardware_bom.py`) — no manual reconstruction needed
- **Digital twin "go here" locator** — the viewer now glows the EXACT
  physical object (a specific tank, the power array, the help beacon),
  not just the whole cell, pulsing red for critical. Confirmed live:
  injected a critical pH sensor fault and watched it correctly flag
  Tank A1 by name with the real alert message, while a simultaneous
  power warning and an active help request each located correctly to
  their own object at the same time. `main.py` now auto-exports this
  every control cycle — it's a running feature, not a manual dev step
- **Device registry (plug-and-play MCUs)** — confirmed: a device
  announcing a known, unclaimed role auto-pairs and its actuators get
  created automatically; an ambiguous/unlabeled device correctly queues
  for a human instead of guessing. `core/device_setup_cli.py` walks
  someone with zero technical background through exactly what to plug
  in and where, sourced from plain-language YAML files under
  `config/devices/roles/` — no code knowledge required
- **Assistant tools** include inventory, maintenance, revenue, the
  to-order queue, system self-knowledge, hardware needs, help requests,
  and device setup — it can answer "what's low on stock," "any open
  repair tasks," "is the greenhouse asking for help," "how do I set up
  the watering controller," "what hardware do I still need," and act on
  requests like "assign someone to fix the leak" or "pair that new
  device as fertilizer"
- **Real Atlas Scientific driver** (`drivers/atlas_scientific_driver.py`)
  — the actual I2C EZO protocol (not a simulation), same
  write-into-sensor_readings contract as the simulator so it's a
  drop-in replacement the moment hardware arrives. Confirmed it fails
  gracefully and informatively without hardware/smbus2 present, rather
  than an opaque import error. Includes a guided (never automated)
  calibration mode.
- **Current hardware pricing** — pH and EC kits were re-priced against
  live search results (`docs/HARDWARE_BOM_CURRENT.md`); the running BOM
  jumped from a rough ~$288 estimate to a real ~$573 once kit pricing
  replaced circuit-only guesses. This is exactly why the registry
  exists — the number changed, and every module's declaration updated
  in one place, not scattered across notes.
- **Desktop-ready** — `requirements.txt`, `.gitignore`, `SETUP.md` with
  a post-transfer verification step (`scenarios/scenarios.py` should
  print 7/7 passing after moving machines), and an initialized git repo
  with a full initial commit so Claude Code has real history to work
  from on the desktop.

**Not yet built (next steps, roughly in order):**
1. Safety MCU firmware implementing `MCU_PROTOCOL.md` (including the
   announce/pairing handshake device_registry.py already expects) —
   the Atlas Scientific sensor driver side is done; this is the other half
2. Real dosing limit values, once dosing pump hardware is chosen and tested
3. SMS provider wiring (Twilio or similar)
4. Real ordering integration (currently tracks order intent only —
   no live supplier API)
5. Physical beacon hardware for self-preservation (a light/speaker —
   the logic and DB layer are ready, this is the last missing piece)
6. Pricing pass on dosing pumps, PIR sensor, beacon, solar/battery
   hardware — only pH/EC/MCU pricing has been verified against current
   market data so far (see `docs/HARDWARE_BOM_CURRENT.md`)
7. MIA Home sync — pushing summarized state to the main dashboard
8. Local web UI for the on-site dashboard

## Full simulation-first workflow (no hardware required)

See `docs/SIMULATION_STRATEGY.md` for the full philosophy. Quick start
for each tier:

```bash
pip install pyyaml anthropic --break-system-packages

python3 -c "
import sqlite3
conn = sqlite3.connect('mia_homestead.db')
conn.executescript(open('schema/mia_homestead_schema.sql').read())
"
python3 drivers/simulator.py --db mia_homestead.db --setup

# Tier 3: run the full safety-behavior regression suite
python3 scenarios/scenarios.py

# Tier 4: view the spatial digital twin
python3 viewer/export_state.py --db mia_homestead.db
python3 -m http.server 8000
# open http://localhost:8000/viewer/digital_twin.html

# Full live loop (Tier 1/2 data + real control logic + live digital twin export)
python3 drivers/simulator.py --db mia_homestead.db --run &
python3 main.py --db mia_homestead.db     # auto-proposes reorders, maintenance tasks, and updates viewer/state.json every cycle

# Review what's flagged for purchase — no API key needed
python3 core/order_queue.py --db mia_homestead.db

# Set up a new physical device — zero technical knowledge required
python3 core/device_setup_cli.py --db mia_homestead.db

# View the running hardware shopping list
python3 core/hardware_bom.py --db mia_homestead.db

export ANTHROPIC_API_KEY=your_key_here
python3 assistant/greenhouse_assistant.py
```

## Running the assistant (once a populated DB exists)

```bash
pip install anthropic pyyaml --break-system-packages
export ANTHROPIC_API_KEY=your_key_here
python assistant/greenhouse_assistant.py
```

## Setting up the database

```bash
sqlite3 mia_homestead.db < schema/mia_homestead_schema.sql
```
