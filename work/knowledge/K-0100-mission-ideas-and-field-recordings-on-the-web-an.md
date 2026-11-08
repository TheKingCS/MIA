---
id: K-0100
kind: implementation
title: Mission ideas and field recordings on the web and by voice
status: confirmed
by: claude
created: 2026-11-08T02:26:27+00:00
concerns: core/web_proposals.py, core/assistant_proposal_actions.py, web/missions.js, web/journal.js
from: dec:DEC-0125
---
The Qt Toolbox's Discovery and Field Captures moved to the pages they feed: MIA's Idea on Missions, From the Field on the Journal (core/web_proposals.py). Suggesting is not an action (nothing changes until the person accepts; DiscoveryManager still validates every skill id and works out the rewards in code); the four decisions are actions (mission_idea.accept/reject, capture.keep/discard) so undo covers them. Both POSTs (/api/missions/idea, /api/journal/captures/check) run the model or transcription in the threadpool with the turn lock inside. Field recordings are filtered to the signed-in person (or no one). Keeping a capture from the web does not run the desktop's background memory extraction; noted in the module. Tests reuse the managers' own test fixtures via fixture.__wrapped__.
