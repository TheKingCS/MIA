---
id: K-0080
kind: implementation
title: Chickens and the Greenhouse in the canvas's look
status: confirmed
by: claude
created: 2026-11-07T18:28:56+00:00
concerns: web/flock.js, web/equipment.js, core/web_grow.py
from: dec:DEC-0113
---
Chickens (web/flock.js) leads with Log Today's Eggs: four big one-tap counts (+1 +2 +3 +6, Other… for any), the tap being the approval with Undo in the message; then This Week / Lay Rate / Feed per Dozen, two weeks of eggs with today lit in the app's color, Cartons on Hand with Carton Them; feed, birds and the log (folded) below. The Greenhouse (web/equipment.js for scope greenhouse) opens on a new Today tab: Needs You (upkeep due with Done, and readings out of range with a jump to Water), then each planting with a four-step stage meter. The stage comes from core/web_grow.growth_stage and is deliberately honest: batches carry no days-to-maturity, so it goes by days since planting (under 7 Planted, under 21 Sprouting, then Growing) and switches to Picking once anything is harvested; the line says 'Day 38' or 'Picking now · 6 heads so far', never a guessed harvest date like the canvas's mock.
