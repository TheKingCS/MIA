---
id: K-0172
kind: implementation
title: What MIA runs on: a service map beside the life graph, never in it
status: confirmed
by: claude
created: 2026-11-09T08:16:31+00:00
concerns: core/service_map.py, core/assistant_turn.py, tests/test_service_map.py
from: dec:DEC-0151, task:T-0007
---
T-0007 / DEC-0151 (proposed), 2026-11-09. core/service_map.py lists the services and devices with what each powers, what still works without it and what it needs; links() gives them as derived DEPENDS_ON links (core/links.Link), walked like links.downstream, but never added to links.derived_links, so the Life State's 'what waits on what' and the connections loop stay about the person's life. Checks only look; Tesseract and PlatformIO use their own finders (core/ocr.available, greenhouse_provision.platformio), since shutil.which missed a Tesseract installed in Program Files. What went wrong: the first version was written over core/self_knowledge.py (DEC-0142's 'what she is', a committed file with no local changes) because the name was taken; restored from git at once, and the map renamed core/service_map.py. Check a name with Glob before Write.
