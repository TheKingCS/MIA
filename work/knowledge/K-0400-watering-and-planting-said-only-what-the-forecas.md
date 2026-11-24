---
id: K-0400
kind: debugging
title: Watering and planting said only what the forecast and calendar really hold
status: confirmed
by: claude
created: 2026-11-24T11:02:40+00:00
concerns: core/planting_now.py, core/weather_watch.py, core/weather.py
from: commit:f98c162c, commit:cb842196
---
A twentieth fresh review: watering said water deeply when tomorrow's words said heavy rain (no chance given), said no rain for a 50% chance or no tomorrow at all, gave summer advice in snow, read only the weather right now (core/weather.card now keeps today_words), and took houseplants and the chickens. Planting: a frost saved with its year never moved to next spring (parse_day keeps a given year), crops matched by substring (peanuts were peas, acorn squash corn, peppermint peppers; now whole words, longest first, with what he'd call them), a late seed start wasn't said, and resown crops were said past in June.
