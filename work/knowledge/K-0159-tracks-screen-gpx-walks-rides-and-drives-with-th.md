---
id: K-0159
kind: implementation
title: Tracks screen: GPX walks, rides and drives with their shapes
status: confirmed
by: claude
created: 2026-11-09T08:11:28+00:00
concerns: core/web_tracks.py, web/tracks.js, web/tracks.html, core/gps_tracks.py
from: dec:DEC-0099
---
GPX tracks (core/gps_tracks.py) could only be added by `python -m tools.tracks`. web/tracks.html in Recreation (core/web_tracks.screen, /api/tracks) shows the totals for 30 days and all time and each track newest first with its numbers and its shape: core/web_tracks.shape() draws an SVG path from at most 160 of its points, north up, longitude scaled by cos(latitude) so it isn't stretched, fitted in a 100 square. Add a Track reads a GPX file in the browser and sends its text as track.add (describe parses it first, so a file that isn't GPX is refused before approval; 4 MB cap); Delete is track.delete. Both undoable through atomic_write_text.
