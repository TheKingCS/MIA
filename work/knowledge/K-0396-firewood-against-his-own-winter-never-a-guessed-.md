---
id: K-0396
kind: implementation
title: Firewood against his own winter, never a guessed one
status: confirmed
by: claude
created: 2026-11-24T10:26:18+00:00
concerns: core/firewood.py, core/assistant_today_actions.py
from: commit:441d9729
---
core/firewood.py reads inventory records named as firewood with a cord measure (a face cord or rick is about a third of a full cord), and compares with prepared.firewood_cords, his own figure set through set_preparedness (I burn 4 cords a winter). Without it she says the usual range only as that (3 to 6 cords as main heat) and asks; a pile with no measure is named. firewood_check is read-only.
