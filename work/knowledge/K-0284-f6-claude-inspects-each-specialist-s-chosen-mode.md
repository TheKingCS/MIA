---
id: K-0284
kind: implementation
title: F6: Claude inspects each specialist's chosen model
status: confirmed
by: claude
created: 2026-11-17T09:47:47+00:00
concerns: core/model_inspection.py, core/night_school.py, core/specialist_roster.py, tests/test_model_inspection.py, tests/test_night_school.py
from: dec:DEC-0200, task:F6
---
What: core/model_inspection.py. A choice is (specialist, model, fingerprint of that model's tools-mode results on the specialist's disciplines); pending() lists specialists whose choice has no verdict. inspect() builds the prompt in code (bench counts per discipline, up to 12 problems it didn't get right with expected and got, read from work/eng_bench/<model>.json rows), asks the inspector, and verdict_from() holds it to two rules: no pass against a failing bench (Choice.passed), and an unreadable reply is a hold. Verdicts append to work/inspections.json (work_path, so it ships with the code like the bench results). Night School step 7a1 inspects pending()[0] with her teacher before study hall (config 'inspections'). The roster gains 'inspected'; voice model_inspections.

What went wrong: test_night_school's night ran a real inspection against the real bench results and wrote work/inspections.json from a test; the fixture now stubs model_inspection.pending. Any new Night School step that reads real records needs the same stub. Also: a default argument path=RECORD binds at import, so monkeypatching RECORD did nothing; the functions take path=None and read RECORD at call time.

Not yet: gating the worksheet on cleared() (deliberately after the first inspections exist), and inspecting Forge-built code (F4).
