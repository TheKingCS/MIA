---
id: K-0176
kind: implementation
title: Eight more link kinds, four more life areas, and what's by design
status: confirmed
by: claude
created: 2026-11-09T09:42:44+00:00
concerns: core/links.py, core/life_areas.py, core/self_audit.py, tests/test_links.py, tests/test_life_areas.py
from: file:core/links.py, file:core/life_areas.py, file:core/self_audit.py
---
2026-11-09, the self-audit's store connections, second pass (47 open, now 20). core/links.py KINDS gained the records a person would tie to a goal, project or debt: subject (classroom), workout_template, grow_batch (named by its crop), questline, workplace (The Dungeon's dungeons: 'job' was already the workshop's), direction, campaign and inbox_item (named by its subject). Lists the stores keep as attributes work as listers, since _records takes a list or a method. core/connections.py walks only its own named kinds, so MIA raises nothing new by surprise. core/life_areas.py gained directions, workplaces (shifts cleared this week, the next planned one), worlds and questlines (the one under way and its chapter). Seven stores went into BY_DESIGN for links: her tools and settings (response style, browser routines, alarms, email drafts, camera frames, her operating journal, the live job). Four existing entries also took links: data_logger, freedom_log, insights and training. What's left is real: links for health, the wallet, memories, notes, learning paths and GPS tracks (dict records need a small adapter, and health and the wallet need care for privacy), and the life state for the creative and game stores.
