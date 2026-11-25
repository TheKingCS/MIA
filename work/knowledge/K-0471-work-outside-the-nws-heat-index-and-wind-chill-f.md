---
id: K-0471
kind: implementation
title: Work outside: the NWS heat index and wind chill from the hourly forecast
status: confirmed
by: claude
created: 2026-11-25T01:36:11+00:00
concerns: core/outdoor_work.py, core/weather.py
from: file:core/outdoor_work.py, file:docs/future/JARVIS_BRAINSTORM.md
---
core/outdoor_work.py: weather.read now keeps the first 48 hourly temperature/humidity/wind values (the request asks for them). heat_index is the Rothfusz regression with the NWS adjustments (simple form below 80 F); wind_chill is the 2001 NWS formula (50 F or colder, wind over 3 mph); levels 80/90/103/125 F and frostbite minutes 30/10/5 at -18/-33/-48 F. Only 6 am to 8 pm is read; Celsius forecasts are converted in and out. Live model (qwen2.5:14b): named safe_to_work_outside, wind chill questions went to get_weather; named wind_chill_and_heat_index, too hot to work went to should_i_water; work_outside_wind_chill_heat_index passed 21 of 21 with neighbours, and get_weather says wind chill is not its job.
