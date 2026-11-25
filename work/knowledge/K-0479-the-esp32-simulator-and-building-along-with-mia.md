---
id: K-0479
kind: implementation
title: The ESP32 simulator and building along with MIA
status: confirmed
by: claude
created: 2026-11-25T07:43:04+00:00
concerns: core/esp32_sim.py, web/labsim.js, core/assistant_turn.py, core/assistant_chat.py, core/paths.py
from: commit:bce80a9f
---
Zac (2026-11-25) liked the ESP32 labs site most for its simulation: building and testing hardware in a simulator, and wanted MIA to walk him through building alongside it. core/esp32_sim.py is pure logic: each lab's circuit (parts, the sketch's pin, build steps with why), his wires joined into nets (union-find), each part judged as it would behave (an LED through a resistor graph: lit, backwards, overdriven; a pot; three-wire modules; shorts, EN held low, serial pins), and a run that produces the sketch's own MIA lines, judged by esp32_path.judge like the real board. A sim run is never an attempt: only the board passes a check. The page is web/labsim.js (an SVG breadboard, wires kept in localStorage per lab, POST /api/labs/{course}/sim). By voice: build_along (position kept on the path: PathBook.build_at/set_build) and simulate_lab (prompt_arg question, so direct_lookup answers it in code).

What the live checks taught: question plans took "walk me through building the pot lab" (project picture) and "next step" (progress), so the build is taken in code before the plans (esp32_sim.reply, as trade jobs are), "next" only right after a step and only when nothing else is said; "How do I wire the relay lab?" counted as a how-to about MIA because "lab" is the Data Logger's keyword, fixed in about_mia for how-tos (not teach-mes: "teach me how to use the mission board" must stay hers); with a build in the history the model answered "what will it print?" from memory, so code answers it. Patch text with a backslash never goes through a bash heredoc (it happened twice here).
