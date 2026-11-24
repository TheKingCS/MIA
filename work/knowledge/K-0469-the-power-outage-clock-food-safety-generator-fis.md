---
id: K-0469
kind: implementation
title: The power outage clock: food safety, generator, fish, hens and well from when it went out
status: confirmed
by: claude
created: 2026-11-24T23:42:32+00:00
concerns: core/outage.py, core/outage_actions.py
from: file:docs/future/JARVIS_BRAINSTORM.md
---
core/outage.py keeps outage.since (device setting); when_said reads at 6 am / 6:30 pm (a later hour is yesterday) / 2 hours ago; food_lines uses FoodSafety.gov guidance (fridge 4 h closed, full freezer 48 h, half 24 h; afterwards perishables above 40 F over 2 h go, freezer food with ice crystals or at 40 F or colder can be refrozen); status adds power_ready.say and lines only when they apply (greenhouse taken over: aeration first; a flock: water; a well asset: fill jugs). Power page card and outage.start/end actions; tool power_outage with state out/status/back. Live model: the freezer question first went to get_power_status; leading the description with the food-safety question fixed it; neighbours list_pantry and get_power_status checked.
