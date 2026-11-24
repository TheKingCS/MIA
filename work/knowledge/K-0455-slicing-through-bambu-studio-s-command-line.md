---
id: K-0455
kind: implementation
title: Slicing through Bambu Studio's command line
status: confirmed
by: claude
created: 2026-11-24T19:34:11+00:00
concerns: core/slicing.py, core/print_parts.py
from: commit:201c78d7
---
core/slicing.py: the printer is read from Bambu Studio's settings (machine preset: a Bambu Lab P1P 0.4 nozzle on his PC), its stock machine, 0.20mm Standard process and PLA Basic profiles from the install's resources/profiles/BBL, and bambu-studio.exe --slice 0 --load-settings machine;process --load-filaments filament --outputdir --export-3mf run with no window. About a second a part; Bambu read MIA's enclosure at its exact size with no warnings (84 x 54 x 32 mm, 40 min). The stock filament leaves density 0 on the command line, so grams are worked out from the G-code's filament length (1.75 mm, PLA 1.24). Git Bash could not launch the exe (exit 127); subprocess with a list of args works. Never run in a test.
