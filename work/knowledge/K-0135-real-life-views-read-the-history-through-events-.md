---
id: K-0135
kind: implementation
title: Real-life views read the history through events_for
status: confirmed
by: claude
created: 2026-11-08T16:21:56+00:00
concerns: core/party.py, core/life_events.py, tests/test_environment.py
from: dec:DEC-0137, commit:3d102292
---
DEC-0137's isolation: every real-life view (the Life State, the Chronicle, the glasses' feed, the seasons, the Operating Journal, the Memory Vault, creations) reads life events through events_for(), which is real-only by default. The one module reading a LifeEventLog directly, the household leaderboard (core/party.py _wins), now skips non-real events with environment.is_real. tests/test_environment.py fails on a new core module that constructs a LifeEventLog and calls .all_events() without is_real.
