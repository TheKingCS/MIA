---
id: K-0050
kind: decision
title: Why MIA's curriculum is practised on her own code
status: confirmed
by: claude
created: 2026-11-07T05:58:49+00:00
concerns: core/curriculum.py, core/night_school.py, docs/CURRICULUM.md
from: dec:DEC-0107, file:core/curriculum.py
---
What: core/curriculum.py holds ten tracks of computing (engineering, testing, documentation, design, web, apps, deploying, security, pen testing on herself, monitoring), each objective saying what she can do once she has it and how she practises it on her own files. Night School gives one lesson a night to the next objective.
Why on her own code: every exercise is real, so the code she learns on gets better too; her files are what she has to be good at; and Night School can grade it the honest way, a test that fails before and passes after, with the full suite showing nothing new broke.
Why the next objective is chosen that way: breadth first (the track least mastered), and on a tie the track she has tried least, so one hard objective can't hold her on one track for weeks.
Why security has rules in the prompt: pen testing is only safe and allowed against what she owns. The rules keep every attack in-process against her own server, and every finding becomes a test and a fix Zac approves.
