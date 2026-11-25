---
id: K-0488
kind: implementation
title: How-tos answered from her own courses' lessons
status: confirmed
by: claude
created: 2026-11-25T12:41:27+00:00
concerns: core/lesson_answer.py, core/assistant_turn.py, core/question_plans.py
from: commit:d2001989
---
core/lesson_answer.py: a how-to whose subject is one listed lesson (ASKS: each lesson its own question pattern, never a loose overlap of words) is answered from that lesson in code, before the question plans: steps, why, what to watch for, a drill to practise it (DRILL_FOR), and how to start the course when he hasn't. Never a when (planting dates are what_to_plant's). Found by a live sweep of twenty everyday questions: the courses taught these, but the turn sent them to the project picture plan, the model or an empty library. A new lesson that answers a common how-to gets an ASKS entry.
