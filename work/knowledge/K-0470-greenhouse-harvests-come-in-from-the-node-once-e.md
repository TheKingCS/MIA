---
id: K-0470
kind: implementation
title: Greenhouse harvests come in from the node, once each
status: confirmed
by: claude
created: 2026-11-25T01:14:37+00:00
concerns: core/greenhouse_link.py, core/life_milestones.py, core/chronicle.py
from: dec:DEC-0150, file:core/greenhouse_link.py
---
core/greenhouse_link.keep_harvests runs in tick after keep_readings: each yield event in the node export (last 7 days) becomes a greenhouse_harvest life event with ref node_yield:<id>, deduplicated by the refs already kept, so a re-read or a restart never doubles it. life_milestones.produce_pounds adds the weighed produce ones (fish excluded by kind harvest_fish); activity.logged is published so rewards rescan. A failure keeping harvests is logged and never stops the alerts. Node ids belong to the node database, so a reset node could restart ids and collide with old refs (accepted: the node is not reset in normal use).
