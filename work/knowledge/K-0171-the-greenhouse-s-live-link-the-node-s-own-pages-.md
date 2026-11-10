---
id: K-0171
kind: implementation
title: The greenhouse's live link: the node's own pages, served as exact files
status: confirmed
by: claude
created: 2026-11-09T08:12:13+00:00
concerns: homestead/viewer/serve_exports.py, core/greenhouse_link.py, tests/test_greenhouse.py
from: dec:DEC-0150
---
DEC-0150 answer 3c ('C later'), 2026-11-09. homestead/viewer/serve_exports.py v0.2 adds PAGES: the dashboard (also '/'), the digital twin, nav.js and config/layout.json (the twin fetches '../config/layout.json', which a browser resolves to /config/layout.json at the root), each an exact file named in code, so no request path is ever joined to a folder and the rest of config/ (the notifications file holds the SMTP password) is never served. Journal and planner pages stay off: their exports aren't refreshed by main.py. MIA's side (core/greenhouse_link.py): live_url, a 'show me the greenhouse live' reply, and 'how's the greenhouse?' fetching fresh when the last read is over a minute old, saying when the node couldn't be reached and the time of the reading it's giving instead.
