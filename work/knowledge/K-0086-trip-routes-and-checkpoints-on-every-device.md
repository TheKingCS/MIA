---
id: K-0086
kind: implementation
title: Trip routes and checkpoints on every device
status: confirmed
by: claude
created: 2026-11-08T01:19:43+00:00
concerns: core/trip_route.py, core/assistant_trip_route_actions.py, core/web_more.py, web/expeditions.js
from: commit:e22f3e9, dec:DEC-0125
---
core/trip_route.py turns the desktop trip dialog's route (waypoint_ids) and splits into route_card(): stops in order, reached, next, legs with km, time and pace. Reached is worked out in order (reached_in_order), not as a set, so an out-and-back route with the start twice is not finished by the first checkpoint; that is also why trip.route_add allows a stop already on the route and says "again (on the way back)". Voice (core/assistant_trip_route_actions.py) runs the same action kinds; with no trip named it uses the one trip underway and asks when there are none or several.
