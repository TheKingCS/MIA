---
id: K-0177
kind: implementation
title: Links read dict records; the creative and game stores are life areas
status: confirmed
by: claude
created: 2026-11-09T09:49:56+00:00
concerns: core/links.py, core/life_areas.py, tests/test_links.py, tests/test_life_areas.py, tests/test_history_and_links.py
from: file:core/links.py, file:core/life_areas.py, file:tests/test_history_and_links.py
---
2026-11-09, the self-audit's store connections, third pass (20 open, now 16). core/links.py read every record with getattr, so stores that keep dicts (the plans shelf, creations, life notes, GPS tracks) could never be linked. field_of(record, attr) reads either kind, and _records takes a dict's values (the plans shelf keeps its plans by id). New kinds: plan, creation, note and track. 'note' and 'track' were already the refs these stores' own history uses (@life_events.on_change) and core/connections.py's note refs, so history and links now meet on them. Naming them life_note and gps_track would have split the two. tests/test_history_and_links.py now checks a dict store's keys as well as a dataclass's fields. core/life_areas.py gained art, creations, plans, play, world_map, bosses and fitness. What's left: health, the ID wallet and memories (linking them needs a privacy decision: a link names the record), learning paths (keyed by program, with no name), the ledger's entries, record sets, the Loop, play entries, the world map's check-ins and business use (no web page yet).
