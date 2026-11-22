---
id: K-0327
kind: implementation
title: The capability truth registry: a record per app, its state from evidence
status: confirmed
by: claude
created: 2026-11-22T13:30:37+00:00
concerns: core/capability_registry.py, core/diagnostics.py, web/diagnostics.js
from: task:WP-08, dec:DEC-0220
---
WP-08 (DEC-0220, REQ-SLF-003/004/005). core/capability_registry.records() builds one record per app from its manifest (services, permissions, tools, action kinds, devices with the parity decisions), the tests that cover it (a test file named after it, or one naming a tool or action kind in quotes), the turn traces (last use of one of its tools), the Fix-It Log (last tool error), capabilities.LIMITS and capability_status. _decide is pure: malfunctioning from a failure with no use since, degraded while orb_state holds offline for one used by words, unverified with no test and no use in 30 days. rebuild() keeps only last states and the changes with their evidence in capability_states.json (device), written only when a state changed: every write moves the live version and pages re-read, so writing each look would loop with Diagnostics open. No other module names the file; a test checks the one write is in rebuild().
