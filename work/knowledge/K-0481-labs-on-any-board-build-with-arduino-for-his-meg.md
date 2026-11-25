---
id: K-0481
kind: implementation
title: Labs on any board: Build With Arduino for his Mega and Nanos
status: confirmed
by: claude
created: 2026-11-25T08:46:21+00:00
concerns: core/boards.py, core/arduino_path.py, core/esp32_sim.py, core/esp32_lab.py, core/lab_page.py, web/labsim.js, web/course.js
from: commit:9b6635a7
---
Zac has an ELEGOO MEGA R3 kit and several Nanos. core/boards.py makes boards data (pins as printed, logic voltage and rail, ADC top, supplies, input-only and serial pins, USB chips, PlatformIO platform and board id, baud). The simulator (core/esp32_sim.py) carries the board and course in ContextVars set by the public calls that take course=/board_id= (an _in_course decorator), so the ESP32 code path and its tests stayed unchanged while the Arduino's circuits (ARDUINO_CIRCUITS) run on 5 V and a 10-bit ADC; parts with no rules of their own are judged against their own build steps (_by_build). The bench (core/esp32_lab.py) takes course and board everywhere; course_in reads the course from his words. Build With Arduino (core/arduino_path.py) uses only pins both boards share, Serial.print at 9600 (no printf on AVR).

Learned: checks_of must match the marker followed by a space or quote (MIA DIST vs MIA DIST_NONE); a program's words must be unique (the ESP32 course had claimed "arduino"); in the full turn the model answered "what's my next Arduino lesson?" in its own words (and the progress plan invented a lesson), so a board course's next lesson is answered in code (esp32_lab.next_lab_reply) and the progress plan's NOT_FOR has the learning words.
