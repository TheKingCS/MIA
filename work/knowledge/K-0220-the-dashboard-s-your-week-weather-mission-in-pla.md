---
id: K-0220
kind: implementation
title: The Dashboard's Your Week, weather, mission in play and Agent Activity
status: confirmed
by: claude
created: 2026-11-11T08:19:33+00:00
concerns: core/today.py, core/weather.py, core/agent_activity.py, core/web_surfaces.py, web/welcome.js, core/assistant_today_actions.py
from: dec:DEC-0153, file:core/weather.py, file:core/agent_activity.py
---
DEC-0153 (Zac, 2026-11-11). Your Week is core/today.week_days: today's list as Today has it, then for each of the next six days the TODAY items of the dated sources only (WEEK_SOURCES: calendar, bills, maintenance, tasks, birthdays, health; alarms ring daily, the pantry and inbox aren't dated), each thing once; no second list of due things exists. The weather is core/weather.py, MIA's first weather source: the person names a town (the action weather.place, Open-Meteo geocoding, kept as the person setting weather.place so Undo works), the forecast comes from Open-Meteo (no key), Fahrenheit only where it's used. A page never waits on the internet: a forecast is kept 30 minutes and refreshed on a daemon thread of its own (the one network wait, scoped to that module), and a test run never goes online unless it hands in fetch. The mission in play is the most recently worked active mission with its first unfinished objective (Missions still owns it). Agent Activity is core/agent_activity.py: her own undoable changes (by MIA, not you), what the communication gate held back today, screens she made, and for the owner only (work_dashboard.allowed) the Council's and the work log's latest, the log's UTC times turned to local. By voice in the today domain: get_week, get_weather, set_weather_place.
