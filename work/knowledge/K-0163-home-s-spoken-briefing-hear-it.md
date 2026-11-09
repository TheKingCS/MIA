---
id: K-0163
kind: implementation
title: Home's spoken briefing: Hear It
status: confirmed
by: claude
created: 2026-11-09T08:30:53+00:00
concerns: core/web_surfaces.py, web/welcome.js
from: dec:DEC-0125
---
WEB_PARITY's last 'not yet' on Home. core/web_surfaces.briefing() says the day in a few sentences from what Home already shows: the greeting and date, today's first three by name (and how many more), how many are coming up, and the one thing MIA noticed (its claim lower-cased to read on, unless it starts with a name or 'I'). dashboard() serves it as `briefing`; Home's Hear It button speaks it through /api/heavy/speak (the home computer's voice) and says so when there's no voice. The screenshot needs sessionStorage 'mia.nexus.opened' set first, or Home redirects to the Nexus.
