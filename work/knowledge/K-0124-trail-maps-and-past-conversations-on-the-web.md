---
id: K-0124
kind: implementation
title: Trail Maps and past conversations on the web
status: confirmed
by: claude
created: 2026-11-08T15:58:13+00:00
concerns: core/web_trails.py, core/trail_map_library.py, core/web_conversations.py, web/assistant.js, server/app.py
from: dec:DEC-0017, dec:DEC-0125
---
Two Qt-only features got web screens. Trail Maps (core/web_trails.py, trails.html): the library is device-level; upload is a raw body checked for the %PDF magic in TrailMapLibrary.add_from_bytes; From a Link only allows http(s) and is fetched outside the turn lock; delete_trail_map now moves the PDF to the folder's removed/ instead of unlinking, and file_path looks there too, so undoing trail_map.delete (which restores trail_maps.json) brings the map back whole. Opening a PDF fetches it with the tab's token (MIA.download) and opens a blob URL, since a plain link can't carry the bearer token. Past conversations (core/web_conversations.py): history skips empty conversations; pick_up bumps updated_at before handing the conversation to Talk, because conversation_for replaces a conversation idle too long with a fresh one on the next turn; for the desk's own profile it also sets the manager's active conversation.
