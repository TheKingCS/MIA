---
id: K-0477
kind: decision
title: Interactive labs: one standard for teaching, Build With ESP32 first
status: confirmed
by: claude
created: 2026-11-25T06:44:03+00:00
concerns: core/esp32_path.py, core/paths.py
from: file:docs/future/INTERACTIVE_LABS_PLAN.md, file:core/esp32_path.py
---
Zac asked for an interactive environment like an ESP32 lab site (paused when checked, so built from his description) and for it to be the standard for other teaching areas. The standard (docs/future/INTERACTIVE_LABS_PLAN.md): a lab is goal, parts, setup, do it, see it, check by evidence, try this, on the existing learning paths. Build With ESP32 (core/esp32_path.py) is six stages with Arduino sketches for esp32dev that print MIA <MARKER> <value>; the board_says verifier passes a check from the serial output (seen, min, spread, range). Found by a test: the line parser let whitespace run across a newline, so MIA WIFI_WAITING swallowed the next line; values now same-line only. Next: build and flash a lab with PlatformIO on his yes and read the serial port; then the lab page.
