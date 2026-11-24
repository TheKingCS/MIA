---
id: K-0390
kind: decision
title: The safety floor knows the common indirect signs
status: confirmed
by: claude
created: 2026-11-24T09:21:39+00:00
concerns: core/safety_floor.py, tests/test_safety_floor.py
from: commit:e87d5526
---
The floor caught only direct words (kill myself, want to die). Prompted by the net-worth review (I feel like nothing, what am I worth anyway reached no safety check), it now also knows the commonly recognised indirect signs, each said of the person themselves: nobody would miss me / notice if I was gone, I would be better off gone, what is the point of living, my life is not worth living, cannot go on living, do not want to exist, wish I had never been born, want it all to end for good; with must-not cases said of things (nobody would miss this old truck, what is the point of this meeting). A false positive costs a caring message (the floor errs broad by design). Zac may want to read the list.
