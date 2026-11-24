# MIA as the homestead's brain: smart ag plan

*Zac, 2026-11-24: "MIA OS should also be optimized for smart ag tech. She will be the brain and manager behind an
aquaponics greenhouse growing produce and fish, will manage my orchard, my garden, my water systems, my power
systems. She needs to be very very thoughtfully and thoroughly built out to take care of a homestead with me."*

This plan starts from what's built (mapped 2026-11-24), keeps the safety rules already decided, and orders the work
so the things that keep fish and plants alive come first.

## What's there today

| Area | Built | Who acts | The gap |
|---|---|---|---|
| Aquaponics greenhouse | `homestead/`: pH/EC dosing, DO, water temperature, climate, biofilter, fish health, leaks, circulation, succession, yield, traceability; 87 scenarios, a digital twin | The node and its safety MCU; MIA watches (`core/greenhouse_link.py`) | Simulation only; no command interface for MIA yet (DEC-0185); firmware gaps (no CRC, override switch unwired, no flow meter) |
| Orchard | Nothing | - | Everything: trees, chill hours, pruning, spraying, pollination, harvest windows |
| Garden | Planning and advice (`garden_plans`, `garden_week`, `planting_now`, `weather_watch`, `harvest_log`) | MIA advises | No soil moisture, no outdoor irrigation control, no pest log |
| Water | The greenhouse's flood/drain schedule (node); roof catchment maths (MIA) | Node for the greenhouse | No well, cistern, pressure or quality; no outdoor zones; no whole-property water picture |
| Power | The greenhouse's battery with load-shedding (node, simulated); hand-entered readings (MIA) | Node for the greenhouse | No inverter or charge controller link, no house loads, no generator auto-start |

## The rules that don't change

- **The node acts, MIA directs** (DEC-0150, amended by DEC-0185). MIA may set targets, schedules and modes as device
  commands, each asked for unless he granted that kind (DEC-0156). The node applies them within its own hard limits,
  its safety microcontroller may refuse, and MIA reports a change only once the node confirms it. Every adjustment
  is in the history with how to put it back.
- **The safety MCU is the spinal cord** (`homestead/docs/SAFETY_SPEC.md`). If the brain goes quiet for 60 seconds it
  falls back to safe defaults. Pumps default off, dosing comes in timed pulses only, stale sensors freeze
  actuation, and aeration and circulation are the last loads ever shed.
- **"Stop" never touches the greenhouse** (DEC-0185). Its loop keeps running.
- **No bare dosing or actuator tools in the assistant** (`homestead/CLAUDE.md` rules 5 and 6). Dosing goes
  through propose-then-approve.
- **Facts in code, simulation first.** Every control path is proven in the node's simulator and scenarios before
  it touches hardware.

## The order of work

### Phase A: MIA knows the whole homestead (no hardware, no decision needed)

1. **The orchard** (complete gap). *Built 2026-11-24 (`core/orchard.py`: his trees from Maintenance by the fruit in
   their names, each kind's needs, the year dated from his frost, "what does the orchard need this month?").* His trees by kind, variety, rootstock, where and when planted. Each kind's
   chill hours, years to bearing, pollination partners, spacing, pruning season and harvest window. A year of
   orchard work dated from his frost dates: dormant pruning, dormant oil, bloom and frost watch, thinning, summer
   pruning, harvest. And "what does the orchard need this month?"
2. **A whole-property water picture.** *Built 2026-11-24 (`core/water_budget.py`: "how long will my water last?",
   "the cistern is at 800 gallons", "my catchment roof is 600 square feet").* His sources (well, cistern, rain catchment, municipal) and his uses
   (greenhouse, garden, orchard, house, animals), as a daily and monthly water budget. Tank levels come as readings
   he logs until sensors arrive.
3. **A whole-property power picture.** *Built 2026-11-24 (`core/power_picture.py`: "if the power goes out, how long
   will my battery run the essentials?", "the well pump draws 1000 watts for an hour a day", "my battery is 10 kWh").* Sources (solar, grid, generator, battery), the loads that matter (well pump,
   aeration, heat), and how long the essentials run on battery. It reads the readings he logs today, with sensor
   feeds later.
4. **The homestead morning sheet.** *Built 2026-11-24 (the question plan "homestead": "how's the homestead?").* One picture of the fish, the beds, the orchard's task, water and power, with
   the one thing to do first (a question plan, the same shape as the project picture).

### Phase B: the node takes MIA's directions (in simulation; follows `homestead/CLAUDE.md`)

*Designed 2026-11-24: `homestead/docs/MIA_COMMAND_INTERFACE.md` (the whitelist, the node's checks, one decision for
Zac, WAITING_ON 0zu).*

1. **The node's command interface** (DEC-0185). Set a target, a schedule or a mode, through a signed, local-only
   channel. The node checks each command against its limits, the MCU may refuse, and the node confirms what it
   applied. Every refusal is said, never retried around.
2. **MIA's side.** The capability and its grants, the confirmation shown only after the node's, and undo as a
   counter-command.
3. **Scenarios.** Every command is proven against the simulator, including the refusals, a dropped link and a stale
   sensor.

### Phase C: the 55-gallon pilot (hardware; `homestead/docs/PILOT_VS_SCALE.md`)

The fishless cycle first, then the firmware gaps closed before fish: message CRCs, the override switch wired, and a
flow meter so dosing limits are enforced.

### Phase D: beyond the greenhouse (hardware, once the pilot runs)

- Outdoor irrigation zones with soil moisture: the node's `watering_mcu` role, with moisture-triggered watering
  for the garden and orchard.
- Well and cistern: level, pressure and pump run-time, with low-water and dry-run protection on the MCU.
- House power: an inverter and charge controller feed, house loads, and generator auto-start with the MCU's
  interlock.

## Decisions for Zac (WAITING_ON 0zn to 0zp)

- **What's in the orchard?** Which trees he has or plans: kinds, roughly how many, and where.
- **Water and power hardware.** Which well pump, cistern or tank, inverter or charge controller he has or will
  buy. Their makes decide how MIA can read them; open, local interfaces (Modbus, MQTT, a local web API) are
  recommended over cloud-only ones.
- **The order.** Recommended: Phase A now (it needs nothing), Phase B in simulation next, the pilot when he's ready
  to buy parts (about $263), Phase D after. The other way is to start the pilot hardware first.
