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
7. **Learning is evidence-based and always human-approved.** The
   experiment system proposes controlled changes to a cell's dosing
   targets, tracks real yield outcomes, and recommends adopting what
   works — through the same approval-queue pattern as inventory
   ordering. It never silently changes what a cell doses toward, and
   it's explicit that a single home-scale experiment is suggestive
   evidence, not statistical proof. See `docs/PILOT_VS_SCALE.md` on
   why running the same experiment across the pilot and full-scale
   cells is how real confidence actually gets built.
8. **The assistant is an Aquaponics Scientist and Greenhouse Manager,
   not a chatbot with a dashboard attached.** It knows what's planted
   where, how much was expected vs. actually harvested, how much water
   and nutrient went where and why, and — critically — how everything
   is physically wired and plumbed and why, so a diagnosis points at a
   specific relay channel and pipe segment instead of a generic
   troubleshooting checklist. See `assistant/PERSONALITY.md`'s Identity
   section and `docs/CAPABILITY_REGISTRATION.md`.
9. **Self-understanding tracks development, not just current state.**
   Every capability/hardware registration diffs against what was known
   last time — real changes get a timestamped, field-level entry in
   `system_changelog`; an unchanged restart produces zero noise. Verified
   directly: two identical registrations logged nothing, one real edit
   logged exactly two precise entries. `core/self_audit.py` is the
   enforcement step — run it before considering any change done; it
   catches the specific failure of writing a real module and forgetting
   to wire it into registration (proven: a deliberately-unregistered
   test module was caught on the first run).
10. **Changes to configuration can be undone — by you, or automatically.**
    `core/backup_manager.py` snapshots config files and live control
    parameters (never history/alerts/yield/species knowledge — those
    are earned record, not config) before a change, and watches for a
    critical-alert spike afterward. Proven live: applied a deliberately
    dangerous dosing limit change (10ml → 500ml max per dose), simulated
    the resulting critical alerts, and confirmed the system detected
    the spike and reverted the limit on its own, with a clear
    notification explaining exactly what happened and why.
11. **Every capability claim is either proven or honestly marked
    unverified — there's no third option.** `Capability.verification_evidence`
    cites the actual scenario test or dated manual proof behind each
    module; `docs/FEATURES_AND_CAPABILITIES.md` regenerates from this
    live data every startup, so the running features list can never
    drift into aspiration. Currently 15/15 registered modules carry
    real evidence — checked and enforced by `core/self_audit.py`.
12. **Caught a real "should auto-update but didn't" bug in this very
    pass.** `main.py` was calling the doc generators' `generate()`
    function, which only returns a string — it never actually wrote
    the file. Found by deliberately deleting both generated docs and
    running `main.py` for real: they didn't come back. Fixed by adding
    a `generate_and_write()` entry point and confirmed by repeating
    the exact same test — delete, run, confirm regeneration with a
    fresh timestamp and correct 15/15 coverage.
13. **Four sustaining features from the brainstorm, all built and
    proven live:** explain-yourself logging for load-shedding and
    beacon actions (`core/action_log.py`), a two-stage dead-man's-switch
    escalation ladder that correctly escalates once per level without
    spamming (`core/deadmans_switch.py`), predictive consumable
    forecasting that projects real depletion dates from actual
    consumption rate (`InventoryManager.forecast_depletion`), and a
    periodic state-of-the-greenhouse report composing existing data
    into one digest (`core/report_generator.py`).
14. **Conversational coverage is audited, not assumed.** A hands-on
    review found six real backend actions with no matching assistant
    tool — water usage logging, harvest/failure recording, adding a
    species, maintenance task status/assignment, denying a parameter
    change — all fixed. `core/self_audit.py` step 5 now checks this on
    every build with a keyword heuristic; run against the fixed code it
    correctly flags only the two actions that are deliberately NOT
    commandable (direct dosing pulses, raw notification sends — both
    bypass safety gating if exposed as bare chat commands), confirming
    the heuristic works without over- or under-flagging.

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
│   ├── device_setup_cli.py         # zero-technical-knowledge setup walkthrough
│   ├── species_registry.py         # ideal pH/EC/temp ranges per plant/fish species
│   ├── bed_planting.py             # what's planted where, cell compatibility checks
│   ├── experiment_manager.py       # the aquaponics scientist — proposes/runs/evaluates experiments
│   ├── infrastructure_registry.py  # wiring + plumbing knowledge, with rationale
│   ├── diagnostics.py              # cross-references alerts against infrastructure for specific guidance
│   ├── self_audit.py               # catches modules that exist but aren't wired into registration
│   ├── backup_manager.py           # config snapshot/restore, auto-rollback on post-update alert spike
│   ├── backup_cli.py                # manual snapshot/restore, no API key needed
│   ├── generate_capabilities_doc.py # regenerates docs/FEATURES_AND_CAPABILITIES.md from live data
│   ├── generate_bom_doc.py         # regenerates docs/HARDWARE_BOM_LIVE.md from live data
│   ├── action_log.py               # uniform "why did you do that" for non-dosing automated actions
│   ├── deadmans_switch.py          # two-stage check-in escalation ladder
│   └── report_generator.py         # periodic state-of-the-greenhouse digest
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
- Notification dispatch (email + SMS via free carrier email-gateway, both working — see punch-list item #3)
- **Sensor simulator + closed-loop physics simulator** — proven via a
  full scenario regression suite (7/7 passing, including a real bug
  found and fixed during testing)
- **3D digital twin viewer** — spatial status view, color-coded by live
  data, runnable before any hardware exists
- **Operations dashboard** (`viewer/dashboard.html`) — data-dense
  live-data overview (sensor trends, alerts, yield vs. target,
  experiments, inventory, maintenance, power), distinct from the
  spatial digital twin above; confirmed against a real seeded DB and
  screenshotted in a real headless browser, not just eyeballed as code
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
  jumped from a rough ~$288 estimate to a real ~$710 once kit pricing,
  aeration/circulation pumps, and relay modules (a real gap — GPIO pins
  can't directly drive a 12V pump, caught and fixed) replaced guesses.
- **The aquaponics scientist** — `species_registry.py`,
  `bed_planting.py`, and `experiment_manager.py`, fully proven live:
  seeded 3 baseline species profiles, planted lettuce + basil in the
  same cell (no compatibility warning — their ranges overlap), then
  added a fabricated incompatible species and confirmed the warning
  fired correctly. Ran a complete experiment lifecycle end to end:
  proposed a target change, confirmed it took effect on the LIVE
  control loop with no restart (`cell._current_targets()` picked up
  the override immediately), logged realistic before/after yield data,
  completed the experiment, got a correct evidence-based "adopt"
  recommendation (+32.3% yield), approved it, and confirmed the change
  correctly promoted from `set_by: experiment` to `set_by: manual` —
  the exact distinction between "currently testing" and "adopted policy."
- **Infrastructure knowledge + diagnostics** — wiring detail (relay
  channel, port, mounting location, WHY wired that way) lives directly
  in the device role configs; plumbing topology (pipe segments, sizes,
  flow direction, WHY routed that way) lives in
  `config/infrastructure/plumbing.yaml`. Proved the full diagnostic
  chain through REAL code, not a hand-written test: backdated a pH
  sensor reading, ran the actual control cycle, let the base contract
  raise a genuine staleness alert, then confirmed the diagnostic engine
  correctly traced it to the exact MCU (pH Dosing Controller, PORT 2,
  relay channel 1), its physical mounting location, and auto-filed a
  maintenance task with that diagnosis attached — not a generic "check
  the sensor" message. Also caught and fixed a real gap in the
  process: the base contract's staleness alerts didn't include sensor
  TYPE, only a numeric ID, which would have made this kind of specific
  diagnosis impossible — fixed at the source (`mia_homestead_contract.py`)
  rather than worked around.
- **Resource tracking with rationale** — `dosing_events` now actually
  gets written to (it existed in the schema but nothing wrote to it
  until this pass) with a plain-language reason for every dose;
  `water_usage_events` and expected-vs-actual yield comparison track
  the same "how much and why" for irrigation and harvest outcomes.
- **Explicit identity** — `assistant/PERSONALITY.md` now states
  outright what "Aquaponics Scientist and Greenhouse Manager" means:
  forms and tests hypotheses, knows the full operational picture down
  to individual pipe segments, and is a steward that proposes and
  diagnoses continuously but never bypasses the human-approval gates
  already built into the safety and financial-decision layers.
- **Desktop-ready** — `requirements.txt`, `.gitignore`, `SETUP.md` with
  a post-transfer verification step (`scenarios/scenarios.py` should
  print 7/7 passing after moving machines), and an initialized git repo
  with a full initial commit so Claude Code has real history to work
  from on the desktop.
- **Safety MCU firmware** (`firmware/safety_mcu/safety_mcu.ino`) — real
  ESP32 code implementing the full protocol: announce/pair handshake,
  heartbeat timeout, safe fallback (dosing forced off, aeration/
  circulation to their configured safe defaults), local dosing limits
  as a redundant safety layer independent of the Pi. **Not compiled or
  tested** — no ESP32 toolchain was available in the environment that
  wrote it. Honest, specific caveats and known gaps (actuator ID
  mapping, blocking delay() during pulses, no live limit sync) are
  documented in `firmware/safety_mcu/README.md` rather than glossed
  over — this is a strong first draft, treat it as one.
- **Complete hardware pricing pass** — dosing pumps re-priced down
  (~$10–15 real vs. $25 guess), solar charge controller priced
  (~$100–150 for RS485/Modbus-capable), PIR sensor confirmed accurate.
  Battery bank deliberately left unpriced — pricing it before sizing
  it against real load would just be a number you'd have to redo.
  Running BOM total: **~$674** (see `docs/HARDWARE_BOM_CURRENT.md`
  for full sourcing).

**Not yet built (next steps, roughly in order):**
1. **Flash-test the Safety MCU firmware on real hardware.** It now
   **compiles clean** (`pio run` against ESP32 + ArduinoJson 6.21.6,
   2026-08-30: RAM 6.7%, Flash 21.5%, zero source changes needed) — the
   remaining gap is a real board, not the code. See
   `firmware/safety_mcu/README.md`'s known-gaps list before flashing,
   especially the actuator-ID-to-pin mapping, which needs resolving
   first.
2. Real dosing limit values, once dosing pump hardware is chosen and tested
3. ~~SMS wiring~~ — **done 2026-08-31** (`core/notifications.py`,
   `CARRIER_SMS_GATEWAYS`). Corrected 2026-08-30 from an original
   Twilio/vendor-API-shaped stub, per this project's own
   no-outside-dependency stance — ships via a free carrier
   email-to-SMS gateway instead, reusing the already-working SMTP
   path with zero new account/API key. Set
   `primary_contact_phone`/`primary_contact_carrier` (a key like
   `"verizon"`/`"att"`/`"tmobile"`) in `NotificationConfig`. A USB GSM
   modem with a prepaid SIM remains a real hardware alternative later
   if gateway reliability ever becomes a problem — not needed now.
4. ~~Real ordering integration~~ — **done at the code level, 2026-08-31.**
   Corrected 2026-08-30: this was mischaracterized as needing a live
   vendor checkout API. It doesn't, and shouldn't — `approve_order`
   only flips a status, and the actual purchase stays human-executed
   by design (mirrors the propose-then-approve pattern everywhere else
   spend is involved). The real, fixable gap turned out to be smaller
   and more concrete: `inventory_items.supplier_url`/`unit_cost` were
   already in the schema and already fetched by
   `core/inventory.py`'s real `get_to_order_list()` — but three
   separate consumer surfaces each silently dropped it anyway:
   `core/order_queue.py`'s CLI display never printed it,
   `assistant/greenhouse_assistant.py`'s tool had its own hand-copied
   query that had drifted and never selected it at all (now delegates
   to `InventoryManager` instead, so it can't drift again), and the
   dashboard's low-stock panel didn't request or render it. All three
   fixed and verified end-to-end with a real seeded item (a clickable
   source link now shows up in the CLI, the assistant's tool result,
   and the dashboard). What's still genuinely missing — real supplier
   URLs for real consumables — is data entry that depends on actually
   choosing real suppliers once real chemicals/feed are being stocked,
   not a code gap.
5. Physical beacon hardware for self-preservation (a light/speaker —
   the logic and DB layer are ready, this is the last missing piece)
6. Battery bank sizing and pricing, once real greenhouse load is known
7. ~~MIA Home sync — pushing summarized state to the main dashboard~~ —
   **fully done and automated, 2026-09-02** (see
   `docs/MIA_HOME_SYNC_PLAN.md`): this repo's `viewer/export_home_snapshot.py`
   (wired into `main.py`) produces the snapshot; `~/Projects/MIA`'s
   `core/homestead_manager.py` + a "Homestead" dashboard widget ingest
   it — verified end-to-end with a real exported file, which caught
   and fixed a real shape mismatch before it shipped (see the plan
   doc). Transport is now automated too: `core/mia_home_sync.py`'s
   `MiaHomeSync` pushes the snapshot via `rsync` on a configurable
   interval (`config/mia_home_sync.yaml`), live-verified pushing to a
   real local destination and being picked up by MIA's own scanner —
   no manual copy step left.
8. ~~Local web UI for the on-site dashboard~~ — **done** (2026-08-30),
   see `viewer/dashboard.html` above. Two real gaps this surfaced were
   both fixed in later commits, not left open: `power_telemetry` had
   no driver at all — fixed 2026-08-30 (`drivers/simulator.py` now
   simulates a solar/battery array); the alerting module never
   de-duped identical repeated alerts — fixed at the actual source
   2026-08-30/31 (`contracts/mia_homestead_contract.py`'s
   `raise_alert()`), not just worked around at export time anymore.

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

# ...or the operations dashboard (same server, different page)
python3 viewer/export_dashboard_state.py --db mia_homestead.db
# open http://localhost:8000/viewer/dashboard.html

# Full live loop (Tier 1/2 data + real control logic + live digital twin export)
python3 drivers/simulator.py --db mia_homestead.db --run &
python3 main.py --db mia_homestead.db     # auto-proposes reorders, maintenance tasks, and updates viewer/state.json every cycle

# Review what's flagged for purchase — no API key needed
python3 core/order_queue.py --db mia_homestead.db

# Set up a new physical device — zero technical knowledge required
python3 core/device_setup_cli.py --db mia_homestead.db

# View the running hardware shopping list
python3 core/hardware_bom.py --db mia_homestead.db

# No API key, no internet — runs against a local Ollama model by default.
# Requires Ollama running (`systemctl --user status ollama`) with a
# tool-capable model pulled (default: llama3.2:latest).
python3 assistant/greenhouse_assistant.py
```

## Running the assistant (once a populated DB exists)

Local model (default — no API key, no internet dependency, matches this
system's self-sufficiency principle; see `docs/OFFLINE_ASSISTANT_PLAN.md`):

```bash
pip install pyyaml --break-system-packages
python assistant/greenhouse_assistant.py
```

Cloud (Anthropic) — an explicit opt-in, kept for re-running the local-vs-
cloud model bake-off, not the recommended default:

```bash
pip install anthropic pyyaml --break-system-packages
export ANTHROPIC_API_KEY=your_key_here
python assistant/greenhouse_assistant.py --cloud
```

## Setting up the database

```bash
sqlite3 mia_homestead.db < schema/mia_homestead_schema.sql
```
