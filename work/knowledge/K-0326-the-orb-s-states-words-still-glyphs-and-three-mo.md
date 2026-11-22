---
id: K-0326
kind: implementation
title: The orb's states: words, still glyphs, and three more from real events
status: confirmed
by: claude
created: 2026-11-22T13:20:02+00:00
concerns: core/orb_state.py, core/actions.py, core/llm_manager.py, web/shell.js
from: task:WP-07, dec:DEC-0255
---
WP-07 (REQ-VIS-009/010, DEC-0255). core/orb_state.LOOK gives each state its words and a still glyph (all distinct, tested), carried to every page in /api/shell as `orb`; web/shell.js sets data-label, data-glyph and aria-label on each orb, and under prefers-reduced-motion web/ui.css shows the glyph inside and the words under it. New states from real events: `needs-you` (orb_state.watch: ActionCenter.waiting is asked whenever the state is read, so a card decided, being decided or expired stops counting at once), `offline` (orb_state.hold, set by LLMManager.is_available and by a turn that couldn't reach the model, cleared by an answer; the spec's Unavailable, drawn with the existing offline style), and speaking (the page, while her reply's audio really plays). tests/conftest.py resets the orb before each test. Not built: processing, interrupted, background, error, muted.
