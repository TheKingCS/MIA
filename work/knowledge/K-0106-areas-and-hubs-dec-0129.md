---
id: K-0106
kind: decision
title: Areas and hubs (DEC-0129)
status: confirmed
by: claude
created: 2026-11-08T06:28:52+00:00
concerns: core/web_areas.py, core/web_surfaces.py, web/shell.js, web/hub.js, web/apps.js
from: dec:DEC-0129
---
Zac's structure: the Dashboard and fifteen areas, each with a hub screen; apps can sit in several areas. One table, core/web_areas.AREAS, decides membership (app module ids, or Page entries for pages that aren't apps, like Projects, Pets, the two Maintenance views). shell() carries areas for the sidebar (the current page's area opens to list its apps) and the Apps page (headings link to hubs); /api/hub/<area> is the hub. Visibility reuses web_surfaces._visible. Tests check every web app has an area, every page exists, and the shared apps Zac named are in both hubs.
