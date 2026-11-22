---
id: K-0335
kind: lesson
title: Two tests wrote into the real data folder, unseen in the pass count
status: confirmed
by: claude
created: 2026-11-22T15:12:12+00:00
concerns: tests/conftest.py, tests/test_phone_ready.py
from: task:WP-04, task:WP-08
---
2026-11-22. The suite's session-end check prints 'Tests wrote into the real data/ folder...' on the progress line and exits 1, but the summary still says 'N passed': filtering a run's output for passed/failed hides it. Two leaks: (1) tests opening Diagnostics rebuilt the capability registry into data/ (only the Linux suite ran that path; tests/conftest.py now points capability_registry._DATA_DIR at the test folder); (2) tests/test_phone_ready.py runs a script in a fresh Python, which skips conftest: once missions.json was sealed (WP-04) it made a data key in data/.keys (the script now sets at_rest.KEY_DIR and a test key). Found by halving the suite. When sealing a store, check subprocess tests that write it.
