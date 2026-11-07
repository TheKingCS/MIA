---
id: K-0060
kind: implementation
title: Learning-path checks passed from the person's own records
status: confirmed
by: claude
created: 2026-11-07T09:27:57+00:00
concerns: learning, verification
from: dec:DEC-0112
---
A check can be verified 'recorded': MIA reads a record she already keeps (core/paths.py SOURCES: workouts, workout minutes, GPS km and the longest track, meals and different recipes made), counted only from the day the path started and only the signed-in person's (unstamped records count for everyone, as the stores count them). sweep() runs before homework is updated and passes what reached the mark by itself, keeping only passes so a daily read doesn't fill the history with misses; asked directly, a miss is kept and says where the records stand. Drafts may use it (the prompt lists the sources; problems() refuses an unknown source). Why: evidence beats a person's say-so, and the records already exist.
