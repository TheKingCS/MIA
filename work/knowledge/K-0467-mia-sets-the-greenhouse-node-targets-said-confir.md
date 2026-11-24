---
id: K-0467
kind: implementation
title: MIA sets the greenhouse node targets: said, confirmed, signed, read back (DEC-0185 step 4)
status: confirmed
by: claude
created: 2026-11-24T22:44:19+00:00
concerns: core/greenhouse_adjust.py, homestead/viewer/serve_exports.py
from: dec:DEC-0185
---
core/greenhouse_adjust.py: parse() reads pH/EC min/max and a value from his words; plan() fetches the node export fresh and takes the believed current value from mia_directions.targets, pre-checking against homestead/config/command_limits.default.yaml read by regex (MIA has no PyYAML; the node is what counts); reply() says the exact change and keeps link.pending until yes, set it; send() signs with the per-node key (greenhouse_provision.command_key_path, never creating one) and POSTs only to his own network, then says the outcome from the node answer and export. greenhouse.adjust (act_with_approval) is the Greenhouse Water tab control. A test loads homestead/core/command_auth.py by file path (stdlib only) so the node own verify checks what MIA signs; MIA never imports homestead packages (both have core). Live run against the real export server: staged, then a second change refused while waiting. Watch: the heredoc mangled backslashes in a regex once more (fixed via a Write-tool script).
