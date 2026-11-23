---
id: K-0350
kind: implementation
title: The weather read against his garden plans and flock
status: confirmed
by: claude
created: 2026-11-23T17:58:18+00:00
concerns: core/weather_watch.py, core/background_jobs.py, core/stop.py, core/message_reasons.py
from: dec:DEC-0287
---
core/weather_watch.py (brainstorm 2.2): crops_now reads confirmed garden plans through garden_plans.schedule (in the ground from the day out to three weeks past first harvest; hardening off from the harden-off day to the day out); concerns() compares tomorrow's low (tonight's coldest hour is early morning, and Open-Meteo's daily minimum for today includes hours already past) with fixed thresholds in F (frost 34 for tender crops, from the NWS frost advisory band; hard freeze 28 for half-hardy; 45 for hardening seedlings; flock heat 90, water 32), converting a Celsius forecast. The daily check fetches the forecast itself (card with fetch) because the in-process cache may be empty once a day; never from a test run. It sits in stop.CHECKS_THAT_WAIT since it goes online. Every new daily check must also be named in stop.py's lists, an app manifest's runtime.background and message_reasons.REASONS (three tests say so; Q-114's check missed them first).
