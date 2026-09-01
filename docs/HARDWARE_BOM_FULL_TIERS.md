# MIA Homestead — Full Hardware Sourcing, All Three Tiers

Researched 2026-08-31 via four parallel live-sourcing passes (structure
+ climate control + safety switch; tanks/beds/biofilter/plumbing;
sensors/dosing/aeration/power; vertical tower add-on). Every price
below is labeled **Confirmed** (independently live-fetched from a real
vendor page this session) or **Estimated** (a real product class with a
market-rate range, not individually live-fetched — usually because a
live fetch technically failed, e.g. Amazon 500 errors, not because the
product doesn't exist). Never treat an Estimated number as a quote —
confirm at checkout, same discipline as `HARDWARE_BOM_CURRENT.md`.

Three tiers, matching the codebase's own scale:
- **Test** = the existing 5-gallon pilot (`pilot_cell` in
  `config/modules.yaml`) — already fully priced, see `PILOT_VS_SCALE.md`.
- **Small** = one ~500-gallon cell, matching the already-simulated
  `cell_a_aquaponics`.
- **Full-scale** = a real greenhouse structure housing multiple such
  cells.

---

## Test tier — 5-gallon pilot

**~$256 total.** Already fully priced and sourced — see
`docs/PILOT_VS_SCALE.md` for the itemized list and
`drivers/simulator.py --seed-pilot-shopping-list` for the live
purchase-queue version. Not re-priced in this pass; nothing here
changes it.

---

## Small tier — one ~500-gal cell (`cell_a_aquaponics`)

Sizing basis, both cited not assumed: 1:1 fish-tank-to-grow-bed volume
ratio (standard beginner range 1:1–1:2), 2× tank volume/hour
circulation turnover target → **500 gal needs ~1,000 GPH design flow**.
DWC raft culture chosen over a media bed — a 1:1 media bed at 500 gal
needs ~67 cu ft of clay pebbles (~$2,100+), cost-prohibitive at this
scale and not standard practice for the leafy greens this project
already tracks (lettuce, basil).

### Tank / grow bed / biofilter / plumbing

| Item | Price | Status | Source |
|---|---|---|---|
| AquaBundance Modular 500-gal fish tank | $810.00 | **Confirmed** | theaquaponicsource.com |
| DWC raft boards, 6× (48 sq ft) | $249.90 | **Confirmed** | theaquaponicsource.com |
| Raft trough (cut/lined IBC tote) | $180.00 | Estimated | — |
| Bio balls, 900-count | $119.99 | **Confirmed** | aquaticexperts.com |
| Biofilter vessel/barrel | $40.00 | Estimated | — |
| Bulkhead fittings ×5 | $62.85 | **Confirmed** | lifegardaquatics.com |
| PVC pipe/fittings/valves | $100.00 | Estimated | — |
| **Subtotal** | **$1,562.74** | | |

### Sensors / dosing / aeration / controller / power

| Item | Price | Status | Source |
|---|---|---|---|
| pH — Atlas Scientific KIT-101P | $175 | Confirmed (reused from pilot BOM) | atlas-scientific.com |
| EC — Atlas Scientific EC-KIT-1.0 | $230 | Confirmed (reused) | atlas-scientific.com |
| Dissolved oxygen — Atlas Scientific DO Kit | $354.99 | **Confirmed** — *optional at this tier* (see below) | atlas-scientific.com |
| Dosing pumps — 2× EZO-PMP (pH up/down) + 1× EZO-PMP-L (nutrient) | $497.97 | Confirmed | atlas-scientific.com |
| Circulation — Active Aqua AAPW1000, 1000 GPH | $69.65 | **Confirmed** | hydropros.com |
| Aeration — EcoPlus AP-793, 793 GPH / ~1.77 CFM | $81.00 | **Confirmed** | aquaponicsusa.net |
| 8-channel relay + 3× ESP32 Safety MCU | ~$83 | Estimated | — |
| Solar array — 6× Rich Solar MEGA 200W (1,200W) | $1,439.94 | **Confirmed** | richsolar.com |
| Battery bank — 4× LiTime 100Ah 12V LiFePO4 (405Ah target) | $1,343.96 | **Confirmed** | litime.com |
| Charge controller — EPEVER 60A Tracer6415AN, RS485/Modbus | ~$240 | Estimated | amazon.com |
| **Subtotal (with DO)** | **$4,516** | | |
| **Subtotal (without DO)** | **~$4,161** | | |

**DO sensor judgment call:** DO crashes are the leading cause of
catastrophic fish loss. At full-scale, real tilapia stocking density
makes it recommended. At the small tier's lower stocking density,
continuous aeration substitutes adequately — treat as optional here.
**Built and live-verified 2026-08-31**: `modules/aquaponics_cell.py`
now monitors DO (warning below 5.0 mg/L, critical below 3.0 mg/L,
same multi-consistent-reading discipline as pH/EC) if and only if a
DO sensor is actually registered for the cell — a cell without one
stays completely silent rather than alerting on hardware that was
never bought. Alert-only: no automated correction exists beyond the
aerator, which already runs continuously regardless.

### Optional add-on: vertical DWC/NFT tower

Taps the same cell's loop rather than adding a second filtration
system — small lift pump draws from the existing sump, pushes water up
a 4–6" PVC tower past staggered net-pot sites, gravity-returns it to
the same sump. Retrofittable later without disturbing the existing
plumbing (just a tee into the sump return + its own pump) — **doesn't
need to be decided before building the flat bed above.**

| Item | Price | Status |
|---|---|---|
| 4" PVC pipe (10 ft) + caps/elbow/drilling | ~$92–97 | Confirmed pipe ($77, homedepot.com) + estimated hardware |
| 2" net pots, 50-pack | ~$15–20 | Confirmed range |
| Growing medium | ~$15–20 | Estimated |
| Lift pump, 400 GPH / ~6 ft head | ~$15–25 | Confirmed range |
| Tubing/manifold/fittings | ~$10–15 | Estimated |
| **Per tower (~16 sites)** | **~$135–160** | |

Yield: multiple sources converge on 3–8× the leafy-green yield per
square foot of floor space vs. a flat bed (one source: 13.8× for
lettuce). Tradeoff: a second pump = a second failure point, tighter
NFT root-zone tolerances vs. a media/DWC bed's buffering.

### Small-tier total

| | Total |
|---|---|
| Tank/bed/biofilter/plumbing + sensors/dosing/power, **without DO** | **$5,723.74** |
| Same, **with DO** | **$6,078.74** |
| + optional vertical tower | **+$135–160** |

---

## Full-scale tier — real greenhouse, multiple cells

### Structure (real, buyable kits — both price-confirmed)

| Option | Footprint | Price | What's included |
|---|---|---|---|
| **Grandio Summit 12×20** | 240 sq ft | **$6,899.00** confirmed (sale price, ends Aug 31 2026) | 1.6mm powder-coated aluminum frame, 10mm twin-wall polycarbonate, sliding doors, 10 roof vents, gutters, drain/snow-load/anchor kits. No foundation — needs a pad. |
| **Bootstrap Farmer 12' hoop house, 20'** | 240 sq ft | **$528.99** confirmed | Spring-lock wire/channel, 4-yr 6mil plastic, connectors, hardware, ground posts. **Lumber/top rail excluded** — real added cost not in this price, buy locally. |

Same footprint, ~13× price gap: Grandio is a permanent rigid structure
ready to mount equipment on; the hoop house is a cheaper plastic tunnel
needing your own lumber framing.

**Sizing conflict — resolved, N=2 decided (2026-08-31):** at N=3, each
cell's DWC bed alone is 48 sq ft (3 × 48 = 144 sq ft), plus tank +
biofilter footprint + walkways — realistically 280–330 sq ft, more
than either 240 sq ft structure priced here. Rather than chase a
bigger, unpriced structure to justify N=3, **going with N=2 cells**,
which comfortably fits both real 240 sq ft kits above. Per-cell
independent life support (the reason N>1 was recommended at all —
isolating one cell's failure/disease from the others) still holds at
N=2; it just isn't N=3. If the greenhouse footprint grows later
(bigger kit, second bay), a 3rd cell is a straightforward add — same
per-cell pattern, not a redesign.

### Climate control — real software gap, stated plainly

**Resolved 2026-08-31** — was a real gap when this doc was first
written (schema forward-declared `'heater','fan'` as valid
`actuators.type` values, but zero code implemented either). Now built:
`modules/climate_control.py` + `config/devices/roles/climate_mcu.yaml`,
live-verified against the running system (safety fallback forced
heater off/fan on during a real stale-sensor condition, then a genuine
92°F reading correctly triggered a temp-driven `auto_control` decision).
This hardware is automatable today, not manual-only.

| Item | Price | Status |
|---|---|---|
| Exhaust fan + shutter, 24", 4450 CFM | $159.99 | **Confirmed**, bootstrapfarmer.com |
| Thermostatic propane heater, 30,000–60,000 BTU | $150–$400 | Estimated (2 live-fetch attempts failed technically — Amazon 500, Parts-Express empty — not a nonexistent product) |

### Optional monitoring/automation add-ons — all now have real control code (2026-08-31)

None of these were in any tier's original BOM above. All four were
found via a schema audit (`sensors.type`/`actuators.type` values the
schema forward-declared with zero implementing code) and have since
been built and live-verified — see `CLAUDE.md`'s current-state summary
for what each one actually does. Listed here so the option is visible
alongside the rest of the real pricing, not because any tier requires
them.

| Item | Price | Status | What it enables |
|---|---|---|---|
| Dissolved oxygen kit (Atlas Scientific) | $354.99 | Confirmed | `modules/aquaponics_cell.py` — alert-only DO monitoring, see small-tier sensors table above |
| Inline flow sensor (hall-effect, e.g. YF-S201) | ~$10 | Estimated | `core/circulation_monitor.py` — detects a pump commanded on but not actually moving water |
| Lux/light sensor (e.g. BH1750 I2C) | ~$6 | Estimated | `modules/climate_control.py` — supplemental grow-light triggering |
| Grow light fixture, relay-switched | ~$40 | Estimated | same — on/off actuator, no hazard either way |
| CO2 sensor (NDIR, e.g. MH-Z19) | ~$25 | Estimated | `modules/climate_control.py` — CO2 enrichment triggering + a real human-safety ceiling check (OSHA PEL) |
| CO2 injector/regulator valve | ~$35 | Estimated | same — short cooldown-limited pulses only, never continuous. Does NOT include a CO2 source tank/generator, not priced here |

Every "Estimated" price above is a typical current market rate for the
part class, not independently live-fetched this session — confirm at
checkout, same discipline as the rest of this doc.

### Physical safety kill switch

Per `docs/SAFETY_SPEC.md`'s local-override requirement, independent of
Pi/MCU.

| Item | Price | Status |
|---|---|---|
| Heavy-duty DPST toggle switch, 20A/125V | $8–$15 | Estimated (same 2 live-fetch failures as the heater) |

### Tank / bed / biofilter / plumbing — per cell, ×N

Same $1,562.74/cell as the small tier, plus one shared water top-off
manifold across cells (~$150, estimated). Per-cell independent life
support (own grow bed + biofilter + plumbing) recommended over a
shared biofilter — one cell's failure or disease outbreak doesn't
cascade to the others.

| Cells | Total |
|---|---|
| **N=2 (decided)** | **$3,275.48** |
| N=3 | $4,838.22 |
| N=4 | $6,400.96 |

### Sensors / dosing / aeration / power — per cell, ×N, plus shared power system

Continuous load/cell: circulation (92W) + aeration (18W) + 3 MCUs
(~3W) + sensor polling (~2W) = **115W/cell**, plus one shared Pi 5 + AI
HAT (~20W total, not per-cell).

| | Per cell | N=2 | N=3 | N=4 |
|---|---|---|---|---|
| Sensors (incl. DO — required at this tier) | $760 | $1,520 | $2,280 | $3,040 |
| Dosing pumps | $498 | $996 | $1,494 | $1,992 |
| Aeration/circulation | $151 | $302 | $453 | $604 |
| Relay + MCUs | ~$83 | ~$166 | ~$249 | ~$332 |

**Whole-greenhouse power system** (sized to total continuous load, not
per-cell — 4 peak-sun-hrs conservative, 0.75 derate):

| | N=2 (270W cont.) | N=3 (365W cont.) | N=4 (460W cont.) |
|---|---|---|---|
| Daily energy | 6.48 kWh | 8.76 kWh | 11.04 kWh |
| Solar array (Rich Solar MEGA 200W, $239.99/panel confirmed) | 11 panels, $2,639.89 | 15 panels, $3,599.85 | 19 panels, $4,559.81 |
| Battery bank (LiTime 100Ah 12V, $335.99/unit confirmed, 1.5-day autonomy) | 9× 100Ah, $3,023.91 | 11× 100Ah, $3,695.89 | 13× 100Ah, $4,367.87 |
| Charge controller (EPEVER 60A, RS485/Modbus, estimated) | ~$240 | ~$240 | ~$240 |

**⚠️ Charge-controller bus-voltage flag:** at 12V, array wattage blows
past any single real controller's rated amperage (e.g. 3,000W/12V =
250A at N=3). Recommend stepping the battery bus to **48V for
full-scale**, which fits one EPEVER 60A controller (3,000W/48V =
62.5A). Total battery cost/Ah is unchanged — but the pack must be wired
in series strings for 48V, not simple 12V-parallel as the per-unit
price above implies. Resolve this before wiring, not after.

### Full-scale totals (N=2 decided, sensors include DO)

| | Grandio structure | Bootstrap Farmer hoop house* |
|---|---|---|
| Structure | $6,899.00 | $528.99 |
| Climate control (fan + est. heater midpoint) | ~$435 | ~$435 |
| Safety switch (est.) | ~$12 | ~$12 |
| Tank/bed/biofilter/plumbing (N=2) | $3,275.48 | $3,275.48 |
| Sensors/dosing/aeration/relay (N=2) | $2,984.00 | $2,984.00 |
| Power system (N=2) | $5,903.80 | $5,903.80 |
| **Total** | **~$19,509** | **~$13,139*** |

\* Hoop house excludes lumber framing cost, real but not individually
priced this pass — expect several hundred dollars more.

Optional vertical towers add ~$150/cell (~$300 at N=2) on top of
either total — no rework needed, bolt-on later.

### Open decisions before ordering anything at full-scale

1. **Charge controller bus voltage** — even at N=2, full array wattage
   (2,200W) at 12V draws ~183A, past any single real controller; 48V
   (~46A) is needed and recommended. Changes battery series/parallel
   wiring from a naive per-unit price sum.
2. ~~Fan/heater control code doesn't exist yet~~ — **built and live-verified
   2026-08-31**, see `modules/climate_control.py`: heater for low temp,
   fan for high temp or high humidity, safe defaults matching the
   dosing-pump/aeration precedent (heater off, fan on, when data can't
   be trusted). No longer a gap — this hardware is automatable today.
