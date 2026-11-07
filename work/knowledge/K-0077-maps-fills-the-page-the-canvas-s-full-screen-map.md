---
id: K-0077
kind: implementation
title: Maps fills the page (the canvas's full-screen map)
status: confirmed
by: claude
created: 2026-11-07T18:16:50+00:00
concerns: web/maps.js, web/maps.html, web/ui.css
from: dec:DEC-0113
---
web/maps.js stage(): the map view fills a section the height of the window; a glass header floats at the top (the map's name, Offline · USGS Topo or OpenStreetMap · zoom, the Topo / vector-area switch), 48 px buttons on the right (zoom in, zoom out, show the waypoints, keep this area offline; on a vector area zoom and take it off, MapLibre's own control removed so there's one set of buttons), and the route card floats along the bottom. The page's plate is hidden on Maps (body.mod-maps .hero: it needs the body selector to beat concept.css's body[data-app] .hero). Fixed on the way: maps.html set data-icon=assistant, so Maps wore Talk's speech-bubble icon.
