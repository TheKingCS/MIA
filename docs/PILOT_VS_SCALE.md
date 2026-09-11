# MIA Homestead — Pilot vs. Full Scale

## Status (2026-09-10)

**Scope change: the pilot is now a 55-gallon tank, fish-inclusive —
supersedes the earlier 5-gallon fishless plan.** The project owner
acquired a real 55-gallon tank and wants this pilot to double as a
genuine proof-of-concept for full-scale fish stocking, not just a
cheap safety-chain proof with no livestock. This replaces the prior
"5-gallon bucket, no fish or 1-2 hardy guppies" plan entirely — same
`pilot_cell` (`config/modules.yaml`, `cell_id: 2`), same role (prove
the control/safety chain, calibrate real dosing), now scaled up and
scoped to include real fish from the start.

**What carries over unchanged from the 5-gallon plan**: everything
software-side already proven — the control loop, safety fallback, MCU
serial transport, day-one hardware readiness (override switch,
notification config, non-blocking firmware pulses) — none of that
depended on tank size. What changes is the physical BOM and the
fishless-cycle-then-stock timeline below.

## Fish: bluegill/sunfish — decided 2026-09-10

**Bluegill / sunfish (*Lepomis macrochirus*)** — chosen over both
goldfish (ornamental, disproportionately high-bioload per pound — see
below) and tilapia (the full-scale plan's species, but needs more room
and warmer water than this tank/climate comfortably supports at real
stocking density). Real, cited profile now in `core/species_registry.py`'s
`BASELINE_SPECIES` (`common_name: "Bluegill"`) so
`modules/aquaponics_cell.py`'s water-temp thermal-stress monitoring has
a real range to check against once fish are actually stocked:

- Ideal range 68-79°F (20-26°C); tolerates a wider swing than a
  tropical species like tilapia — likely no water heater needed for
  most indoor/climate-controlled setups, confirm against your actual
  ambient conditions before assuming.
- pH tolerance 6.5-8.5 — matches this pilot's existing `ph_target_min`/
  `ph_target_max` (6.6-7.2) comfortably.
- Real stocking rule of thumb: ~1 lb of bluegill per 10 gallons in a
  system with adequate filtration. At 55 gallons, that supports
  roughly 3-5 adult bluegill (bluegill can reach ~12 inches / ~1 lb) —
  consistent with the tank owner's own conservative "about 3" estimate.
- A real, harvestable food fish — keeps this pilot representative of
  the eventual full-scale food-production goal, unlike an ornamental
  species.
- Real, honest caveat on timeline: grow-out to a marketable ~3/4-1.25
  lb fish is commonly cited as 12-24+ months depending on conditions —
  this is a multi-season commitment, not a quick harvest.

**Not done yet, a real physical step for later**: once fish are
actually stocked, set the pilot tank's `tanks.species` to `"Bluegill"`
(matches `species_profiles.common_name`) so the thermal-stress
monitoring picks up this real range automatically — no code change
needed, just real data entry once the tank has real fish in it.
**Fishless-cycle first** (see priorities below) — no fish go in until
the biofilter is proven, regardless of species.

## Side-by-side

| | **Pilot (55-gallon, fish-inclusive)** | **Full scale** |
|---|---|---|
| Tank | 55-gal | 500–1,000 gal, split across 2+ tanks |
| Grow bed | Small media bed or raft, sized to real bioload — not yet purchased, see below | 1:1–2:1 sqft-to-gallons, media bed |
| Fish | 3-5 bluegill (*Lepomis macrochirus*) — decided, see above | Tilapia, real stocking density |
| Cells (software) | 1 (`pilot_cell`) | 2–3, modular — each an independent `AquaponicsCell` config entry |
| MCUs | 1 (covers pH dosing; add a 2nd for fertilizer once EC loop is added) | 3 per cell (watering, fertilizer, pH dosing) |
| Dosing pumps | 1 (pH-up) today; pH-down likely needed once real fish bioload is observed — not yet bought | 3 per cell |
| Water quality monitoring | pH + water-temp (existing) + **EC now recommended** (real fish bioload/nutrient dynamics, unlike the fishless plan) + **DO strongly recommended** (real animal welfare — DO crashes are the leading cause of fish loss) | Full pH/EC/DO suite |
| Power | Wall outlet + optional small battery for MCU fallback testing | Real solar array + battery bank, sized to load |
| Structure | None — a shelf, stand, or desk | Real greenhouse |
| Est. cost | **~$848** (real, verified against `seed_pilot_shopping_list()` — the original ~$263 pilot BOM plus a confirmed-price EC kit and DO kit; tank/pump upsizing/biofilter media/fish are real additional cost not yet priced, see below) | **~$17,400–$23,700** real sourced structure+equipment BOM at N=3 cells (see `docs/HARDWARE_BOM_FULL_TIERS.md`) |
| Timeline | Buildable now; fishless-cycle (4-6 weeks) before any fish go in | Gated on greenhouse construction |

## What changes in the shopping list

The existing ~$263 pilot list (pH kit, ESP32, DS18B20 temp probe, relay,
pH-up dosing pump, air pump, circulation pump, override switch — see
`drivers/simulator.py`'s `seed_pilot_shopping_list()`) was sized for a
fishless 5-gallon bucket. Real changes for 55 gallons with fish:

**Added to the shopping list now** (real, already-confirmed pricing —
reused from `docs/HARDWARE_BOM_FULL_TIERS.md`'s small-tier research,
not re-guessed):
- **Atlas Scientific EC-KIT-1.0 — $230** (confirmed, atlas-scientific.com).
  Real fish bioload changes nutrient dynamics enough to be worth
  reading, even though EC has no automated dosing built yet (alert-only,
  same as DO below).
- **Atlas Scientific DO Kit — $354.99** (confirmed, atlas-scientific.com).
  Recommended, not just optional the way it was for the small tier's
  lower stocking density — this pilot now has real animals in it, and
  DO crashes are the single leading cause of catastrophic fish loss.
  Your call on budget, but flagged here plainly rather than left out
  quietly.

**Flagged as needing real re-sourcing, NOT yet added (don't guess a
specific product without verifying it first)**:
- **Aeration and circulation pump sizing.** The current pilot's air
  pump (rated 15-40 GPH, "3-20 gallon buckets") and circulation pump
  (80 GPH) were sized for a 5-gallon bucket and are very likely
  undersized for 55 gallons. Real aquaponics sizing guidance: circulate
  the full tank volume at least twice an hour (~110 GPH minimum for 55
  gallons), with 100-300 GPH commonly recommended for a complete small
  aquaponics system. `HARDWARE_BOM_FULL_TIERS.md`'s small-tier BOM
  already has a confirmed, same-brand option one size up (Active Aqua
  AAPW1000, 1000 GPH, $69.65, confirmed) that would comfortably cover
  this — real oversizing headroom at a low price, a defensible choice
  if you'd rather not shop further — but a properly-sized option
  in-between hasn't been individually sourced/confirmed yet.
- **A real biofilter media quantity for 55 gallons.** The small-tier
  BOM's bio balls (900-count, $119.99, confirmed) are sized for 500
  gallons — real overkill at this scale, but no smaller confirmed
  listing has been sourced yet for a 55-gallon-appropriate quantity.
- **A pH-down dosing pump.** Not needed for a fishless system (nothing
  was pushing pH down); real fish bioload may change that. Recommend
  waiting for real pH-drift data from the fishless-cycle period before
  buying a second pump you might not need.
- **The fish themselves** — bluegill, 3-5 of them per the stocking math
  above; real cost depends on local source (bait shop/hatchery/local
  fishing, common for bluegill specifically), not researched here.

## What the pilot is FOR (in priority order) — fish-inclusive revision

1. **Fishless-cycle the biofilter FIRST.** Now the load-bearing first
   step, not priority #4 — real animals don't go in until this is
   done. Standard aquaponics practice: dose ammonia and track the
   nitrogen cycle establishing (~4–6 weeks) before any livestock goes
   in. Doing this before fish arrive means recognizing what a healthy
   cycle looks like before it matters with real animals in the tank.
2. **Flash and prove the Safety MCU firmware for real.** Compiles clean
   against real ESP32 + ArduinoJson toolchains
   (`firmware/safety_mcu/platformio.ini`, `pio run`) — the remaining
   unknown is real hardware behavior, not whether the code is valid.
3. **Calibrate real dosing pulse magnitudes** — now at 55-gallon
   volume, not 5-gallon. How much does a 1-second pulse actually move
   pH in a 55-gallon volume, at your actual pump's flow rate? That
   number replaces the placeholder in `physics_sim.py`'s
   `DOSE_EFFECT_PER_SECOND`.
4. **Run a real device pairing.** Confirm the announce → pair →
   actuator-creation flow in `device_registry.py` actually works
   against firmware, not just `announce_device()` called directly.
5. **Stress-test the actual failure modes** — physically unplug the Pi
   mid-dose and watch the MCU fall back for real; physically disconnect
   the pH probe and confirm the staleness alert fires on schedule.
6. **Once cycled: stock the chosen fish species at real, conservative
   density** and observe real bioload effects on pH/EC/DO — the actual
   proof-of-concept payoff for full-scale planning.

## What changes when scaling up — and what doesn't

**Carries over directly, no rework:**
- All control logic, the module contract, the safety spec
- The Safety MCU firmware (same code, more instances)
- The capability/hardware registries, inventory, maintenance, assistant
- The device role configs — same watering/fertilizer/pH-dosing roles,
  just more of each

**Recalibrated, not rebuilt:**
- Dosing pulse durations and `dosing_limits` — a 55-gallon pulse and a
  500-gallon pulse are not the same number, but 55 gallons is a much
  closer real analog to full scale than 5 gallons was
- `physics_sim.py`'s drift constants — same mechanism, new numbers
- Fish stocking density/species — bluegill informs the general
  husbandry practice; full scale still plans around tilapia specifically

**Genuinely new:**
- Real greenhouse structure, solar/battery sizing against real load,
  multiple tank cells, tilapia-specific stocking density at full scale

## The recommendation worth calling out explicitly

**Don't decommission the pilot once the full-scale system exists.**
Keep it running permanently as a staging cell — the same role a
staging server plays for software. Any future control-logic change
gets proven on the pilot (which now has real historical data behind
it, not just simulation, AND real fish husbandry experience) before it
ever touches the full-scale tanks. This is the same simulation-first
discipline from `docs/SIMULATION_STRATEGY.md`, just extended one more
tier: sim → scenario tests → pilot hardware → production hardware.

## Software changes needed to represent this

Same `pilot_cell` entry, `config/modules.yaml` — no structural change
needed, the modular registry already supports this without new code.
`ec_target_min`/`ec_target_max` move from "unused until an EC probe
exists (phase 2)" to genuinely relevant once the EC kit above is
bought and wired — still alert-only (no automated EC dosing exists),
same as DO once that kit is added too:

```yaml
# config/modules.yaml — real entry
- id: pilot_cell
  enabled: true
  class: modules.aquaponics_cell.AquaponicsCell
  cell_id: 2
  params:
    ph_target_min: 6.6
    ph_target_max: 7.2
    ec_target_min: 800   # now relevant once the EC kit above is wired in
    ec_target_max: 1500
```

A DO sensor, once bought and registered, is picked up automatically by
`modules/aquaponics_cell.py`'s existing opt-in DO monitoring (warning
below 5.0 mg/L, critical below 3.0 mg/L) — no config change needed
beyond registering the real sensor once it exists.
