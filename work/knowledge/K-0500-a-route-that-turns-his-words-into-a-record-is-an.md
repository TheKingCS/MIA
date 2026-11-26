---
id: K-0500
kind: lesson
title: A route that turns his words into a record is an allow-list, and its catch-all is checked against th
status: confirmed
by: claude
created: 2026-11-26T07:25:27+00:00
concerns: core/assistant_turn.py, core/safety_floor.py
from: commit:332638c2
---
The 'we're out of X' route (core/assistant_turn._OUT_OF) first used a deny-list of idioms; the Fable review found 'I'm out of hope' and 'I'm out of reasons to live' would have been added to the grocery list, and the safety floor didn't hear either. Fixed both ways: the route takes only food and household words or what's already in his pantry or list (_groceries), and the floor's never-miss list grew (core/safety_floor._DANGER). Any new route that writes from a free phrase: allow-list what it takes, and run its pattern's open slot against despair phrasings.
