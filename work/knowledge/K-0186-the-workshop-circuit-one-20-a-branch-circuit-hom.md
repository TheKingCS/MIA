---
id: K-0186
kind: implementation
title: The workshop circuit: one 20 A branch circuit, homeowner only under a permit
status: confirmed
by: claude
created: 2026-11-09T04:42:45+00:00
concerns: core/trade_jobs.py, tests/test_trade_session.py
from: dec:DEC-0149
---
DEC-0149 WANTED, 2026-11-08 night. Scoped to a single 120 V branch circuit to a detached building because that is the case the NEC lets go without a grounding electrode at the building (250.32 exception) and with a snap-switch disconnect on residential property (225.36); anything more is a feeder and subpanel, a separate job, and the first step says so from the load. The panel phase proves dead with live-dead-live testing and warns that the main lugs stay live with the main off. Burial depths are given as Table 300.5's common values and sent back to the local office. The depth loop's test now finds the next unwritten job itself instead of naming it.
