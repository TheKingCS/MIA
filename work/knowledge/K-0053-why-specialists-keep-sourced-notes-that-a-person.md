---
id: K-0053
kind: decision
title: Why specialists keep sourced notes that a person confirms
status: confirmed
by: claude
created: 2026-11-07T06:42:24+00:00
concerns: core/specialists.py, core/night_school.py, work/specialists
from: dec:DEC-0109, file:core/specialists.py
---
What: core/specialists.py gives each area of what MIA knows a worker with a charter, limits and a workbook of notes. Night School's study hall has one study a night: her teacher writes notes for its open questions.
Why every note needs a source: a model writes fluent, confident text whether or not it's true; a source is what lets a person check it, and what MIA says when she answers. A note with no source is refused in code.
Why derived until confirmed: the same reason as the Knowledge Vault (DEC-0083): she's never taken to be right because she said so. Answers always say which a note is.
Why limits in the charter, and in the prompt: some areas (strategy, radio, construction) touch safety and the law. The limit says what the area is for (strategy: history, planning, logistics, protecting a household; never how to hurt people) and is given to the teacher with every study session.
Why turns: the specialist that studied longest ago goes next, so every area grows, not only the one asked most.
