---
id: K-0408
kind: implementation
title: A plan cut list read one cut at a time for the shop
status: confirmed
by: claude
created: 2026-11-24T12:27:52+00:00
concerns: core/assistant_plan_actions.py
from: commit:df0e29ae
---
next_cut (plans domain, observe) reads a plan materials.cuts one at a time: the plan he names via PlanLibrary.best, else the one he was cutting; the place is kept in config (modules.plans.cut_at) for the session only, never saved, since it is a place in a list rather than a record. Start over resets it. The hands-free half of shop mode that needs no decision; how shop mode starts is Zac to say (brainstorm round 6).
