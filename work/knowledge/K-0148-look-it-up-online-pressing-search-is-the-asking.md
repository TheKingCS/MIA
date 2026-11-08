---
id: K-0148
kind: implementation
title: Look It Up Online: pressing Search is the asking
status: confirmed
by: claude
created: 2026-11-08T20:46:02+00:00
concerns: core/web_lookup.py, web/lookup.js, server/app.py
from: dec:DEC-0053, task:T-0017
---
core/web_lookup.py puts online_lookup on a screen without an action: a search changes nothing, and typing words and pressing Search is the person asking (DEC-0053's offer-then-search is satisfied by the asking), so POST /api/lookup runs search() directly, outside the turn lock because it waits on the network. The page shows the query actually sent (scrub() may have taken parts out) so the person sees exactly what left the computer, and never keeps a result. The page has no 'Say:' line yet: there's no voice tool for lookups (the parity session's), and a screen shouldn't teach a phrase that doesn't work.
