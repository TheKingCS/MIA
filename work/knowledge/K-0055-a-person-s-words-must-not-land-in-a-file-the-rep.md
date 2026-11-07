---
id: K-0055
kind: security-finding
title: A person's words must not land in a file the repo keeps
status: confirmed
by: claude
created: 2026-11-07T07:29:38+00:00
concerns: core/specialists.py, work/specialists
from: dec:DEC-0109, file:core/specialists.py
---
What happened: the first version of ask_specialist added any question no note answered to the specialist's workbook, word for word. The workbooks are work/specialists/*.json, versioned in git and pushed: a question like "what wire for my neighbour's deck" would have been published with the code. Caught on review the same day, before anyone had asked one.
Fix: a question asked by voice is never written; the specialist only counts that it was asked something it couldn't answer, and study hall takes the most-asked specialist first. A question typed at the PC with python -m tools.specialists ask is kept, as Zac's own. A test checks the words aren't kept.
Lesson: before writing anything a person said, ask where the file lives. Personal folders (data/profiles/<id>/) keep a person's words; anything under work/ or docs/ is shared with everyone who has the repo. The same rule as the Fix-It Log and capability gaps, which keep the words in the person's folder and give the shared side only kinds and counts.
