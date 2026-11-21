---
id: K-0319
kind: implementation
title: Outside text is framed wherever it reaches the model
status: confirmed
by: claude
created: 2026-11-21T04:25:01+00:00
concerns: core/browser_safety.py, core/tool_loop.py, core/main_thread.py
from: commit:8fa8f877
---
WP-03. browser_safety.outside(text, what) frames any outside text like untrusted() does a web page. tool_loop frames the results of OUTSIDE_WHAT lookups (list_inbox, world_finds, get_receipt, whats_in_the_workspace) before the model reads them, and a change asked for after one is held. The loop decides 'lookup' by name prefix (main_thread.changes_records): world_finds and whats_in_the_workspace needed READ_ONLY_DESPITE_NAME or they never entered the loop. tests/test_injection.py: 20 poisoned inputs through every entry.
