---
id: K-0059
kind: implementation
title: MIA's own curriculum runs on the learning-path engine
status: confirmed
by: claude
created: 2026-11-07T08:42:00+00:00
concerns: core/curriculum.py, core/night_school.py, core/paths.py
from: dec:DEC-0112, file:core/curriculum.py
---
What: core/curriculum.py now makes each of its ten tracks a Program for core/paths.py (program_for: stages by level, a lesson per objective saying how she practises it, a check per objective verified "tested"), and keeps her own PathBook in data/dev/mia_paths (mia_book, every track started). Night School reads her next objective from that book (progress_of) and records each curriculum lesson on it (record_lesson: a practice session and an attempt).
The mastery rule kept: an objective is passed only when its second lesson passes; earlier lessons are attempts not yet passed, their value the passes so far. So the stage of a track moves exactly when her level moves.
The "tested" verifier refuses anything sent: her checks are passed only by Night School's grading (a test that fails before and passes after), never by a claim.
Test safety: Night School's test fixture points curriculum.BOOK_DIR at a temporary folder, or a test night would write into the real data/dev (the conftest guard would fail the run).
Why: Zac, 2026-11-07: she should use herself the same way the user does. Now she literally does: one engine, the same practice log, attempts, stages and statistics.
