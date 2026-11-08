---
id: K-0126
kind: implementation
title: Every area as a room of its apps (Nexus M5, first pass)
status: confirmed
by: claude
created: 2026-11-08T16:15:31+00:00
concerns: core/web_environments.py, web/hub.js
from: dec:DEC-0130, dec:DEC-0135
---
Rather than wait for each area's bespoke space, core/web_environments.room gives every area without one a room: its _entries as doors, each counting today's overdue/today items whose module is that app (web_nexus._today), and up to six of those items as What Needs You. environment() now returns room() for areas without a builder, so hub() always carries one; web/hub.js draws it with the Nexus engine only in the Spatial look and falls back to the tiles otherwise (and with ?flat, which the Tiles › link uses). App icons in the hub data are emoji, which the engine's placeholder can't draw, so the room passes the app's line-icon name (MIAIcons.svg(id)) and falls back to the page icon or mia.
