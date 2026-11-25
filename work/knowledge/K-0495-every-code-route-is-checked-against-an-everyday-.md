---
id: K-0495
kind: test-procedure
title: Every code route is checked against an everyday corpus
status: confirmed
by: claude
created: 2026-11-25T16:11:41+00:00
concerns: tests/test_code_routes_corpus.py, core/assistant_turn.py, core/lesson_answer.py
from: commit:edf9d16d
---
Answers taken in code before the model (lesson_answer, materials_reply, next_lesson_reply, days of water, reminders on a day or weekly, drills.requested, first_aid_floor.teach, the lab routes) kept taking messages meant for others: review after review on 2026-11-25 found one. tests/test_code_routes_corpus.py runs a corpus of everyday messages through all of them and fails on any taken, and checks each still takes its own question (MEANT). A new code route gets a line in ROUTES and MEANT; a message a route wrongly took goes into EVERYDAY.
