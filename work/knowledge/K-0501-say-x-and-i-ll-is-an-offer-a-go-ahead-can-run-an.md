---
id: K-0501
kind: lesson
title: 'Say "X" and I'll ...' is an offer a go-ahead can run; an example is worded 'Say one, like "X", to .
status: confirmed
by: claude
created: 2026-11-26T09:04:05+00:00
concerns: core/conversation_state.py, core/assistant_turn.py
from: commit:6ff0125b
---
core/conversation_state.offered_phrase runs the words of her own last 'Say "X" and I'll ...' when he says a go-ahead that says to act ("do it", "start it", "go ahead", "yes please"; never a bare ok, sure or thanks). The Fable review found an example worded as an offer ('Say "I harvested 3 pounds of beans" and I'll keep it') that a bare ok would have logged. When writing a reply: an offer she'd carry out on a yes is 'Say "..." and I'll ...'; a sample sentence for him to adapt is 'Say one, like "...", to ...'; an undo, stop, cancel or delete is never run on a yes.
