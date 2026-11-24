---
id: K-0432
kind: test-procedure
title: The trigger overlap ratchet
status: confirmed
by: claude
created: 2026-11-24T16:07:26+00:00
concerns: tests/test_trigger_hygiene.py, work/trigger_overlap_baseline.json
from: dec:DEC-0104
---
tests/test_trigger_hygiene.py now holds the trigger audit as a test: every tool: phrase that fires inside a routing-corpus or everyday-phrasing sentence meant for another domain, against work/trigger_overlap_baseline.json (33 known on 2026-11-24, mostly a second tool offered beside the right one). A new overlap fails; narrow the phrase, or when it is meant, run the file with MIA_TRIGGER_BASELINE=1 to write it in.
