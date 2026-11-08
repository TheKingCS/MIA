---
id: K-0130
kind: implementation
title: Connections: how a remark is tied to something started weeks ago
status: confirmed
by: claude
created: 2026-11-08T16:21:56+00:00
concerns: core/connections.py, core/talk_it_out.py, core/assistant_chat.py, core/loops.py
from: dec:DEC-0146, commit:bded921c
---
core/connections.py runs in talk_it_out.pre_turn after the danger check, never in a private or personal turn (life_notes._private). find() first names records the words mention outright (MENTIONABLE kinds: assets, materials, skills... people, pets, money and the calendar left out on purpose) and follows links_for() to an open project, goal or mission on the far end; then looks for an open target or a set-aside idea sharing a distinctive word (one of five letters or more, or two words). Guards: the target must be at least 7 days old (newer is still top of mind), a thing named outright is the topic not a connection, finished things never come back. One per thing is kept, held 2 hours so it lands in a later conversation, and goes only into the everyday conversation's system message (never build_personal_system_message, never a faith-or-meaning turn), framed 'only if it fits, one sentence, then let it go'. The next turn settles it from her last reply. connections.unlinked counts word-only ties by (kind, kind): each is a link her graph doesn't make yet.
