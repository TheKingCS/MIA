---
id: K-0357
kind: lesson
title: The second review: an orb word that never showed, and water stored the usual ways
status: confirmed
by: claude
created: 2026-11-23T19:19:36+00:00
concerns: core/tool_loop.py, core/left_off.py, core/preparedness.py, core/unusual.py, core/weather_watch.py, core/weather.py
from: commit:7b8dcb3d
---
A second fresh reviewer (2026-11-23) on the afternoon builds: the orb detail was set only while registry.execute ran (milliseconds, with the orb idle), so it never showed; now a round holds its words from the first lookup until the model follow-up returns (round_doing), and each lookup shows as working. left_off showed the oldest decisions and promises (of_kind is oldest first) and repeated each label; now newest first, without it. preparedness missed 16.9 fl oz bottles and 5-gallon jugs and counted coconut and tonic water; _SIZE and is_drinking_water fix both (careful: stripping every dot broke 16.9 into 16 9). The spending overrun repeated weekly; its key now names the month. Rain falls back to the forecast words; a null in tomorrow no longer drops today. Lesson: test a presence signal against how long the thing really takes, and test units against real product labels.
