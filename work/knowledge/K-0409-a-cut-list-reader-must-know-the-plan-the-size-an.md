---
id: K-0409
kind: debugging
title: A cut list reader must know the plan, the size and the hay
status: confirmed
by: claude
created: 2026-11-24T12:37:57+00:00
concerns: core/assistant_plan_actions.py
from: commit:e8fdd726
---
A twenty-fourth fresh review of e8fdd726: first cut and the cuts for brought next_cut into hay questions and named it, so a hay answer could be replaced by a cut and his place moved; PlanLibrary.best gave the first plan on the shelf for the plan and a workbench for potting bench (a summary word); the cuts were the plan's default size while he built another; going back to a plan restarted it; a finished one named never started again; the place lived in config, which other code saves. Now title words must match, sizes are taken and kept, places live in memory for the run (_CUT_PLACES), and the triggers are the cut list's own words.
