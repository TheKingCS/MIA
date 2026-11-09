# MIA Homestead — Pilot 3D Visualization Brief

One consolidated, accurate source for anything building a 3D visual of
the pilot build (or the full greenhouse) — written 2026-09-03 so a
tool like Claude Design doesn't have to piece this together from
`config/layout.json`, `docs/PILOT_VS_SCALE.md`, and five product pages
itself, and doesn't have to guess at part sizes. Every number below is
tagged **real** (measured/confirmed) or **placeholder** (a stand-in,
not yet true) — don't blend the two categories when generating a scene.

## What already exists: a live schematic 3D twin

`viewer/digital_twin.html` (Three.js) already renders a real-time 3D
scene of this layout, driven by `config/layout.json` + live sensor
state — simple colored boxes for tank/bed/site footprint that glow red
on a real fault, for fast "go here" fault-locating. It's intentionally
abstract, not a realistic render. Anything built from this brief should
be a complementary, richer visual — not a duplicate of that pipeline —
and should stay spatially consistent with it (same relative positions)
so the two don't drift into different mental models of the same site.

## Site layout — REAL positions, PLACEHOLDER full-greenhouse footprint

From `config/layout.json` (coordinates in feet, `x`/`z` plane):

| Object | Position | Status |
|---|---|---|
| Full greenhouse site footprint | 25ft × 25ft | **PLACEHOLDER** — explicitly flagged in the file itself as not yet real; update once real greenhouse dimensions exist |
| Cell A (future full-scale cell) | (0, 0) | Placeholder — no physical cell built yet |
| **Pilot Bucket** | (-12, 0) | **Real position choice** — "a desk/shelf position is a valid position for this one, not a greenhouse slot" (the pilot deliberately doesn't need a greenhouse to exist) |
| Solar/power array | (15, -5) | Placeholder |
| Entrance help beacon | (0, 12) | Placeholder (no beacon hardware purchased yet) |

**Implication for a 3D visual**: a realistic render of "the pilot" (bucket
+ tray + electronics on a shelf/desk) can be built from real numbers today.
A realistic render of "the greenhouse" cannot yet — its footprint is a
stand-in, not a measurement. Recommend building the pilot scene first,
and treating any full-greenhouse render as explicitly conceptual/illustrative
until real site dimensions exist.

## Pilot build — REAL confirmed dimensions

| Component | Real dimensions | Source |
|---|---|---|
| Pilot tank (5-gal bucket) | 1.3ft × 1.3ft × 1.2ft (W×L×H) | `config/layout.json` |
| Pilot grow tray | 1ft × 1.5ft, 1.5 sqft | `config/layout.json` |
| Grow media | Net pots (2–4), no media bed | `PILOT_VS_SCALE.md` |

## Approved parts list — real sourcing, dimensions where confirmed

All 8 items below are **approved** in the app's order queue (2026-09-02,
~$262.88 total) — real product URLs, prices confirmed direct from the
seller where noted, otherwise a stated Amazon-listing estimate (never
fabricated). Physical dimensions are NOT yet captured locally for most
of these — pull them from the product page linked, don't guess:

| # | Part | Real price | Confirmed? | Product page (real dimensions live here) |
|---|---|---|---|---|
| 1 | Atlas Scientific KIT-101P pH kit (circuit + probe + carrier board + calibration solution) | $174.99 | Confirmed, atlas-scientific.com | https://atlas-scientific.com/kits/ph-kit/ |
| 2 | Adafruit HUZZAH32 ESP32 Feather (pre-soldered) | $20.95 | Confirmed, adafruit.com | https://www.adafruit.com/product/3591 |
| 3 | DS18B20 waterproof temp probe | $10.95 | Confirmed, sparkfun.com | https://www.sparkfun.com/temperature-sensor-waterproof-ds18b20.html |
| 4 | 4-channel 5V relay module (DIYables) | ~$10.00 | Estimate | https://www.amazon.com/DIYables-4-Channel-Arduino-ESP8266-Raspberry/dp/B0BXKKYH5C |
| 5 | 12V DC peristaltic dosing pump (INTLLAB) — pH-up only | ~$12.00 | Estimate | https://www.amazon.com/INTLLAB-Peristaltic-Flowrate-Aquarium-Analytical/dp/B07MTBV5RR |
| 6 | Aquarium air pump + airstone kit (Pawfly), 15-40 GPH | ~$12.00 | Estimate | https://www.amazon.com/Pawfly-Aquarium-Aerator-Airline-Accessories/dp/B0CMT6G4KM |
| 7 | Submersible circulation pump (AQUANEAT), 80 GPH | ~$15.00 | Estimate | https://www.amazon.com/AQUANEAT-Submersible-Fountain-Aquarium-Hydroponics/dp/B0BJJBK746 |
| 8 | Heavy-duty DPST toggle switch, 20A/125V (safety override) | ~$6.99 | Estimate | https://www.amazon.com/DPST-Heavy-Duty-Toggle-Switch/dp/B016CJBQL4 |

**Skipped for the pilot on purpose** (real trims, not oversights — carries
over at full scale, not part of this visual): EC/nutrient dosing, a second
(fertilizer) MCU, PIR/beacon hardware, all power-monitoring hardware,
pH-down pump (pH-up only to start).

## Real wiring/functional relationships (for an accurate, not just pretty, scene)

- **1 ESP32 (#2)** is the Safety MCU — the brain that talks to the Pi and
  is the final safety authority. Everything else wires into it.
- **1 relay module (#4)** — 4 channels, driven by the ESP32, switches the
  pumps below.
- **pH probe (part of #1)** sits in the tank, wired to the ESP32.
- **Temp probe (#3)** — waterproof, submerged in the tank, wired to the
  ESP32.
- **Dosing pump (#5)** — pH-up only, output tube into the tank, driven by
  one relay channel.
- **Air pump + airstone (#6)** — always-on aeration, airstone submerged
  in the tank, driven by one relay channel (or wired directly always-on,
  per `PILOT_VS_SCALE.md`).
- **Circulation pump (#7)** — submerged in the tank, always-on, driven by
  one relay channel.
- **Override switch (#8)** — wired in series with the dosing pump's relay
  channel specifically (per `SAFETY_SPEC.md`: "kill dosing, force
  aeration on, independent of the Pi and any software state") — this is
  a hardware-only safety path, not something the ESP32 or Pi can
  override in software. Physically mount it somewhere a human can reach
  it fast, not tucked away.
- **Pi 5** (not in the shopping list — already owned) runs the control
  loop and talks to the ESP32 over USB serial (`drivers/mcu_serial.py`).

## Honest gaps this brief does NOT resolve

- No real physical dimensions for parts #4-8 are captured anywhere in
  this repo — only real product URLs. A 3D tool building accurate
  part-scale geometry needs to fetch those from the linked pages itself.
- No real photos exist of the assembled pilot (nothing has been
  physically built yet) — everything here is planned/sourced, not built.
- The full greenhouse structure has no real design source at all in
  this repo (`config/layout.json`'s own `_meta` says structural design
  is meant to live in a separate CAD workflow, e.g. FreeCAD — none
  exists here yet).
