# MIA Homestead — Safety Layer Specification

## Purpose
This system must default to a SAFE, STABLE state under any failure condition —
sensor dropout, network loss, Pi crash, power interruption, or software bug.
"Safe" always means: fish and plants survive, nothing over-doses, nothing floods,
nothing runs dry. Optimal growth is a secondary goal to survival.

## Architecture principle: two-tier control

- **Pi (brain)**: runs control logic, logging, dashboard sync, ML/optimization.
  Allowed to be wrong, slow, or offline without endangering the system.
- **Safety MCU (spinal cord)**: a separate microcontroller (ESP32) that directly
  drives relays/pumps. Runs a hardware watchdog. If it stops hearing from the
  Pi within a timeout window, it ignores the Pi entirely and falls back to
  hard-coded safe defaults below. The Pi cannot be the single point of failure
  for anything that could kill livestock or crops.

## Sensor staleness rules

| Condition | Action |
|---|---|
| Sensor reading not updated in > 10 min | Flag stale, stop using for control decisions |
| Sensor reading out of physically plausible range (e.g. pH < 0 or > 14) | Discard reading, flag sensor fault, alert |
| >2 consecutive sensors on same parameter disagree beyond tolerance | Alert, do not average — flag for manual check |
| All sensors on a cell stale | Freeze all dosing/actuation for that cell, maintain aeration/circulation only |

## Dosing rules (hard limits, enforced in MCU firmware, not just Pi software)

- **Never dose based on a single reading.** Require 3 consistent readings over
  a minimum interval before triggering a correction.
- **Max dose per event** and **max dose per rolling 24h window**, defined per
  chemical, per cell, in `dosing_limits` table. MCU firmware enforces the hard
  ceiling independent of what the Pi requests.
- **Minimum interval between doses** of the same type per cell (prevents
  oscillation/overcorrection loops).
- **Dosing pumps default OFF.** Every dosing action is an explicit timed pulse,
  never a continuous "on" state. A stuck-open valve should be structurally
  impossible for chemical dosing.

## Power failure behavior

- **Aeration/oxygenation is the highest priority load.** Fish suffocate faster
  than plants die of anything else. Aeration gets battery priority over
  dosing, lighting, or non-critical sensors.
- **Water circulation pumps**: second priority. Biofilter needs flow to avoid
  ammonia spikes.
- **On low battery SOC** (configurable threshold, start at 20%): shed dosing,
  non-critical sensors, and dashboard sync first. Aeration and circulation
  are last to be shed.
- **On full power loss with no battery reserve left**: system should have
  physical/passive fallback where possible (e.g. air-stone driven by battery-
  backed micro pump sized for aeration only, separate from main system power).

## Alerting escalation

1. **Info**: logged only (e.g. routine dose administered)
2. **Warning**: pushed to dashboard + daily digest (e.g. sensor drift detected,
   nearing dosing limit)
3. **Critical**: immediate push notification/SMS to primary + secondary contact
   (e.g. sensor fault with no healthy backup, water level critical, power
   below reserve threshold, safety MCU failed to hear from Pi)
4. **Dead-man's check-in**: if no human acknowledges ANY alert or dashboard
   view within a configurable window (default 72h), escalate critical-level
   alert to secondary contact even absent an active fault — surfaces the
   "what if something's wrong and no one's watching" case.

## Manual override

- Physical local override switch at the greenhouse (kill dosing, force
  aeration on) independent of the Pi and any software state.
- Dashboard-level override always available but never required for the
  system to remain safe — the whole point is it works without you looking.

## Open items to define once hardware is selected

- Exact dosing limit values per chemical (pH up/down, nutrient concentrate)
- Battery SOC thresholds calibrated to actual battery capacity once sized
- MCU-to-Pi heartbeat timeout value (start proposal: 60s, tune after testing)
