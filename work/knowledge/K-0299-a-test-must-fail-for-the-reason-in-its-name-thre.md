---
id: K-0299
kind: test-procedure
title: A test must fail for the reason in its name: three ways the old ones didn't
status: confirmed
by: claude
created: 2026-11-18T11:00:05+00:00
concerns: tests/test_recall_index.py, tests/test_activity_watch.py
from: commit:eec85f3b, file:tests/test_observation_review.py
---
Fable's review of 2026-11-18 found tests that passed without checking their claim: one returned early when an embedding model happened to answer on the machine; one asserted a file existed where its name said sealed and private; one used the only window title that contains the word incognito; two asserted a candidate's urgency where their names said it was never dropped. Check a new test by breaking the code it guards and watching it fail; never branch on what the machine happens to have; use real inputs, not the one that fits the rule.
