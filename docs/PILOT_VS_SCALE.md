# MIA Homestead — Pilot vs. Full Scale

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
| Est. cost | **~$150–200** (pH kit, 1 ESP32, 1 relay module, 1 dosing pump, air pump, circulation pump — reuses the exact "buy first" list) | **~$710+** full BOM (see `docs/HARDWARE_BOM_CURRENT.md`) |
| Timeline | Buildable now, no land/greenhouse needed | Gated on greenhouse construction |

## What the pilot actually needs to buy

Trimmed from the full BOM to the minimum that proves the whole
control/safety chain end to end — not a separate shopping list, a
subset of the same one:

- Atlas Scientific pH kit (~$175) — the EC loop can wait for phase 2
- 1x ESP32 dev board (~$20) + 1x 4-channel relay module (~$8)
- 1x peristaltic dosing pump (~$12) — pH-up only to start
- Aquarium air pump + airstone (~$10) — aeration, wired to always-on
- Small submersible circulation pump (~$15)
- DS18B20 temp probe (~$8)

**Pilot total: ~$248.** Skip EC/nutrient dosing, the watering/
fertilizer MCUs, PIR/beacon, and all power-monitoring hardware — none
of that is needed to validate the core safety-critical loop.

## What the pilot is FOR (in priority order)

1. **Flash and prove the Safety MCU firmware for real.** This is the
   single biggest unknown left in the whole system — it's written but
   never compiled or run. An LED standing in for the relay (per
   `firmware/safety_mcu/README.md`) gets you most of the way; a real
   pump gets you the rest.
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

## Software changes needed to represent this

The pilot is just another `AquaponicsCell` config entry — the modular
registry already supports this without new code:

```yaml
# config/modules.yaml — add alongside cell_a_aquaponics once greenhouse exists
- id: pilot_cell
  enabled: true
  class: modules.aquaponics_cell.AquaponicsCell
  cell_id: 2
  params:
    ph_target_min: 6.6
    ph_target_max: 7.2
    ec_target_min: 800
    ec_target_max: 1500
```

And a corresponding `cells` row + `layout.json` entry (position it
wherever it physically lives — a desk is a valid `position`). This
also validates something worth validating early: that the modular
architecture actually handles two simultaneously running cells
correctly, not just in theory.
