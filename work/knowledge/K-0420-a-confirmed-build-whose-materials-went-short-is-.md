---
id: K-0420
kind: implementation
title: A confirmed build whose materials went short is said once
status: confirmed
by: claude
created: 2026-11-24T14:23:43+00:00
concerns: core/project_ripple.py, core/unusual.py
from: dec:DEC-0171
---
Step 3 of docs/future/UNIFIED_INTELLIGENCE.md for builds: core/project_ripple.gone_short, run in the unusual daily check, keeps each confirmed build plan materials fully on hand in the config (planner.covered); one covered at the last check and not now is said once (the key names the plan, the materials and the day), and the new covered set becomes the baseline so it is not repeated. The first check for a plan only remembers. Completed projects and drafts are skipped.
