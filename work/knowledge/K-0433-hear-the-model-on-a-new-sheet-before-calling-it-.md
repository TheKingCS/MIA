---
id: K-0433
kind: lesson
title: Hear the model on a new sheet before calling it done
status: confirmed
by: claude
created: 2026-11-24T16:16:43+00:00
concerns: core/question_plans.py, core/project_ripple.py
from: dec:DEC-0052
---
Run live on qwen2.5:14b (demo data, 2026-11-24): the project picture came back as one generic sentence. Two causes. The sheet held only its first line, because an unguarded read of the projects (a record with no status) threw and gather logged it; now guarded, and a failed lookup's apology never goes on a sheet as a fact. And the answer protocol's point-out-one-thing rule beat a plan wanting area by area; question_plans.HOW gives a plan its own shape, placed last in the system message (after the sheet) and saying it replaces the one-thing rule: placed before the sheet, the 14b model ignored it. After: nine short sentences, one per area, ending with the offer to draft.
