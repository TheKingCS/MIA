---
id: K-0062
kind: implementation
title: The Highest Self in MIA: what goes in the prompt, what code checks, what's measured
status: confirmed
by: claude
created: 2026-11-07T11:03:54+00:00
concerns: personality, conversation
from: dec:DEC-0114, file:core/personality.py
---
Zac and ChatGPT's personality doctrine (H-0089) is too long for a local model's prompt, so each part went where it can work. Her prompt got two short clauses (truth before approval, encourage without flattering, challenge without belittling; on their side, never a replacement for people) and one tone example (doubting isn't failing). A guidance line on faith and meaning joins only when a message turns there (personality.deep_line). Code checks what she must never say (dependency, divine authority, flattery: personality.INTEGRITY, counted by tools/conversation_check). Her values are data pinned by a fingerprint so they change only by decision. The corpus gained twelve cases and was run before and after each change. Measuring found the biggest problem wasn't the prompt at all: two feelings were being answered by question plans (faith guilt by 'patterns', quitting a job by 'freedom'); feelings were added to NOT_A_PLAN, and the 112-question routing audit was unchanged. Prompt gains were real but modest and single runs vary, so tuning stopped for Zac's ratings.
