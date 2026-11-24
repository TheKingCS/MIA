---
id: K-0404
kind: implementation
title: His rain gauge in the data logger, counted by the watering answer
status: confirmed
by: claude
created: 2026-11-24T11:49:36+00:00
concerns: core/weather_watch.py, core/assistant_today_actions.py
from: commit:82544c27
---
log_rain (act_within_grant) keeps rainfall off his gauge in the data logger (series weather:rain_gauge, inches; millimeters and words like half an inch read), the same store his meters use, so undo and history come with it. say_watering leads with rain_this_week (the last seven days) against the inch a week the garden wants; freezing still says no watering first.
