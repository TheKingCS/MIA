---
id: K-0391
kind: security-finding
title: A denial in a message cancelled every danger phrase in it
status: confirmed
by: claude
created: 2026-11-24T09:30:26+00:00
concerns: core/safety_floor.py, tests/test_safety_floor.py
from: commit:fded0659
---
A seventeenth fresh review of fded0659: detect_danger cancelled the whole message when any denial matched, so I'm not suicidal but what's the point of living (the classic way passive thoughts are said) got no safety reply. A denial now cancels only the danger phrase inside its own span. Also: indirect wording missed (noone, disappeared, nobody'd, wouldn't anyone miss me, better off not being here, life's not worth living, what is the point, can not go on, never born with was), and ordinary talk that fired (the point of going on with this project, living in the city, better off gone by noon, miss me at the meeting, exist on ramen), which matters because a false positive turns the conversation to Listen mode and alerts a child's guardians.
