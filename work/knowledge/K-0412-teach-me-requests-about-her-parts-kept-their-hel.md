---
id: K-0412
kind: debugging
title: Teach-me requests about her parts kept their help pages
status: confirmed
by: claude
created: 2026-11-24T13:14:42+00:00
concerns: core/assistant_chat.py, core/assistant_actions.py
from: commit:8441a41a
---
Adding teach me about and teach me how to the library's asking words made every teach-me match the library, so teach me how quests work or teach me about the budget lost her help pages. Those words came back out; a teach-me request is hers when it names one of her parts (an app's name from its manifest, leaving out everyday words like power or kitchen, or a feature word: quests, alarms, budget, journal) or starts with an app verb (add, see the, update, remind me), never because a topic's keyword matched (teach me about solar power is the world's). matched_domains_by_words now uses the router's own whole-word keyword test.
