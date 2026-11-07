---
id: K-0071
kind: implementation
title: Power on the web
status: confirmed
by: claude
created: 2026-11-07T17:38:45+00:00
concerns: core/web_power.py, core/power_actions.py, web/power.js
from: dec:DEC-0125, dec:DEC-0113
---
Power had no phone screen (parity gap power:phone, DEC-0125). core/web_power.py assembles it: this device's battery from core/power_manager.py, and each energy source tracked by hand (core/energy_manager.py) with its latest reading per meter, how long ago it was, and a meter for a percent reading (amber under LOW_PERCENT, sorted first: needs you). Changes are core/power_actions.py: energy_source.add/edit/delete from one Record, and energy.reading (a reading into the Data Logger through log_energy_reading). Served at /api/power; web/power.html and power.js draw it. The parity decision for power:phone is removed and docs/PARITY.md edited by hand to match (its generator needs PySide6; run python -m core.parity on the PC to confirm).
