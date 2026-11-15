---
id: K-0231
kind: implementation
title: Research and Verify: key terms leave the device, verdicts need a source
status: confirmed
by: claude
created: 2026-11-15T11:39:18+00:00
concerns: core/ual.py, core/online_lookup.py, core/web_account.py, core/assistant_ual_actions.py
from: dec:DEC-0165, dec:DEC-0053
---
What: core/ual.py _research and _verify (READ, where=ONLINE), offered only when the person's switch ual.online is on (now a PERSONAL_SETTINGS key, a Settings toggle in core/web_account.py, and the voice tool selections_search_web via setting.set) and never for a sensitive capture. spec_problems now blocks only CLOUD from being ready; ONLINE was the "B" Zac approved.

How little leaves: each search is key_terms() of the selection (or of one claim), at most six words, passed through core/online_lookup.search, which scrubs emails, long numbers and everything after "password" and only talks to the person's own SearXNG (own_engine). A test puts an email, a phone number and "my bank password" in the selection and checks none of it is in the query.

Verify's rule in code: claims_of() takes up to three sentences of four words or more; each is searched on its own; the model returns JSON verdicts; a claim is printed "Supported by <site>" or "Contradicted by <site>" only if its verdict names a result number that exists among that claim's own results. A missing, zero or out-of-range source, or a reply that isn't JSON, prints "Couldn't verify". Every report ends saying it's from search snippets only.

Research: the model writes from online_lookup.said(found) (each snippet untrusted()) plus the framed selection; facts carry [n]. If the model is down, the sources still come back.

Open question: on the phone, online.searxng_url defaults to the phone's own 127.0.0.1, so research there probably needs the PC's home-network address set; not tested on a device.
