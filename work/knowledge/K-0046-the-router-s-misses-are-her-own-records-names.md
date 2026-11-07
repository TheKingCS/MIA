---
id: K-0046
kind: lesson
title: The router's misses are her own records' names
status: confirmed
by: claude
created: 2026-11-07T05:17:37+00:00
concerns: core/model_forge.py, core/assistant_actions.py
from: dec:DEC-0106, file:core/assistant_actions.py
---
What: the first router missed "I fertilized the peppers", "How much plywood do I have?" and "Do I have any 555 timers?". The tools' own words say nothing about peppers or plywood; the keyword router gets them right because it also knows the names of the person's own records (register_entity_names in core/assistant_actions.py).
Lesson: what a model can't know from its training data, give it as features (a feature for "names one of your maintenance assets", for example) rather than hoping it guesses. That's the next step for the router.
