---
id: K-0375
kind: test-procedure
title: The hobby programs needed their own words to be reachable
status: confirmed
by: claude
created: 2026-11-24T06:54:47+00:00
concerns: core/assistant_path_actions.py, core/question_plans.py
from: commit:6eb341aa
---
A routing probe of seventeen everyday phrasings for the four hobby programs built 2026-11-23 found fifteen reached nothing on the phone: the learning tools had guitar-only trigger phrases. register_path_actions now registers LEARNING_WORDS (woodworking, the shop, dovetail, bushcraft, ferro rod, knots, fitness, gardening, homework, lesson, practice...) and the program names as the learning domain words, and the week review and evening plans leave homework and practice questions to them. All seventeen are in tests/test_everyday_phrasing_routing.py. A new program should add its words there.
