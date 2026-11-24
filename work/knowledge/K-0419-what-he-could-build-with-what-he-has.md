---
id: K-0419
kind: implementation
title: What he could build with what he has
status: confirmed
by: claude
created: 2026-11-24T14:16:44+00:00
concerns: core/buildable.py
from: dec:DEC-0118
---
core/buildable.py (what_can_i_build): every built-in Library plan at its starting size against the workshop stock through plan_library.shopping_list; ranked by the share of materials fully on hand, then partly, then the cheapest to finish; a plan with nothing on hand is left out; the cost to finish is said as at least while anything has no price. Read-only, ends by offering to draft one.
