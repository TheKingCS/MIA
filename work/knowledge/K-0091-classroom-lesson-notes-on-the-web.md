---
id: K-0091
kind: implementation
title: Classroom lesson notes on the web
status: confirmed
by: claude
created: 2026-11-08T01:14:20+00:00
concerns: core/classroom_actions.py, core/classroom_manager.py, core/assistant_life_actions.py, web/classroom.js
from: commit:ae48ba8, dec:DEC-0125
---
A lesson's notes show under it on web/classroom.html (screen() carries notes). The Notes button edits the whole note through lesson.notes (replace; empty clears), while voice keeps adding a line with add_lesson_notes and reads it back with the new get_lesson_notes. Replace on the screen, append by voice: the screen shows the whole text, so editing it whole is what a person expects.
