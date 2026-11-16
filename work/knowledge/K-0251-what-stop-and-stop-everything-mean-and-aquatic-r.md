---
id: K-0251
kind: decision
title: What 'stop' and 'stop everything' mean, and Aquatic read from Zac's picture
status: confirmed
by: claude
created: 2026-11-16T05:58:46+00:00
concerns: docs/mia_os/MIA_OS_AUTONOMY_AND_TRUST_REQUIREMENTS.md, docs/mia_os/MIA_OS_APPEARANCE_ENGINE.md
from: dec:DEC-0181, dec:DEC-0183
---
Zac (Q-34) asked for 'stopping everything' to be specified. Written in docs/mia_os/MIA_OS_AUTONOMY_AND_TRUST_REQUIREMENTS.md section 4: two commands recognised in code on every device; 'stop' ends the current turn's work, 'stop everything' also pauses her own initiative (her skill runs, workflows, agents, outward jobs, unprompted messages) until 'carry on' or a named time, surviving a restart; a step already writing finishes, nothing further starts, nothing is undone automatically, a pending browser commit is discarded. Never stopped: alarms, the safety floor, backups, sync, monitoring, his own requests. Not hers to stop: the homestead node's control loop, devices' states, the OS. Waits on his confirmation (Q-40).
Aquatic (Q-37) is based on his reference picture, cropped (no phone status bar) into docs/design/reference/prompt24_glass_dashboard.jpg; its palette read with Pillow's median-cut quantisation: edge glow #7fddec to #23c4e8, glass #2b323c to #33434d, charts #23c4e8 to #3f79e5 to #5955cb, progress #567fd8 on #12223c. The glow belongs to the shell's frame (deep tier), not every card.
