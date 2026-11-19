---
id: K-0313
kind: implementation
title: What MIA learned on her own is listed with evidence and reset one at a time
status: confirmed
by: claude
created: 2026-11-19T02:56:37+00:00
concerns: core/learned.py, core/communication_gate.py, core/homeostasis.py
from: commit:1fe9bbcc, dec:DEC-0282
---
LS-10 (DEC-0282): core/learned.habits() gathers the gate's learned paces (gate.pace, skipping 'still learning'), the breaks she took herself (gate.inferred_breaks, never one he asked for with mute) and answer styles learned only from A/B picks (StyleBook.learned_only; choose() records rejected='' and is his own). learned.reset relearns that one (gate.relearn keeps a per-topic time before which sends don't count; resume; StyleBook.relearn). Homeostasis.spend() counts deferrable work's seconds a day (scheduler.on_ran, the daily check loop) against homeostasis.daily_budget_minutes.
