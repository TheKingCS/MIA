---
id: K-0249
kind: decision
title: MIA OS Prompt 04: requirements as checked rows, a generated matrix, targets from measurements
status: confirmed
by: claude
created: 2026-11-16T05:35:42+00:00
concerns: docs/mia_os/MIA_OS_SYSTEM_REQUIREMENTS.md, tools/requirements_matrix.py, tests/test_requirements_spec.py
from: dec:DEC-0179, dec:DEC-0180, dec:DEC-0181, dec:DEC-0182
---
What: sixteen documents in docs/mia_os (the philosophy, the product vision, the system requirements and six requirement documents, scenarios, the MVP, acceptance, open questions, risks, diagrams) and a generated traceability matrix. Each requirement is one 8-column row (ID, statement, MoSCoW priority, release tier, devices, status against the code, verification, sources → owner prompt); tools/requirements_matrix.py reads the rows and the scenarios' Exercises lines, checks them, and writes the matrix; tests/test_requirements_spec.py keeps it current.
Why this way: the prompt asked for every field per requirement; a row with a combined trace cell keeps 194 of them readable, and generating the matrix means it can't drift. Status was checked against files, never assumed; performance targets were set from measurements on the reference PC (Ollama timings: llama3.2 3B 4.1 s cold load, 0.3 s answer, 220 tok/s; qwen3 14B 11.2 s, 0.9 s, 73 tok/s; qwen2.5 32B 37 s, 3.4 s, 14 tok/s; engine import 0.5 to 1.7 s; assemble_life_state_v2 0.02 s) and marked provisional where only the image can measure them.
What to know: the prompt's seven autonomy levels map onto the five built tiers (DEC-0181 adds reversibility, reach and a stop instead of more levels). Conflicts found: the multi-user list against DEC-0119 (Q-36) and Ubuntu (HARDWARE.md) against Fedora Atomic (DEC-0157), left to Prompt 06's GPU test. The 32B's 14 tok/s looks low for a 24 GB card and is worth checking on Linux.
