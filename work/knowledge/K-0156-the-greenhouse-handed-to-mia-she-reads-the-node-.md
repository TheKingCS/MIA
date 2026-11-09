---
id: K-0156
kind: implementation
title: The greenhouse handed to MIA: she reads the node, the node acts; device steps wait for a yes
status: confirmed
by: claude
created: 2026-11-09T03:50:30+00:00
concerns: core/greenhouse_link.py, core/greenhouse_provision.py, homestead/viewer/serve_exports.py, core/trade_jobs.py, tests/test_greenhouse.py
from: dec:DEC-0150, dec:DEC-0145
---
DEC-0150, 2026-11-08. The homestead merge was verified before pushing (MIA's suite unchanged at 5,955; the node's scenarios 242 of 245 with a scratch venv for pyyaml, the 3 needing rsync); the push itself was held by the session's safety check, so it waits for Zac. MIA can't import the node's code (both have a `core` package), so she reads its generated documents (FEATURES_AND_CAPABILITIES.md, HARDWARE_BOM_LIVE.md) and its dashboard export instead. The node had no server and the home snapshot had no readings, so homestead/viewer/serve_exports.py serves exactly dashboard_state.json and home_snapshot.json read-only (refresh off by default: main.py already rewrites them every cycle). core/greenhouse_link.py reads only from an address on the person's own network, with a 3 s timeout (it runs on the app's 5-minute check, so the cadence is 4 minutes), raises each alert once, and keeps readings every 30 minutes a sensor (EC converted from uS/cm). core/greenhouse_provision.py: PlatformIO upload and an SSH push, both behind a 'yes, ...' phrase, every command through an injectable run with no window, configs written from the node's templates with comments kept and the SMTP password left empty, into gitignored data/. The node's self_audit couldn't run here: its repo database has no capability tables until main.py runs, and main.py would rewrite the tracked database.
