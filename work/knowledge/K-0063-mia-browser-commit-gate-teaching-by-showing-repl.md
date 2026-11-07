---
id: K-0063
kind: implementation
title: MIA browser: commit gate, teaching by showing, replay
status: confirmed
by: claude
created: 2026-11-07T13:23:29+00:00
concerns: core/browser.py, core/browser_routines.py, core/browser_safety.py
from: dec:DEC-0117
---
Built DEC-0117. core/browser_safety.classify sorts every step READ/ACT/COMMIT/NEVER in code; unknown buttons are COMMIT. core/browser.Browser holds a commit as a Pending and proposes browser.commit (proposed_by mia); core.actions approves it as the person, and perform_pending refuses when the URL changed or the control is gone. A plain yes is handled in talk_it_out.pre_turn by browser.yes_to_waiting only when MIA's last reply named the button. Playwright objects are thread-bound, so one _Worker thread owns them and calls go to it as futures.
What went wrong: (1) the recorder callback runs on the worker thread, so asking the page for its title from it would deadlock; the recording script now sends document.title with each event. (2) A file:// address fell through to search and sent a local path to DuckDuckGo; address_for now refuses every non-http(s) scheme, and file/data/edge links are COMMIT. Smoke-tested on real Edge against a local http page.
