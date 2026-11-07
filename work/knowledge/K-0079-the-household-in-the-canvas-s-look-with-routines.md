---
id: K-0079
kind: implementation
title: The Household in the canvas's look, with routines added, paused and resumed
status: confirmed
by: claude
created: 2026-11-07T18:25:36+00:00
concerns: core/household_routines.py, core/routine_actions.py, core/assistant_household_actions.py, web/household.js
from: dec:DEC-0113, dec:DEC-0125
---
web/household.js now matches the canvas: Done Today with its meter (gold when every routine is done), a card per routine (Daily or This week, its streak in words from household_routines.streak_words) with Did It or Done, what's still to do first, paused routines apart with Resume, Add a Routine. Routines could only be added by voice: household_routines.add_routine is now the one way (the voice tool add_household_routine calls it), with the action kinds routine.add / routine.pause / routine.resume (core/routine_actions.py) and RecurringMissionManager.set_active; pause keeps the history so resume picks the streak back up. Voice gained pause_household_routine (names matched by the words said, via assistant_cooking_actions.find_recipe; its trigger phrases say 'routine' so 'pause the music' doesn't reach it). Fixed on the way: seven pages (Household, Classroom, Diagnostics, Knowledge, Memories, Navigation, Observations) wore Talk's icon through a leftover data-icon='assistant'; Operating and Kept now use the journal and notes icons.
