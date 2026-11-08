---
id: K-0112
kind: implementation
title: The Nexus on the glasses: a flat ring of areas
status: confirmed
by: claude
created: 2026-11-08T10:37:07+00:00
concerns: core/glasses.py, web/glasses.js, web/glasses.css
from: dec:DEC-0130
---
glasses_apps() now carries `areas` (core/glasses.glasses_areas): each area in AREAS order that has an app on the glasses, with its short name (short_name: '&' for 'and', Settings), hue, those app ids and needs from web_nexus.portal_status. web/glasses.js adds a Nexus card first among the cards; selecting it sets nexus='ring' and nexusRing() lays the names round an ellipse (offset half a step so nothing sits on the top or bottom, where long names collided), the chosen one bright in the middle. Selecting an area sets nexus=<id> and cards() returns only that area's apps plus a Back to the ring; back() steps area -> ring -> the Nexus card. No particles or depth: black is see-through. Also fixed: a voice 'open X' put appIndex at X's place in data.apps, which was off by one whenever a sync, welcome or Nexus card came first; it now finds X in cards().
