---
id: K-0398
kind: implementation
title: Watering advice from the kept forecast, ending with the soil check
status: confirmed
by: claude
created: 2026-11-24T10:44:20+00:00
concerns: core/weather_watch.py, core/assistant_today_actions.py
from: commit:424b0723
---
core/weather_watch.watering (pure) reads core/weather.card's forecast: today's words (rain, showers, drizzle, thunder) say skip, tomorrow's rain chance at RAIN_LIKELY or more says hold off, a high of 85 F (29 C) or more with no rain says water deeply in the morning at the base; every answer ends with the finger test (dry 1 to 2 inches down) and about an inch a week, since the forecast can't see his soil. should_i_water is read-only.
