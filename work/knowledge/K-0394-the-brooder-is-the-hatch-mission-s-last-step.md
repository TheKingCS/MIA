---
id: K-0394
kind: implementation
title: The brooder is the hatch mission's last step
status: confirmed
by: claude
created: 2026-11-24T10:05:00+00:00
concerns: core/hatch_tracker.py
from: commit:c94d7ceb
---
core/hatch_tracker.plan adds a brooder step the day after hatch: about 95 F (35 C) the first week for chicks, poults, keets and quail, 90 F for waterfowl (BROODER_START_F), 5 F cooler each week until feathered (about six weeks), and how to read them (huddled is cold, spread to the edges is hot).
