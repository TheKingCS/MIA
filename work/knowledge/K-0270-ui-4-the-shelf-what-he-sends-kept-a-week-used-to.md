---
id: K-0270
kind: implementation
title: UI-4, the shelf: what he sends, kept a week, used together
status: confirmed
by: claude
created: 2026-11-16T14:36:00+00:00
concerns: core/shelf.py, core/shelf_actions.py, core/ual.py, core/assistant_ual_actions.py, server/app.py, web/shelf.js, web/shell.js, tests/test_shelf.py
from: dec:DEC-0165, task:UI-4
---
What: core/shelf.py, a personal store (PERSONAL_STORES 'shelf', sealed at rest, atomic so undo works) of ShelfEntry, each the UAL's Capture fields unchanged plus kept/until. KEEP_DAYS 7, MAX_DAYS 30, MAX_ENTRIES 50; expired entries drop on read (written outside undo, since an expiry isn't anyone's change). The same text from the same place moves to the top instead of being kept twice. combined() makes several entries one Capture (source_app mia:shelf, each text under '--- n. from <where> ---', cut at 20,000) for any catalogue action.

How: actions shelf.keep (params are the capture's fields, re-checked by Capture.from_dict), shelf.remove, shelf.clear in core/shelf_actions.py, all act_within_grant in the assistant app's manifest. The UAL catalogue gains keep_shelf (ACT, any kind), so the palette, the phone card and do_with_this offer it with no new front-door code. API: GET /api/shelf, POST /api/shelf/use {which, action_id} (no action: the offer). Web: shelf.html in AI Tools, and a document-level drop in shell.js that proposes keep_shelf (pages with their own drop zone call preventDefault first). Voice: whats_on_my_shelf, use_my_shelf (numbers as listed, or all), take_off_my_shelf.

Why: Q-43 (only what is sent), so no clipboard watching. Reusing the capture and catalogue means a shelved page is outside text exactly as a selection is (framed, OUTSIDE_MARK), and the shelf itself never writes elsewhere (a test reads its source).

What went wrong: a file alone used to be offered nothing; it is now offered Keep On My Shelf, so test_ual's 'nothing I can do' case moved to an empty offer. MIAShell.el prints a null child as the word 'null': filter children. A planted-instruction test must compare offers of the same length, since some actions fit by length.
