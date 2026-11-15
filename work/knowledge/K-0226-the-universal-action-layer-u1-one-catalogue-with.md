---
id: K-0226
kind: implementation
title: The Universal Action Layer U1: one catalogue with tiers, captures always untrusted
status: confirmed
by: claude
created: 2026-11-15T10:28:45+00:00
concerns: core/ual.py, core/assistant_ual_actions.py, web/shell.js, server/app.py
from: dec:DEC-0165
---
core/ual.py holds the capture contract (Capture.from_dict, kind_of, framed with OUTSIDE_MARK), the catalogue (ActionSpec: inputs, tier read/prepare/act, where local/online/cloud, output, ready) and offer()/run(). Tiers are enforced in code: spec_problems() rejects a read or prepare action that names an action kind and an act action that runs here; run() turns an act pick into a proposal on core/actions (approve executes, undo after). Nothing online is ready or offered until the person's switch (ual.online) and never for a capture from a sensitive MIA screen. Front doors only capture and show: /api/ual/offer, /api/ual/run, the Ctrl+K palette in web/shell.js (page selection or 80+ pasted characters), voice tools in core/assistant_ual_actions.py (domain ual, owned by the assistant app). Five actions are ready (find_known, save_inbox, make_mission, make_project, remember); the rest are listed as planned so offer() can say what's coming. Lesson: a new tool domain must be listed on an App in core/web_surfaces.py (test_every_assistant_tool_belongs_to_an_app).
