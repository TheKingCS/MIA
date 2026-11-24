---
id: K-0456
kind: debugging
title: Eight review findings on the printed parts
status: confirmed
by: claude
created: 2026-11-24T19:44:33+00:00
concerns: core/print_parts.py, core/slicing.py
from: commit:92914278
---
Review of f39bd906..92914278: in read the word in as inches (80x50x30 mm in the garden became 2 m); stray numbers (ESP32, M3, a 2 mm wall) were taken as sizes; a cable hole on a low box made inverted pieces; posts collided with the lid lip on low boxes; Bambu names (X1 Carbon, P1S, A1 mini) missed their profile codes and other nozzles used the 0.4 process; box and lid on one plate failed past the bed; a reused output folder could report old G-code; names overwrote earlier parts; print me a caught an invoice. Now each number takes its own unit, numbers glued to letters and walls are skipped, holes and posts only where they fit, MODELS maps names, a non-0.4 nozzle is refused, each part slices alone in a fresh folder, names never collide, and the triggers are narrowed.
