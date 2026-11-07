---
id: K-0072
kind: implementation
title: The Toolbox on the web: calculators worked out in core, alarms as actions
status: confirmed
by: claude
created: 2026-11-07T17:54:16+00:00
concerns: core/toolbox_calcs.py, core/unit_conversion.py, core/web_toolbox.py, core/toolbox_actions.py, core/assistant_toolbox_actions.py, web/toolbox.js, core/capabilities.py
from: dec:DEC-0125, dec:DEC-0113
---
The Toolbox's math lived inside its Qt calculator files, which import PySide6 at the top, so neither the web nor a test without Qt could reach it. Moved it to core: Ohm's law solve() and the new ohms_law (any two of three, power, metric-prefixed words like 54.5 mA), board_feet and concrete_volume in core/toolbox_calcs.py; the unit tables in core/unit_conversion.py. The Qt files re-export them, the voice tools import from core, and tests/test_ohms_law.py and test_unit_converter.py now run without Qt. core/web_toolbox.py serves the page (/api/toolbox) and calc() (/api/toolbox/calc, read-only, never raises: plain-word errors) so the page never does arithmetic; it asks 250 ms after the last keystroke and draws only the newest answer. Alarms got actions (alarm.add/switch/delete, core/toolbox_actions.py, clock_time reads '7:30 pm', '730am') and a switch_alarm voice tool; board feet and concrete got voice tools too (core/assistant_toolbox_actions.py). The demo can't calculate, so the example carries demo_answers. Watch: core/capabilities.LIMITS said 'No web screen yet' for Power and Toolbox; tests/test_capabilities.py catches that once a page exists, so change LIMITS with the page.
