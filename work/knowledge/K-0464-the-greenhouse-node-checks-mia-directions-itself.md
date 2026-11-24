---
id: K-0464
kind: implementation
title: The greenhouse node checks MIA directions itself (DEC-0185 step 1)
status: confirmed
by: claude
created: 2026-11-24T21:59:08+00:00
concerns: homestead/core/mia_commands.py, homestead/config/command_limits.yaml
from: dec:DEC-0185
---
homestead/core/mia_commands.py checks a direction against homestead/config/command_limits.yaml, which MIA cannot edit: only the four pH/EC target-band parameters the cell reads from target_overrides today, fish-safe hard limits (pH 6.0-7.6, EC 300-2000), a kept band between min and max, believed-current equal to the real current target (stale otherwise), at most one change per parameter per cell per hour. Every decision is a mia_commands row; a pass is a parameter_change_proposals row, approved on the node (approval node, default until 0zu) or at once through ExperimentManager.approve_parameter_change (approval mia), so it lands as a target_overrides row the cell reads. Six mia_command_* scenarios. Homestead needs its own venv (pyyaml) and a fresh mia_homestead.db for self_audit. Also fixed: the two generated docs were written in the Windows codepage (em dashes broken); now utf-8 with LF. Watch: sed in Git Bash turned a backslash-n into a real newline; edit with a script file.
