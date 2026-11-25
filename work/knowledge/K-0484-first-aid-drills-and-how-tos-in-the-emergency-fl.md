---
id: K-0484
kind: implementation
title: First aid drills and how-tos, in the emergency floor's own words
status: confirmed
by: claude
created: 2026-11-25T12:03:50+00:00
concerns: core/drills.py, core/first_aid_floor.py, core/conversation_modes.py, core/assistant_turn.py
from: commit:7dd5e48f
---
Two survival drills (core/drills.py: deep_cut, choking) and a code answer for a first-aid how-to (core/first_aid_floor.teach, core/assistant_turn._first_aid_reply), all in the floor's own Red Cross and AHA words, so practice never teaches what an emergency reply wouldn't say, and no medicine doses. Went wrong first: "give me a choking drill" tripped the floor (its choking pattern), so a drill, scenario or practice asked for isn't an emergency unless the words say it's happening or real ("this is not a drill"); "quiz me on first aid" was the textbooks' quiz mode, and the model then claimed it had added a Red Cross textbook, so the quiz and study modes step aside for drills.requested; "how do you use a tourniquet?" was refused by the model, so a how-to about a floor kind is answered in code with the number for his country and the drill to practise it.
