---
id: K-0114
kind: implementation
title: An area's 3D room on the Nexus's engine, and re-renders
status: confirmed
by: claude
created: 2026-11-08T11:20:44+00:00
concerns: web/nexus3d.js, web/hub.js, web/nexus.js, web/spatial.css
from: dec:DEC-0130
---
The Garage's room (web/hub.js garageRoom) mounts the same engine as the Nexus (window.MIARoom = MIANexus3D) with shape 'bay' (a rounded-rectangle frame in the portal shader, uShape; art fitted cover-style to 3:2 before upload), fire 0.35, needsGlow (a pedestal turns amber when its item has overdue work) and art from MIA.image(photo). Arrival: nexus.js stores the portal's hue in sessionStorage 'mia.arrive'; the next page mounts with arrive, and the camera eases back out of the portal while its light fades. Lessons: (1) the first frame builds the shaders and can take seconds on a slow GPU, so time-based intros must start their clock after the first frame, not at mount; (2) MIAShell.start re-runs the render on every data change (refreshOnChange), so anything that mounts a canvas must keep a handle, stop() it (cancel the frame, lose the WebGL context, remove labels) and remount at the same index, and add document listeners once, or rooms stack up. Headless screenshots at 1600x900 take about 4 s each on SwiftShader, too slow to catch a 1.4 s animation; log the state per frame instead.
