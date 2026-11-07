---
id: K-0058
kind: decision
title: One loop for every desire: learning paths
status: confirmed
by: claude
created: 2026-11-07T08:31:42+00:00
concerns: core/paths.py, core/guitar.py, core/assistant_path_actions.py
from: dec:DEC-0112, file:core/paths.py
---
What: core/paths.py. Guitar was built first as its own module, then Zac asked that the same principle serve every desire, so the same day the guitar-only store, homework, stats and tools became one engine, and guitar became its first program (core/guitar.py now holds only its content and its ear).
The loop: understand the desire, plan stages, teach, log practice, weekly homework missions whose progress comes from the log, statistics, verify by evidence (a verifier in code, counted against a mark, or said), next stage.
How a new interest gets a program: the local model drafts one from the interest and the goal, given the specialists' notes on it; program_from_draft makes the ids in code and problems() refuses a shape that won't do (a counted check with no mark, a stage with no checks); the draft is kept, described, and started only on "start it".
Lesson from the refactor: the server reads each person's own view (view_for), so a store set on the shared context isn't the one an endpoint sees; tests must set up the person's own store.
Why one engine: two ways of doing the same thing drift apart; one, tested end to end on guitar, keeps every path honest. Her own curriculum is the next to move onto it.
