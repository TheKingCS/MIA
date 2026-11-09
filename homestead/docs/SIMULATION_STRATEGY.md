# MIA Homestead — Simulation Strategy

## Why simulate before buying hardware

Every dollar spent on a sensor or pump is a bet that the control logic
around it is already right. Simulation lets you find the bugs, tune the
thresholds, and stress-test the failure modes for free, before any of
that logic is anywhere near a real fish tank. This isn't a demo — it's
the actual QA process for a system whose whole premise is "works
correctly when no one's watching."

## The four tiers

### Tier 1 — Logic simulation (built)
`drivers/simulator.py`. Random-walk sensor data, just enough realism to
prove the control loop, alerting, and assistant all function end-to-end.
Good for: initial development, UI/assistant testing, CI smoke tests.
Not good for: telling you whether a dosing decision is actually correct.

### Tier 2 — Physics-informed closed-loop simulation (building now)
`drivers/physics_sim.py`. The simulator now models real aquaponics
cause-and-effect: nitrification naturally drifts pH down over time (a
real, well-documented phenomenon — this is *why* pH-up dosing is
periodically needed in every real system), evaporation slowly
concentrates EC and drops water level, and — critically — a dosing
pulse the control loop issues actually moves the simulated pH/EC in the
right direction by a physically plausible amount.

This is what makes it a genuine test: if the control loop's dosing logic
is wrong (too weak, too strong, wrong direction, oscillating), Tier 2
will show that as the simulated system failing to stabilize, the same
way a real tank would drift out of range or overcorrect.

### Tier 3 — Scenario / fault-injection test harness (building now)
`scenarios/scenarios.py`. Scripted failure scenarios that specifically
target the safety spec's claims: sensor dropout, power loss, disagreeing
readings, a real pH crash. Each scenario asserts an expected system
response (alert raised, correct commands issued, dosing correctly
withheld). This is the closest thing to a regression test suite for the
safety-critical parts of the system — anytime control logic changes,
these scenarios should be re-run before it goes near real hardware.

### Tier 4 — Spatial digital twin (now a live feature, not a dev tool)
`config/layout.json` + `viewer/digital_twin.html`. Every physical object
in the layout — a tank, the power array, the help beacon — declares a
`linked_module_id`. `viewer/export_state.py` looks up that module's open
alerts and colors/glows the EXACT object, not just the whole cell:
green/idle when fine, amber and steady for a warning, red and pulsing
for critical — a literal "go here" signal for a person walking into
the greenhouse, with the actual reason listed in a HUD panel. `main.py`
re-exports this every control cycle automatically, so it's always
current — you don't run anything by hand to keep it live.

## The process going forward

1. **Any new control logic** (a new dosing rule, a new module type) gets
   built and proven against Tier 1/2 simulation first — never designed
   directly against real hardware assumptions.
2. **Any safety-relevant change** gets a new or updated Tier 3 scenario
   before being considered done. If you can't write a scenario that
   proves the behavior, the behavior probably isn't well-defined yet.
3. **Hardware gets purchased against a simulation-validated spec.**
   E.g., once Tier 2 simulation tells you what dosing pulse duration
   and interval actually stabilizes pH under realistic drift, that's the
   number you shop for a dosing pump against — not a guess.
4. **Tier 4 updates as real measurements come in** — it's a living
   spatial reference, not a one-time artifact.

## What this deliberately does NOT try to do

- No fluid dynamics, no real chemistry engine — the physics model is
  intentionally simple (linear drift + proportional dosing effect), just
  enough to validate control logic direction and rough magnitude, not to
  predict exact real-world numbers. Real calibration happens once real
  sensors exist.
- No CAD/structural simulation — greenhouse structural design stays in
  FreeCAD/your existing CAD workflow. `layout.json` only captures enough
  geometry for a status view, not for fabrication.
