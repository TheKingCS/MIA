---
id: K-0498
kind: lesson
title: Narrowing a safety pattern needs the old cases run against it
status: confirmed
by: claude
created: 2026-11-26T00:08:26+00:00
concerns: core/first_aid_floor.py
from: commit:855b6b57, commit:617aa6ea
---
On 2026-11-25 the home kinds of the emergency floor (fire, gas, carbon monoxide) were widened, then a review found false takes and the next fix narrowed the fire words to a list of places; Fable's check then found real fires the first version caught that the narrowed one missed ("the apartment is burning", "the smoke alarm is blaring and there are flames"), and that a mixed message could lose its CPR steps once three kinds matched. What held: run every phrase the old pattern caught against the new one before narrowing (the never-miss list does this only for phrases already in it), keep a figure's veto to its own span, and say a person's emergency beside a home's.
