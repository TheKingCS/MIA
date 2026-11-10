---
id: K-0205
kind: test-procedure
title: Checking the web frame without a test that starts a browser
status: confirmed
by: claude
created: 2026-11-10T13:35:38+00:00
concerns: web/shell.js, web/mia.js, tools/page_check.py
from: commit:e5cee113, commit:ad2dee89, file:tools/page_check.py
---
No test may start a real process, so browser checks are tools: tools/page_check.py opens every web page in demo mode in headless Edge (Playwright with channel msedge; /schema served from docs/schema as the server does) and fails on a page that doesn't answer 200, throws or logs a console error; CI runs it on Windows. For a frame change, a one-off harness page in the scratchpad loading the real shell.js with a stand-in MIA, or a real page with page.route() failing the /api calls, shows the behaviour; run it against the old file too, to be sure it tells the difference.
