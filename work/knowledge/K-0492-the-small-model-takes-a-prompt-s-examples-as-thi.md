---
id: K-0492
kind: lesson
title: The small model takes a prompt's examples as this conversation
status: confirmed
by: claude
created: 2026-11-25T14:35:43+00:00
concerns: core/personality.py, core/assistant_chat.py
from: commit:a86f327e
---
Written as a Them/You dialogue, the tone examples were read by qwen2.5:14b as things he had said: it brought up that marathon you are running next week and you mentioned you rewrote an email four times. Recast as described pairs (told X, you would say Y), labelled as other people and never to be mentioned, they stopped leaking in repeated live runs. A humor nudge on a bare thanks made it copy an example subject (a tangled cord), and with the day facts in its prompt it tacked the overdue bill onto every thanks: a pleasantry now gets no joke and pleasantry_line. Examples for this model should never read like a transcript.
