---
id: K-0462
kind: implementation
title: Fixing a batch of jars put up with the wrong count
status: confirmed
by: claude
created: 2026-11-24T21:21:25+00:00
concerns: core/canning_fix.py, core/canning_shelf.py
from: commit:9c325fb6
---
The review of 9c325fb6 found jars canned could only go down by undo. core/canning_fix.py: jars.correct records one more canned event carrying the difference (negative when fewer) with ref pantry:<id>, never rewriting the history, and moves the pantry quantity by it (never below 0); recorded() sums a batch canned events. An unlock already earned stays (unlocks are for good). Kitchen pantry shows Fix Jar Count on a home-canned batch (home_canned from the canning MARK); voice: fix_jar_count by food name, the newest batch.
