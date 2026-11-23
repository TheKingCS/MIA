---
id: K-0352
kind: implementation
title: The emergency floor answers before the model
status: confirmed
by: claude
created: 2026-11-23T18:04:40+00:00
concerns: core/first_aid_floor.py, core/talk_it_out.py
from: commit:29396ed9
---
core/first_aid_floor.py runs in talk_it_out.pre_turn right after detect_danger, as a fixed_reply: an emergency sign (regex per kind, most time-critical first: cpr, choking, anaphylaxis, bleeding, stroke, heart, unconscious, poison, snakebite, burn, heat, hypothermia) AND a now-sign (a pronoun, a family word, 'right now', 'just'), unless it opens like a topic question ('what are the signs', 'how do you treat', 'what to do if'). Words from Red Cross/AHA first aid; no medicine doses (the operator gives those); the number from region_for, never a guess. Gotchas: 'heat stroke' matched stroke until a lookbehind; 'his clothes caught fire' missed until his/her/their joined the now-signs. Errs broad: a false positive costs one careful message.
