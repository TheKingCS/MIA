---
id: K-0473
kind: lesson
title: astral reads the moon in UTC whatever the time zone
status: confirmed
by: claude
created: 2026-11-25T02:26:54+00:00
concerns: core/fishing_times.py, core/sun_moon.py, core/catch_log.py
from: file:core/fishing_times.py, file:core/catch_log.py
---
astral 3.2 moon.elevation(observer, dt) ignores dt.tzinfo and treats the wall time as UTC: local Chicago times put a nearly full moon highest at 5 am, at its own moonset. core/fishing_times.moon_extremes converts each sample with astimezone(timezone.utc) first; sun() and moonrise/moonset take tzinfo and are right. tests/test_fishing_times checks the moon a day before full is highest near midnight. The live check of the new tool also showed log_catch getting length 3 copied from 3 pound and where unknown: core/catch_log drops placeholders and lengths over the cube rule (weight > length^3/400).
