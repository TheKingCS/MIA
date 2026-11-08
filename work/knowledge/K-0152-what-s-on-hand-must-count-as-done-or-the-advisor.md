---
id: K-0152
kind: lesson
title: What's on hand must count as done, or the advisor keeps recommending it
status: confirmed
by: claude
created: 2026-11-08T22:00:21+00:00
concerns: core/development_engine.py, tests/test_development_engine.py
from: dec:DEC-0144
---
DEC-0144, 2026-11-08 afternoon, found by walking the year by hand again (five months x four profiles): with beds, compost and soil on hand, next_step still said 'build a three-bay compost bin' in every month, its goal the bin itself. done_from_records and IMPLIED_TAGS cover projects the records show; nothing covered a project whose whole purpose is already had. met() now adds every candidate whose provides are all on hand (rivals too: seed cups on hand meet both the toilet-roll cups and the trays); a sale provides nothing, so it's never met. Applied in ranked() and next_step(). After: winter says a rain barrel toward drip irrigation, July and September say a canning setup for the harvest. Walking scenarios by hand keeps finding what the tests' scenarios don't.
