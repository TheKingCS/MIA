---
id: K-0421
kind: debugging
title: A shortage notice that could be used up unseen
status: confirmed
by: claude
created: 2026-11-24T14:34:12+00:00
concerns: core/project_ripple.py, core/buildable.py, web/planner.js
from: commit:b85cb7ae, commit:a40287e1, commit:f338788d, commit:8b0813bd
---
Review of b85cb7ae and the three before it: gone_short saved its baseline every time findings ran, so a notice the gate held back, or one read by anything-unusual first, was lost; it replaced the whole config dict, dropping other plans; one bad plan stopped it. Now what has been covered only grows (merged plan by plan), a shortage is reported while it lasts with a key naming the material and its count, and the gate says each once. Stock is laid against confirmed builds in turn, oldest first (_allotted), so two builds never both count the same boards; the afford line says the spoken-for money is not in the freedom date; what_can_i_build lost the bare what could I build triggers (what could I build to keep deer out); the Planner panel speaks to him (to_you), lower-cases after a label, and retries after a failed read.
