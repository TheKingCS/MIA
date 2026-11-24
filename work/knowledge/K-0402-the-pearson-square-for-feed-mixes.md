---
id: K-0402
kind: implementation
title: The Pearson square for feed mixes
status: confirmed
by: claude
created: 2026-11-24T11:30:54+00:00
concerns: core/feed_mix.py
from: commit:bdb7e90e
---
core/feed_mix.py: parts of the low feed are high minus target, parts of the high feed target minus low; the target must lie strictly between the two, else MixError in words (never a forced mix). read() picks the three percentages (the target after to/get/make/for, else the last) and a batch in lb or kg. feed_mix is read-only (flock domain).
