---
id: K-0218
kind: implementation
title: Eight destinations with one owner each, in the same registry
status: confirmed
by: claude
created: 2026-11-11T08:01:26+00:00
concerns: core/web_areas.py, core/web_nexus.py, core/web_environments.py, web/shell.js, web/hub.js, web/apps.js
from: dec:DEC-0153, file:docs/NAVIGATION_ARCHITECTURE.md, file:core/web_areas.py
---
DEC-0153 (Zac, 2026-11-11): MIA's navigation is Dashboard, Home, Garage, Finances, Health + Fitness, AI Tools, Missions and Settings, each with subdashboards, and every app or page has exactly one owner. Done by extending core/web_areas.py rather than adding a registry: Area gained `parent` (a subdashboard is an area inside a destination), `shortcuts` (links to members owned elsewhere, drawn as 'Also here', never a copy) and `page` (the Dashboard is index.html, not a hub). OLD_IDS and resolve() keep DEC-0129's hub links working (hub.html?area=plants_animals opens Homestead). tests/test_web_areas.py fails when an app or page has two owners, none, or a web page is in neither an area nor the listed frame pages. What reads it: the sidebar (web/shell.js sideLinks, shell.areas with subs), the hubs (subdashboards first, back one level), the rooms (a subdashboard is a door counting the apps inside it), the Apps page (each subdashboard its own list), voice (core/web_nexus.wants_area: the eight, the subdashboards, old and everyday names) and the glasses' menu (core/glasses.glasses_areas). No app id, page, store, tool or action kind changed. The demo example files (docs/schema hub, shell, nexus, portals, glasses) were rebuilt from the code with each file's own indentation.
