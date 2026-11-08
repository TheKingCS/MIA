---
id: K-0111
kind: implementation
title: Area environments, Garage first (DEC-0130 M3)
status: confirmed
by: claude
created: 2026-11-08T07:52:00+00:00
concerns: core/web_environments.py, core/web_areas.py, web/hub.js, web/spatial.css
from: dec:DEC-0130
---
core/web_environments.ENVIRONMENTS maps an area to a builder; web_areas.hub() adds 'environment' (None keeps the tiles, and a failing builder falls back to tiles). garage() reuses equipment_page('garage')['assets'] (not all_assets, which includes the house's furnace and properties), sorts bays by overdue, takes attention for needs-you, and gathers low parts across assets once each (asset_parts.parts_for). hub.js renders by environment kind; spatial.css adds .holo panels, perspective bays that come forward on hover, the area hue on the hero and a faint hue vapor; reduced motion stills it.
