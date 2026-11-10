---
id: K-0157
kind: implementation
title: The greenhouse setup as one sequence, each step done from the record
status: confirmed
by: claude
created: 2026-11-09T04:25:17+00:00
concerns: core/greenhouse_setup.py, core/greenhouse_provision.py, core/greenhouse_link.py, core/assistant_turn.py, tests/test_greenhouse_setup.py
from: dec:DEC-0150
---
DEC-0150, 2026-11-08, Zac: 'if we are setting up the greenhouse and I ask what is next is she able to tell me what device to flash'. The pieces were separate phrases; core/greenhouse_setup.py orders them (STEPS) and works out where you are from what's recorded, never a counter: trade_finished events for the jobs, mcu_flashed and node_pushed (now recorded by greenhouse_provision.reply when a flash or push finishes), PlatformIO found, the key and PI_SETUP.md, the node read. 'done' only counts for a step only the person can see (the SD card); a later step done proves an earlier one like that. Bare 'what's next?' is only taken once the setup has started, and a live job's own 'next' still comes first (job_reply runs before it). Once finished, 'done' is let go for other uses.
