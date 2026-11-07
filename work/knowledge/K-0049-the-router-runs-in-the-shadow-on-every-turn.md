---
id: K-0049
kind: implementation
title: The router runs in the shadow on every turn
status: confirmed
by: claude
created: 2026-11-07T05:39:17+00:00
concerns: core/model_forge.py, core/turn_trace.py, core/loops.py
from: dec:DEC-0106, file:core/turn_trace.py
---
What: core/turn_trace.py now notes, on each traced turn, the top five tools MIA's own router would have offered (shadow_picks in core/model_forge.py), beside the tools she actually called. The models.router_shadow loop (core/loops.py) reads how often the called tool was in that top five over 30 days, once 20 such turns exist.
How: the router is loaded once and again only when its weights file changes; a pick takes about 1 ms. shadow_picks returns nothing on any error, so it can never break or slow an answer. Only tool names are kept; private turns are never traced at all.
Why: the keyword router was tuned on the routing corpus, so the corpus can't show which router is better. New requests can. The tool she called isn't always right either, so this is agreement, not accuracy: the stronger test is the turns that went wrong (the Fix-It Log), to be read next.
What it doesn't do: change any answer. A model goes into use only when it wins on new requests and Zac approves.
