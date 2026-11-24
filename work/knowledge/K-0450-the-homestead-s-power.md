---
id: K-0450
kind: implementation
title: The homestead's power
status: confirmed
by: claude
created: 2026-11-24T18:49:11+00:00
concerns: core/power_picture.py, core/assistant_energy_actions.py, core/project_ripple.py
from: dec:DEC-0153
---
Phase A3 of docs/future/SMART_AG_PLAN.md. core/power_picture.py: essentials from power.loads (set_power_load) else TYPICAL said as typical (well pump, aquaponics air and water pumps, fridge, freezer, lights: 10.66 kWh a day), the battery (power.battery_kwh via set_preparedness) in hours on them, solar sources' kWh readings over 30 days against them, and the generator line from power_ready. Found on the way: get_power_status is this computer's own battery, and the project picture had used it as the homestead's power; it now reads power_picture.
