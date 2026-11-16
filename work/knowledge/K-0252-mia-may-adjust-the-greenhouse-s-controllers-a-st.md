---
id: K-0252
kind: decision
title: MIA may adjust the greenhouse's controllers; a stop never touches the greenhouse
status: confirmed
by: claude
created: 2026-11-16T06:05:14+00:00
concerns: core/greenhouse_link.py, homestead/, docs/mia_os/MIA_OS_AUTONOMY_AND_TRUST_REQUIREMENTS.md
from: dec:DEC-0185, dec:DEC-0150, dec:DEC-0181
---
Zac (Q-40, 2026-11-16): "MIA absolutely should be able to adjust greenhouse controllers but stop shouldnt effect this like you said." This amends DEC-0150 (she only watched). DEC-0185: adjustments to targets, schedules and modes are device commands through capabilities, asked for unless granted, applied by the node within the safety microcontroller's hard limits (which may refuse), reported only on the node's confirmation, recorded with how to put them back. Stop and stop everything leave the greenhouse running and its settings in place; only an unsent adjustment is cancelled. Not built: core/greenhouse_link.py only watches; REQ-FUN-103 (R1) starts with the node's command interface and limits, tested against homestead/'s simulator.
