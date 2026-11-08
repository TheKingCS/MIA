---
id: K-0147
kind: implementation
title: Online lookup: the rules of DEC-0053 in code, SearXNG only
status: confirmed
by: claude
created: 2026-11-08T20:42:10+00:00
concerns: core/online_lookup.py, tests/test_online_lookup.py, docs/ONLINE_LOOKUP.md
from: task:T-0017, dec:DEC-0053
---
T-0017 (DEC-0053, Zac's answers 2026-10-31): core/online_lookup.py. allowed() refuses only on a known offline state (unknown lets the search try and say if it can't), a child's account, or online.lookup off. scrub() takes emails, long numbers and anything from 'password' on out of the words before they leave; an empty result sends nothing. search() uses only a SearXNG on this computer or the home network (own_network), JSON format, results deduplicated and web pages only, each with its site and published date; said() marks them as web content through browser_safety.untrusted with the day searched, apart from her records, never a legal or tax ruling. Not built: the voice tool (parity session), a screen control (design), the hosted-API fallback (needs a key). SearXNG isn't installed (no Docker on the PC): Zac's step, docs/ONLINE_LOOKUP.md, in WAITING_ON.
