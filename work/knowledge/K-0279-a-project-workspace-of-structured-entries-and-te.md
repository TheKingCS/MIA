---
id: K-0279
kind: decision
title: A project workspace of structured entries, and teams that start only on his yes (T2)
status: confirmed
by: claude
created: 2026-11-17T07:50:29+00:00
concerns: core/teamwork.py, core/teamwork_actions.py, core/assistant_teamwork_actions.py, web/projects.js
from: commit:502ee831, dec:DEC-0198
---
core/teamwork.py: one personal store (teamwork.json) per person with entries and teams, linked to a project by id. Entries are typed (KINDS), carry who wrote them and the model, a basis for findings, and a status: his confirmed, a specialist's derived until confirmed, withdrawn kept with why (the workbooks' honesty rule). The checks live in note(): a specialist must be in the registry, name its model, and source a sourced finding; an unsourced one is an assumption. framed(ids) is the only way a specialist reads entries: exactly those named, each marked as outside text, so a planted instruction is data. Teams: proposed then ready; ready rather than working because nothing runs until T3 (an honest status). team.start is act_with_approval so grants.require refuses it for MIA; team.propose is suggest, since a proposal is a draft. Voice confirms by the number whats_in_the_workspace read out (newest first; same-second entries keep insertion order, a bug the voice test caught). Gotcha: MIAShell.el flattens children one level only, so a section function must return a flat list and be spread.
