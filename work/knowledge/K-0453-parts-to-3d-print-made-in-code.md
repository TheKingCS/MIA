---
id: K-0453
kind: implementation
title: Parts to 3D print, made in code
status: confirmed
by: claude
created: 2026-11-24T19:18:15+00:00
concerns: core/print_parts.py, core/assistant_project_plan_actions.py
from: dec:DEC-0058
---
First step of the engineer plan's printing part: core/print_parts.py writes binary STL itself (no OpenSCAD on his PC; Bambu Studio is): an enclosure from the inside size (open box of floor and four walls as overlapping boxes, which slicers merge; a lid plate with a lip 0.4 mm inside the walls) and a round spacer. Sizes read in mm or inches; files in the household's prints folder; the most plastic as solid volume and PLA grams. Holes are not cut yet (solids only): said, for the slicer or a drill. The tool design_print_part lives in the Workshop app.
