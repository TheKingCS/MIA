---
id: K-0411
kind: debugging
title: A record named isn't a question about using MIA
status: confirmed
by: claude
created: 2026-11-24T12:59:57+00:00
concerns: core/assistant_chat.py
from: commit:39a64f2f
---
Teach me how to sharpen a chainsaw was held to her help pages (he owns a chainsaw, so a maintenance tool matched), and walk me through canning salsa or teach me about rotational grazing (nothing matched) got the teaching instruction that forbids outside knowledge. about_mia now counts a record's tool as hers only when one of its phrases or an app verb (add, log, set up, use the...) matched, never only because a record was named; and a teach-me request that matches nothing is the world's (a how-to that matches nothing stays hers, the safe side).
