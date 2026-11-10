---
id: K-0160
kind: implementation
title: Voice for screens that had none: look it up online, what isn't working, past conversations
status: confirmed
by: claude
created: 2026-11-09T08:14:32+00:00
concerns: core/assistant_screen_tools.py, core/application.py, core/core_runtime.py
from: dec:DEC-0125, dec:DEC-0053
---
core/assistant_screen_tools.py registers four tools on both the desktop (core/application.py) and the headless core (core/core_runtime.py): look_up_online (the person asking is the yes core/online_lookup.OFFER waits for; results through online_lookup.said, sources and dates, marked as from the web; LookupUnavailable's words when it can't), get_app_status (core/capabilities.status_summary; 'what's not working' stays check_my_setup's, so its phrases are 'what isn't working', 'what's broken', 'are any of your apps broken'), list_past_conversations and find_in_conversations (kept messages only; private and off-the-record ones were never written). Seven lines added to tests/assistant_routing_corpus.py. docs/ASSISTANT_CAPABILITIES.md needs `python -m tools.dump_assistant_capabilities` on the PC (it imports PySide6), not run here. Trail maps already had voice (list_trail_maps and friends).
