---
id: K-0052
kind: implementation
title: One decorator puts a store in her history
status: confirmed
by: claude
created: 2026-11-07T06:34:51+00:00
concerns: core/life_events.py, core/links.py, core/self_audit.py
from: dec:DEC-0108, file:core/life_events.py
---
What: the first self-audit found only 15 of 73 stores recorded life events. life_events.on_change(type, noun, ref) is a decorator for a store method: after each call that succeeds it records one event, named from what the method returned (name, title or label) and referenced as ref:id. 109 methods in 34 stores now carry it, and 20 new link kinds in core/links.py use the same ref names, so a record's history and its links meet.
Why a decorator: hand-written record calls in a hundred methods would be a hundred places to get wrong; a one-line decorator says the same thing the same way, and can't break the change (it records only after success, and swallows its own errors).
Choices: named=False for what's personal (a memory's words, a draft); left out on purpose, with why in BY_DESIGN: sensor readings, the daily freedom balance, MIA's own insights, the live workout. links._records now also accepts a list a store keeps (places, obligations, policies) as well as a method.
Result: 49% to 67% of store connections made. The life state is the biggest gap left.
