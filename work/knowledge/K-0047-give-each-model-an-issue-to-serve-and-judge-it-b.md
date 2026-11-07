---
id: K-0047
kind: method
title: Give each model an issue to serve, and judge it by that issue
status: confirmed
by: claude
created: 2026-11-07T05:35:25+00:00
concerns: core/model_forge.py, core/loops.py
from: dec:DEC-0106, file:core/model_forge.py
---
What: every model the forge makes names what it serves on its card (loop:answers.no_tool, project:..., mission:..., gap:...). PLAYBOOK in core/model_forge.py says which kind of small model could move which loop: a router for requests reaching the wrong tool, a classifier for messages that aren't welcome or documents of the wrong type, an extractor for fields read wrong, a forecaster for numbers and dates she guesses, a scorer for answers that land badly. opportunities() lists the slipping loops a model could help with.
Why: a model with a good test score can still change nothing that matters. Tying it to an issue means the question is always whether the issue got better, read from the loop that already measures it. It also answers what to build next: whichever loop slips, the playbook names the kind of model to try.
How MIA uses it: python -m tools.model_forge needs. A test checks every loop the playbook names still exists.
