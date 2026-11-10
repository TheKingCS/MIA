---
id: K-0197
kind: debugging
title: Two tests wrote into the real data folder and repo root
status: confirmed
by: claude
created: 2026-11-10T08:58:24+00:00
concerns: tests/test_glasses.py, tests/test_at_rest.py
from: commit:5697f59c, file:tests/conftest.py
---
The glasses every-panel test reached PC Health, which ran a real inspection of the PC and saved it in data/inspections; the sealed-store test gave its stores MagicMock() as context, so FinanceManager made a watched folder named after the mock in the repo root. Fixed with a stand-in inspection, inspection._DIR redirected in conftest, and a context whose config.get returns defaults and a temp folder. The conftest guard is what caught it: the suite passed but exited 1.
