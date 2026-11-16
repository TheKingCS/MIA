---
id: K-0272
kind: implementation
title: M7, first half: MIA Forge's scaffold for a new app
status: confirmed
by: claude
created: 2026-11-16T18:21:13+00:00
concerns: core/app_scaffold.py, tools/new_app.py, tests/test_app_scaffold.py, core/capabilities.py, core/app_registry.py
from: dec:DEC-0175, task:M7
---
What: core/app_scaffold.py and tools/new_app.py. AppSpec (id, name, area, tagline, description, ask, icon, group) -> plan() -> write(). Creates apps/<id>/manifest.json (no capabilities, next free order), web/<id>.html and .js on the frame, tests/test_app_<id>.py. Changes, each located with ast (never by text search) and added as the last element: WEB_ONLY (web_surfaces), the area's members tuple (web_areas), LIMITS and OVERVIEW_SKIP (capabilities), NOT_ON_GLASSES (glasses); and by JSON: work/parity.json (<id>:voice and <id>:glasses as todo), docs/schema/shell.example.json and apps.example.json. Everything is computed before the first write, so a refusal writes nothing; a changed file keeps its line endings.

How the list of places was found: scaffold a demo app in a scratch worktree and run the full suite. Eight tests failed the first time; each named a place a new app must be listed. Do the same when adding a kind of thing the scaffold should make (a store, a tool).

Why placeholders: OVERVIEW_SKIP, NOT_ON_GLASSES and the two todo decisions are the honest 'not yet' placements; capabilities.capability_status then reports the app as partial and its voice and glasses as planned, so MIA says so herself. The manifest's ask is left empty because test_parity requires an ask to reach the app's own tools.

What went wrong: test_self_knowledge asserted no limit line contains 'on the glasses', which any planned glasses card broke; it now checks the line it meant ('Not available on the glasses'). 'Seed Bank on the voice' became 'by voice' (capabilities._way). A test that scaffolds 'seed_bank' fails in a tree that already has one: the tests use 'scaffold_probe'.

Not built: generation in the lab (dev_lab running a model on the scaffolded worktree), a voice or screen way to ask for an app, scaffolding a store or a tool.
