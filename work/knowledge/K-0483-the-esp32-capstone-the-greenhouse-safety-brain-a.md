---
id: K-0483
kind: implementation
title: The ESP32 capstone: the greenhouse safety brain as a watchdog lab
status: confirmed
by: claude
created: 2026-11-25T11:47:22+00:00
concerns: core/esp32_path.py, core/esp32_sim.py, core/lab_ask.py, web/labsim.js
from: commit:4c565a85
---
Stage 7 of Build With ESP32 (core/esp32_path.py, lab watchdog) is the greenhouse safety board in small: an LED for a dosing pump, a heartbeat typed as hb, a dose as dose, 15 s of quiet goes safe (pump off, doses refused), a heartbeat recovers, BOOT stops it for good. Its sketch never blocks (no delay in loop), the lesson homestead/firmware/safety_mcu learned the hard way. It touches nothing in homestead/: it only points at that firmware, whose own LED test is the greenhouse next milestone. The simulator runs it in esp32_sim._watchdog. Went wrong in the live check: the model took the heartbeat to guard the board, not the PC, until the lesson why said so plainly; and by voice, simulate the X lab and a why about a named lab went to the model, which answered from memory, so esp32_sim.reply takes both in code (the why through lab_ask.ask with record=False, from the lesson material).
