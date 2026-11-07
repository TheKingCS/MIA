---
id: K-0042
kind: decision
title: Claude writes MIA a knowledge entry for what it builds
status: confirmed
by: claude
created: 2026-11-07T04:59:59+00:00
concerns: core/dev_knowledge.py, work/knowledge
from: dec:DEC-0104, file:core/dev_knowledge.py
---
What: Zac asked (2026-11-07) that while Claude develops MIA it also writes documents for her explaining what it is doing, how, and why that way, so she has them to refer to even before she can study them fully.
How: they go in this vault (work/knowledge), as entries like this one, each citing the commit, task or decision it came from and the files it concerns. for_task() already hands the entries about a task's files to whoever works on it next, MIA's own coder and Night School included, so what Claude learned reaches her where she uses it. Code docstrings (DEC-0104) say what the code does; these entries say why it was built that way and what went wrong on the way.
Why the vault and not a new folder: it's already versioned, sourced, searchable by file, and read by MIA's tools.
