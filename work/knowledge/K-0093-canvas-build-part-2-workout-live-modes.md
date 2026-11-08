---
id: K-0093
kind: implementation
title: Canvas build part 2: Workout live modes
status: confirmed
by: claude
created: 2026-11-07T14:42:36+00:00
concerns: web/workout.js, core/training_session.py, web/ui.css
from: dec:DEC-0113
---
What: web/workout.js shows the live training session as the canvas draws it: Active (one set in focus, the count large, how it was counted beside it), Rest (a ring draining from rest_total), Done (planned against done, how each was counted) as a full-screen layer over the page; Today leads with one big Start. How: core/training_session.view() gained each count's how, last_counted, weight and rest_total, so web/ computes nothing; the overlay is redrawn from MIA.fitness() like every page. Why: DEC-0113 approved with the design canvas as the reference; workout.md asks for one thing in focus and 56 px targets. Watch: a count is never shown as verified; +30 s on rest has no action yet.
