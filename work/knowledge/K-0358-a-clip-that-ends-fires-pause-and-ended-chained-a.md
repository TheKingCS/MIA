---
id: K-0358
kind: lesson
title: A clip that ends fires pause and ended: chained audio must move on once
status: confirmed
by: claude
created: 2026-11-23T19:44:31+00:00
concerns: web/shell.js, core/show_source.py, server/app.py
from: commit:755f4142
---
Third fresh review (2026-11-23), of first-words-sooner and show-me-where-it-says-that: in Chromium a finished Audio fires pause then ended, so the chained playReply took two parts at once and dropped the rest after the first sentence; each clip now moves on once (a moved flag). show_source cut refs at the first space (PDF names have spaces) and missed titles with quotes; its ask fired on everyday sentences (show me where it is, open the page for my budget) and never expired; now it needs words pointing back at her answer, no topic named, within 15 minutes. PDF pages are numbered from 1 in pack_index (no +1). The split is used only when this PC can voice the rest itself (/api/heavy/speak has no home-computer fallback).
