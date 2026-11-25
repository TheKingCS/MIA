---
id: K-0482
kind: implementation
title: My Bench: his own parts, wired freely, checked by each part's spec
status: confirmed
by: claude
created: 2026-11-25T09:03:06+00:00
concerns: core/part_specs.py, core/free_build.py, web/bench.js, web/labsim.js, core/boards.py
from: commit:a336b1fe
---
Zac asked to tell MIA what hardware he has and simulate connecting it, with specs fetched online. His parts stay in the Component DB (core/component_manager.py); what a part is lives in core/part_specs.py (pins with roles, supply range, output level; built-in specs from datasheets, his own in data/labs/part_specs.json). A new spec is drafted from his own SearXNG's results (only the name leaves the PC), read by the model as untrusted web text, checked in code (clean: roles, sane volts, power and ground) and kept only through the approved action partspec.add; never over a built-in one (by id or name). core/free_build.py judges a free build by those specs and core/boards.py's limits: the HC-SR04's 5 V echo into a 3.3 V pin is a stop with the divider fix. web/bench.html reuses web/labsim.js through options (check, key, noRun, checkTitle).

Learned: wires drawn over pins block clicking them (wires now on a layer beneath); a named part's pinout is answered in code (the model invented a tool); "what parts can I wire in the simulator?" still reaches three tools by "what parts" (the Component DB's, the asset list, part_specs), so the model decides and answered in text: a most-specific-phrase rule for direct_lookup would fix it, not built. SearXNG isn't running on this PC, so the web import says so until it is (docs/ONLINE_LOOKUP.md).
