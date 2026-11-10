---
id: K-0210
kind: debugging
title: She misdescribed herself because a question about her was answered from the help pages
status: confirmed
by: claude
created: 2026-11-10T23:38:37+00:00
concerns: core/assistant_chat.py, core/self_knowledge.py, core/device_help.py
from: file:docs/CONVERSATION_REVIEW.md, file:docs/specs/CONVERSATION.md, dec:DEC-0142
---
Zac's first real conversations: she denied having a greenhouse app, listed features she doesn't have, invented what the Chronicle is, said she had nothing for the glasses, and didn't know when her development began. One cause for most of it. A question about herself was treated as a help question, and the help search (device_help.build_grounded_prompt) handed the model whichever pages shared a word with it; for "greenhouse" that was the Homestead node's module list, which the model read back as her own abilities. Her true records (the app registry, the decisions, the commit history, her own files) existed and were only reached when a narrow pattern matched. Found by asking the specification's own questions of the real model and reading what each turn was sent, not by reading the prompt. Fixed in core/assistant_chat.py: a question about her (self_knowledge.asks_about_her or wants_described) gets her records and no help pages, and the last thing the model reads is a reminder to answer from them in the first person. A second cause worth remembering: her own wrong answer one turn earlier came back as a fact in the next (limits repeating the glasses mistake), so a wrong self-description compounds within a conversation. Measured before and after on the same 23 questions: answers ending on a question 17 of 21 to 1 of 20, median length 75 words to 45. The findings, the evidence and what is still not right: docs/CONVERSATION_REVIEW.md.
