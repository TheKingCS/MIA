---
id: K-0392
kind: implementation
title: A hatch is a mission with dated steps
status: confirmed
by: claude
created: 2026-11-24T09:47:50+00:00
concerns: core/hatch_tracker.py, core/assistant_goods_actions.py
from: commit:8b03cba9
---
core/hatch_tracker.py: hatch.start (act_within_grant) makes one mission from BIRDS' fixed incubation days (candle, lockdown three days before hatch, hatch day), each step dated from the day set, and keeps the bird and day in config (MAP_KEY) so hatch_status can say the day and what's next. Guided steps live in Missions (Zac, 2026-11-09). Registered from register_goods_actions (flock domain) so the PC and the phone both have it.
