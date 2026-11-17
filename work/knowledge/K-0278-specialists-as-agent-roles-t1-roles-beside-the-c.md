---
id: K-0278
kind: decision
title: Specialists as agent roles (T1): ROLES beside the charters
status: confirmed
by: claude
created: 2026-11-17T07:33:03+00:00
concerns: core/specialists.py, core/specialist_work.py, core/eng_bench.py
from: commit:4ba902c7, dec:DEC-0198, dec:DEC-0197
---
The teams design's agent fields (department, task types, tools, reasoning, needs, reviews, caveat) live in ROLES in core/specialists.py, merged onto each charter by _as_agent with dataclasses.replace, so the charters stay readable and a test checks ROLES and the charters name the same ids. Agent tools are only those tiered observe or suggest (a test holds it); the calculators are tiered act_within_grant, so an agent reaches numbers through the worksheet (work_it_out, suggest), added in code to every role whose needs include numbers. The model is never named on a role: T1's second part chooses it from core/eng_bench.py's results. Built on the PC while a cloud session built the bench and the worksheet; a duplicate bench of mine was dropped for theirs.
