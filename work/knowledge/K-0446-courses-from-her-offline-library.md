---
id: K-0446
kind: implementation
title: Courses from her offline library
status: confirmed
by: claude
created: 2026-11-24T18:10:16+00:00
concerns: core/library_course.py, core/assistant_library_actions.py
from: dec:DEC-0112
---
Zac asked: I want to learn about x and have offline coursework about any subject, quality information. core/library_course.py (learn_about, library_lesson): the subject is searched in the offline library once per STAGES (what it is, basics, tools, how it is done, safety, problems, going further, history); each stage keeps the best article no earlier lesson used whose title or text holds the subject's words; fewer than 2 lessons is said plainly, never padded. The course goes in Classroom under Library courses, each lesson's notes naming its article, pack and ref, made in one tool call (one undo). Teaching reads the next undone lesson's article whole (read_further, framed as outside text) with an instruction to teach only from it. learn about now builds a course (add_course lost that trigger); learn to play still starts a learning path. On this Windows PC the library reader is blocked (WAITING_ON 0zh), so it says so and offers a path; it works where the packs read.
