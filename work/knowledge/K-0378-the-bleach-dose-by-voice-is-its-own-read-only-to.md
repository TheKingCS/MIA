---
id: K-0378
kind: implementation
title: The bleach dose by voice is its own read-only tool
status: confirmed
by: claude
created: 2026-11-24T07:28:25+00:00
concerns: core/assistant_today_actions.py, core/eng_calcs.py
from: commit:10478294
---
bleach_for_water (today domain, observe) reads the water (gallons, liters, quarts) and any strength from what he said and runs eng_calcs water_bleach, the EPA dose in code; with no strength it gives both common ones (6 and 8.25 percent) to check against the label. Before, the calculator was reachable only through the specialists worksheet, so how much bleach to purify 5 gallons went to the library or the model memory.
