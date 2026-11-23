---
id: K-0356
kind: lesson
title: A fresh review of the day's builds: the emergency floor missed most panicked words
status: confirmed
by: claude
created: 2026-11-23T18:29:32+00:00
concerns: core/first_aid_floor.py, core/themes.py, core/appearance.py, web/shell.js, core/money_ahead.py, core/unusual.py
from: commit:87120401
---
A reviewer agent given only the code (2026-11-23) found 12 problems all tests had passed. Worst: first_aid_floor needed a pronoun, so 'baby not breathing', 'he fainted', 'a snake bit me' were missed; it had no seizure, drowning, asthma or electric-shock kind; first-match-wins gave CPR for 'choking and can't breathe'; 'cut off', '2-stroke', 'turning blue', 'won't wake up' fired on everyday sentences; the three desktop chat boxes returned before pre_turn when no model was set, so the floor never ran there; and every follow-up got the same canned text. Fixed: kinds() returns every match most-critical-first (choking, anaphylaxis, drowning, shock before CPR), each pattern needs a person or body where an everyday sentence could match, _FIGURE/_PAST/_ANIMAL exclusions, _HAPPENING overrides a question's opening, respond() lets the same emergency's next words reach the model. Also: a light theme could set a meaning colour near-black or to another meaning's hue (now saturation, brightness and nearest-meaning checks); --accent-soft washed out on Daylight; a reply asked before he cut in still played (voice epochs); money_ahead dropped all but the first missed bill and double-counted debts; the egg check counted today's unfinished tally. Lesson: for a safety floor, write the corpus from how people actually talk in a panic, not from tidy sentences.
