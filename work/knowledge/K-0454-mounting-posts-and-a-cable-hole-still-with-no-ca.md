---
id: K-0454
kind: implementation
title: Mounting posts and a cable hole, still with no CAD
status: confirmed
by: claude
created: 2026-11-24T19:25:45+00:00
concerns: core/print_parts.py
from: commit:f39bd906
---
core/print_parts.py: posts are hollow tubes (outside, bore, both end rings) on the floor at a board's hole spacing, centred, 6 mm across with a 2.5 mm bore an M3 self-taps in PLA, left out when they would not fit inside; a cable hole is the end wall built as four boxes around an 8 x 6 mm slot above the floor, so no boolean is needed. A test checks every shape's signed volume is positive (faces point out), the thing a slicer needs to read it as solid.
