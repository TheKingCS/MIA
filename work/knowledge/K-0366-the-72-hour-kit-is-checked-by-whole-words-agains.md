---
id: K-0366
kind: implementation
title: The 72-hour kit is checked by whole words against his records
status: confirmed
by: claude
created: 2026-11-24T05:30:09+00:00
concerns: core/ready_kit.py, core/question_plans.py
from: commit:cce9189a
---
core/ready_kit.py checks Ready.gov basic disaster supplies kit against the names in his inventory and pantry, each kit item with its own whole-word pattern (a headlamp counts as a light, maple syrup is not a map; a propane torch was taken out of the light words). Water and food come as days from core/preparedness.py against three days. What is not found is said as not in your records, never as you do not have it, since he may own it unlogged; medicine, glasses, cash and papers are said as only he can check. Also: the debts plan words now catch the card said plainly (toward the card, which card should I pay, my card paid off) for the phone, which has no embedding model.
