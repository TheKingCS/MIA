---
id: K-0128
kind: lesson
title: A read-only tool must be named like one, and how-to phrasing never reaches tools
status: confirmed
by: claude
created: 2026-11-08T16:21:56+00:00
concerns: core/assistant_homestead_actions.py, core/main_thread.py, core/assistant_actions.py
from: commit:2cc27cc0
---
direct_lookup() answers instantly only when exactly one read-only tool's trigger matches and it takes no details but the question's own words. 'Read-only' is decided by the name (core/main_thread.changes_records: get_, list_, search_...), so homestead_next_step was treated as a write and never looked up; renamed get_homestead_next_step. A budget became prompt_arg and is read from money words only ('$300', '200 dollars', 'a budget of 150'), so 'the next 3 projects' is never a budget. 'Where do I start...' is a how-to question, which goes to the help docs with no tools offered: don't use it as a trigger phrase.
