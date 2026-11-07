---
id: K-0045
kind: lesson
title: Never choose a model's settings on the requests that score it
status: confirmed
by: claude
created: 2026-11-07T05:17:37+00:00
concerns: core/model_forge.py
from: dec:DEC-0106, file:core/model_forge.py
---
What happened: trying more training epochs and watching the score on the routing corpus took the router from 47% to 84% first pick. But picking the settings by that same score makes the score a flattering one: the settings were fitted to those exact requests.
Fix: split() halves the held-out requests (alternating). The settings are chosen on one half; the card's score comes from the other half, which chose nothing. The honest number is 81% first pick, 97% in the top five.
Lesson: keep three groups apart: what a model learns from, what you choose its settings with, and what you report its score on. The score is only true for requests that had no say in building it.
