---
id: K-0497
kind: lesson
title: A veto must take out its own words, never the whole sentence
status: confirmed
by: claude
created: 2026-11-25T20:31:47+00:00
concerns: core/first_aid_floor.py, core/assistant_turn.py
from: commit:a7a2afbe, commit:710858c3
---
The Fable review (2026-11-25) found the emergency floor missing real emergencies because each whole-sentence veto added to quiet a false alarm (a figure of speech, a past event, a machine word) silenced any emergency in the same sentence: "he was burning brush and his clothes caught fire", "she almost drowned and now she isn't breathing". What held: a veto removes only its own span and the rest is checked again (first_aid_floor._without); words are normalised before matching ("hes", "im", "wont"); repeat suppression compares the kinds covered, not one. The same review found the routes that write records misreading everyday sentences after nineteen rounds; they now act only on a sentence they read whole and hand the rest to the model (Q-0018 asks Zac about retiring them).
