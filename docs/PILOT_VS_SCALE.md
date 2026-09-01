# MIA Homestead — Pilot vs. Full Scale

## Status (2026-08-31)

**Software scaffold done, running in simulation now.** `pilot_cell`
(`config/modules.yaml`, `cell_id: 2`) is enabled today — deliberately
not gated on "once greenhouse exists" like a second full-scale cell
would be, since the whole point of the pilot is that it doesn't need
one. `drivers/simulator.py --setup-pilot` seeds it with exactly the
trimmed hardware scope below (pH + water-temp sensors only, one pH-up
pump, always-on aeration/circulation, no EC probe, no fish yet).
Verified for real, not assumed: ran the actual control loop with both
`cell_a_aquaponics` and `pilot_cell` live simultaneously — no crash,
`pilot_cell` correctly raised an honest "no EC reading" warning (not an
error) exactly as its trimmed scope predicts, and confirmed the two-cell
case the software was always claimed to support but had never actually
been run. That check caught one real bug: the dashboard's sensor tiles
had no cell label, so two cells produced two visually-identical "Water
pH" tiles — fixed (`viewer/dashboard.html` now prefixes each tile with
its cell name once more than one cell exists).

**What this does NOT change**: nothing about the physical build below.
This is the pure-software half — proving the architecture handles a
second cell correctly before physical hardware ever needs to. The
buy/flash/wire/calibrate steps are still real-world actions only the
project owner can take.

## The core decision: build the pilot now

Simulation validates *logic*. It can't validate real dosing pulse
magnitudes, real nitrification drift rates, real firmware behavior, or
real device pairing — those numbers in `physics_sim.py` are explicitly
labeled placeholders until something real produces data to replace
them. A 5-gallon pilot is the cheapest possible way to get that data,
and every dollar spent on it is reused at full scale, not thrown away.

## Side-by-side

| | **Pilot (5-gallon)** | **Full scale** |
|---|---|---|
| Tank | 5-gal bucket | 500–1,000 gal, split across 2+ tanks |
| Grow bed | 1 small tray, 2–4 net pots | 1:1–2:1 sqft-to-gallons, media bed |
| Fish | None, or 1–2 hardy guppies | Tilapia, real stocking density |
| Cells (software) | 1 (`pilot_cell`) | 2–3, modular — each an independent `AquaponicsCell` config entry |
| MCUs | 1 (covers pH dosing; add a 2nd for fertilizer once EC loop is added) | 3 per cell (watering, fertilizer, pH dosing) |
| Dosing pumps | 1–2 | 3 per cell |
| Power | Wall outlet + optional small battery for MCU fallback testing | Real solar array + battery bank, sized to load |
| Structure | None — a shelf or desk | Real greenhouse |
| Est. cost | **~$256** (real, verified pricing/sourcing as of 2026-08-31 — see below) | **~$17,400–$23,700** real sourced structure+equipment BOM at N=3 cells (see `docs/HARDWARE_BOM_FULL_TIERS.md`) |
| Timeline | Buildable now, no land/greenhouse needed | Gated on greenhouse construction |

## What the pilot actually needs to buy

Trimmed from the full BOM to the minimum that proves the whole
control/safety chain end to end — not a separate shopping list, a
subset of the same one:

Real, sourced pricing (WebSearch/WebFetch, 2026-08-31 — see
`drivers/simulator.py`'s `seed_pilot_shopping_list()` for the full
sourcing notes and confidence level per item):

- Atlas Scientific KIT-101P pH kit — **$174.99** (confirmed direct from
  atlas-scientific.com) — the EC loop can wait for phase 2
- Adafruit HUZZAH32 ESP32 (pre-soldered) — **$20.95** (confirmed direct
  from adafruit.com) + 4-channel relay module — **~$10** (real product,
  Amazon-listing price estimate)
- 12V DC peristaltic dosing pump — **~$12** (real product, Amazon-listing
  price estimate) — pH-up only to start
- Aquarium air pump + airstone kit — **~$12** (real product, Amazon-listing
  price estimate) — aeration, wired to always-on
- Small submersible circulation pump — **~$15** (real product,
  Amazon-listing price estimate)
- DS18B20 temp probe — **$10.95** (confirmed direct from sparkfun.com —
  meaningfully more than this doc's original ~$8 guess)

**Pilot total: ~$256.** (Up modestly from an earlier ~$248 estimate —
mainly the DS18B20 turning out to cost more than originally guessed,
now a real confirmed number instead of a guess.) Skip EC/nutrient
dosing, the watering/fertilizer MCUs, PIR/beacon, and all
power-monitoring hardware — none of that is needed to validate the
core safety-critical loop.

**This list is now a real, ready-to-review purchase queue in the app
itself**, not just this document — run
`python3 drivers/simulator.py --db mia_homestead.db --seed-pilot-shopping-list`
once, then `python3 core/order_queue.py --db mia_homestead.db` to
approve/deny each line item before actually buying anything (same
propose-then-human-approves gate every purchase in this project goes
through — nothing here places a real order on its own). The
Amazon-listing items are real products with real URLs but
estimated/unconfirmed current prices — confirm at checkout, same as
this doc has always said.

## What the pilot is FOR (in priority order)

1. **Flash and prove the Safety MCU firmware for real.** Half done in
   software (2026-08-30): it now **compiles clean** against real
   ESP32 + ArduinoJson toolchains (`firmware/safety_mcu/platformio.ini`,
   `pio run`) — the remaining unknown is real hardware behavior, not
   whether the code is even valid. An LED standing in for the relay
   (per `firmware/safety_mcu/README.md`) gets you most of the way; a
   real pump gets you the rest.
2. **Calibrate real dosing pulse magnitudes.** How much does a 1-second
   pulse actually move pH in a 5-gallon volume, at your actual pump's
   flow rate? That number replaces the placeholder in
   `physics_sim.py`'s `DOSE_EFFECT_PER_SECOND`, which makes every future
   scenario test more trustworthy, not just the pilot itself.
3. **Run a real device pairing.** Confirm the announce → pair →
   actuator-creation flow in `device_registry.py` actually works
   against firmware, not just `announce_device()` called directly from
   a test script.
4. **Fishless-cycle the biofilter.** Standard aquaponics practice —
   dose ammonia and track the nitrogen cycle establishing (~4–6 weeks)
   before any livestock goes in, at either scale. Doing this on the
   pilot first means you'll recognize what a healthy cycle looks like
   before it matters on a system with real fish in it.
5. **Stress-test the actual failure modes**, not just simulated ones —
   physically unplug the Pi mid-dose and watch the MCU fall back for
   real; physically disconnect the pH probe and confirm the staleness
   alert fires on schedule, not just in `scenarios/scenarios.py`.

## What changes when scaling up — and what doesn't

**Carries over directly, no rework:**
- All control logic, the module contract, the safety spec
- The Safety MCU firmware (same code, more instances)
- The capability/hardware registries, inventory, maintenance, assistant
- The device role configs — same watering/fertilizer/pH-dosing roles,
  just more of each

**Recalibrated, not rebuilt:**
- Dosing pulse durations and `dosing_limits` — a 5-gallon pulse and a
  500-gallon pulse are not the same number; the pilot gives you a
  starting ratio, not a final answer
- `physics_sim.py`'s drift constants — same mechanism, new numbers

**Genuinely new:**
- Real greenhouse structure, solar/battery sizing against real load,
  multiple tank cells, fish stocking

## The recommendation worth calling out explicitly

**Don't decommission the pilot once the full-scale system exists.**
Keep it running permanently as a staging cell — the same role a
staging server plays for software. Any future control-logic change
gets proven on the pilot (which now has real historical data behind
it, not just simulation) before it ever touches the tank with real
fish and real money in it. This is the same simulation-first discipline
from `docs/SIMULATION_STRATEGY.md`, just extended one more tier: sim →
scenario tests → pilot hardware → production hardware.

## Software changes needed to represent this — done (2026-08-31)

The pilot is just another `AquaponicsCell` config entry — the modular
registry already supported this without new code, and now actually has
one:

```yaml
# config/modules.yaml — real entry, not a proposal
- id: pilot_cell
  enabled: true
  class: modules.aquaponics_cell.AquaponicsCell
  cell_id: 2
  params:
    ph_target_min: 6.6
    ph_target_max: 7.2
    ec_target_min: 800   # unused until an EC probe exists (phase 2)
    ec_target_max: 1500
```

Plus a real `cells` row + `layout.json` entry (`drivers/simulator.py
--setup-pilot`; positioned off to the side in the digital twin — "a
desk is a valid position"). This also validated something worth
validating early, for real: the modular architecture running two
simultaneous cells correctly, not just in theory — see "Status" above
for what that check actually found and fixed.
