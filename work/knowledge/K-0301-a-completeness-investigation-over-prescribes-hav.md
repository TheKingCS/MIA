---
id: K-0301
kind: lesson
title: A completeness investigation over-prescribes: have two independent reviewers cut it down
status: confirmed
by: claude
created: 2026-11-18T13:41:39+00:00
concerns: docs/mia_os/MIA_LIVING_SYSTEM_GAP_ANALYSIS.md
from: file:docs/mia_os/MIA_LIVING_SYSTEM_REVIEW.md, dec:DEC-0285
---
Prompt 21 (2026-11-18). The first draft answered every gap with a framework: a hybrid logical clock for sync, a compensation framework for multi-store changes, runtime-enforced timeouts on 800 capabilities, contradiction detection in code over free-text memories, a dated restore of learned habits, durable events in the history, one ten-stage engine. A fresh Fable reviewer and Codex, independently, found each either not implementable here (synchronous Python cannot be cut off mid-write; free text has no attribute to compare), overbuilt for a two-device star, or a risk to a safeguard (a dated restore can bring back what he took back; history that syncs and is never rewritten cannot hold device-only facts). What survived was small joins: a trace id, a declaration, a few lines that restore before-images on failure. Build the small join; wait for three uses before a framework.
