---
id: K-0465
kind: implementation
title: The greenhouse node takes one signed write: POST /mia/command (DEC-0185 step 2)
status: confirmed
by: claude
created: 2026-11-24T22:09:15+00:00
concerns: homestead/viewer/serve_exports.py, homestead/core/command_auth.py, core/greenhouse_provision.py
from: dec:DEC-0185
---
homestead/viewer/serve_exports.py accepts POST /mia/command only with --db; homestead/core/command_auth.py verifies X-MIA-Timestamp (within 300 s), X-MIA-Nonce (16-64 safe chars, kept in mia_command_nonces for 2x the window; a repeat is a replay) and X-MIA-Signature = HMAC-SHA256 over timestamp, nonce and body, compared in constant time, before the JSON is even parsed; then core/mia_commands.submit. Body capped at 4096 bytes. The key is config/mia_command_key (git-ignored, 32 bytes hex); no key refuses all. MIA makes it once in data/.keys/greenhouse_command_key and push_node sends it last over SSH stdin (umask 077). Watch: reply() called push_node without run_input, so the existing test would have run real ssh and written a real key; threaded through and isolated COMMAND_KEY in the test.
