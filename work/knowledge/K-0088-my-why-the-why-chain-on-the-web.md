---
id: K-0088
kind: implementation
title: My Why, the why chain on the web
status: confirmed
by: claude
created: 2026-11-08T01:40:31+00:00
concerns: core/web_why.py, web/why.js, web/profile.js, server/app.py
from: commit:14916ed, dec:DEC-0125
---
core/web_why.py shapes why_graph.build_why_sheet for web/why.html (reading it never records a checkpoint: record_checkpoint=False; asking by voice still records one a month). why.link takes a goal and what it serves by id or by name, making a new goal from a name like link_my_reason does, and refuses a cycle with intents.would_create_cycle before anything is made. The page is reached from Profile (What You are Working Toward) because the Dashboard app that owns the why domain is retired; moving it into an app waits on the audit (Stage 3).
