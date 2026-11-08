---
id: K-0101
kind: implementation
title: Search on the web (Ctrl+K)
status: confirmed
by: claude
created: 2026-11-08T02:39:52+00:00
concerns: core/web_search.py, web/shell.js, server/app.py, web/knowledge.js
from: dec:DEC-0125
---
The frame (web/shell.js openSearch) opens a dialog on Ctrl+K or '/' (not while typing), and from Search in the sidebar and the phone's bottom bar. Apps are matched in the browser from /api/shell's list (so only apps the person can open); records come from /api/search (core/web_search.py), which walks core/links.KINDS (the catalog the link graph already uses) in the person's own view, so no second registry. Ranking is pure (score: whole query at the start, then word starts, then inside a word; every word required) and tested. Each kind maps to its web page in PAGES; asset and recipe pages take ?id=. Knowledge now reads ?q= so the dialog can offer 'Search the library'. The private journal is never searched. Results from an older keystroke are dropped (a sequence number).
