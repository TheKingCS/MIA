---
id: K-0169
kind: implementation
title: Made by MIA by voice: the screens' actions through the same code
status: confirmed
by: claude
created: 2026-11-09T07:47:00+00:00
concerns: core/assistant_creation_actions.py, core/application.py, core/core_runtime.py, core/web_surfaces.py, tests/test_creations.py
from: dec:DEC-0091, dec:DEC-0125
---
DEC-0091/DEC-0125, 2026-11-09, from the self-audit's 'no Assistant tool reads it' on creations. core/assistant_creation_actions.py: list_creations reads the store; make_creation calls creation_maker.make (a private draft, no data changed; the local model writes the design, so a test patches creation_maker._ollama); publish, rollback and retire find the creation by its title and run the creation.* action kinds through assistant_goods_actions._run, so Undo covers them. The new 'creations' domain had to belong to an app (tests/test_web_surfaces: every tool's domain is an app's); it went on the MIA Assistant app, since Made by MIA is reached from the shell, not an app of its own.
