---
id: K-0490
kind: lesson
title: The sixth review: a safety exception on a bare word silenced real emergencies
status: confirmed
by: claude
created: 2026-11-25T13:37:39+00:00
concerns: core/first_aid_floor.py, core/tool_loop.py, core/assistant_plan_actions.py, core/assistant_turn.py
from: commit:91a78048, commit:fcdca1b9
---
The first-aid drills added a practice exception to the emergency floor on the bare words practice and drill, and real emergencies (she choked at soccer practice and cannot breathe; I cut my hand with the drill and it will not stop bleeding) got nothing. An exception to a safety floor must be as narrow as the thing it lets through: now only a drill actually asked for (core/drills.requested), and a test lists the panicked phrasings. The same review found new code routes taking statements and commands (I built 200 feet of fence; remind me to buy 14 days of water) and a prompt replacement clobbering good model arguments: a route needs a question and its own exclusions, and a replacement only the junk it was made for.
