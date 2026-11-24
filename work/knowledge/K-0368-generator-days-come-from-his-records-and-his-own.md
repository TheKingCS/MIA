---
id: K-0368
kind: implementation
title: Generator days come from his records and his own burn rate
status: confirmed
by: claude
created: 2026-11-24T05:48:42+00:00
concerns: core/power_ready.py, core/preparedness.py, core/assistant_today_actions.py
from: commit:b1b2a7c9
---
core/power_ready.py reads fuel from inventory and pantry by whole word (gas cans, off-road diesel, kerosene, propane; never a gas grill, gas mask, gas bill or natural gas), in gallons from a unit or a size in the name, propane by the pound at about 4.24 lb a gallon; what has no readable size is named, never guessed. Days = gallons / (burn rate x hours a day). The burn rate is his generator manual figure, never assumed: without it she asks. set_preparedness (act_within_grant) sets people, target days and the generator, each range-checked; before it nothing could set prepared.people or prepared.target_days at all.
