---
id: K-0073
kind: implementation
title: The Lab on the web: series chips, a chart placed by core, other apps' series read only
status: confirmed
by: claude
created: 2026-11-07T17:58:00+00:00
concerns: core/web_lab.py, core/lab_reading_actions.py, core/assistant_lab_actions.py, web/lab.js
from: dec:DEC-0125, dec:DEC-0113
---
core/web_lab.py serves /api/lab?series=: the Data Logger's own series (chips: latest, how long ago, how many; newest first), and one in full: readings newest first, stats() (latest, low, high, average, change since the first) and chart() points already scaled 0..1 so the page only draws an SVG polyline. The Data Logger also holds Power's (energy_source_<id>_<meter>) and Garage's (maintenance_asset_<id>_<meter>) series; owner_of() spots them by prefix and the page lists them apart under their own names, read only, with a link there; lab_reading.add/delete refuse them so a reading is only changed where it belongs. The action family is lab_reading.* because lab.* is the development lab's (core/lab_actions.py). A series is joined whatever its case (resolve_series, as the voice log_lab_reading does). Voice gained delete_lab_reading (the newest in a series) on the same action, so undo works.
