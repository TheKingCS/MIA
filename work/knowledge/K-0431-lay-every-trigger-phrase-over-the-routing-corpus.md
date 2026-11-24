---
id: K-0431
kind: test-procedure
title: Lay every trigger phrase over the routing corpus
status: confirmed
by: claude
created: 2026-11-24T16:01:02+00:00
concerns: core/assistant_creation_actions.py, tests/test_trigger_hygiene.py
from: commit:459b3449
---
A trigger phrase is a substring, so a short one fires inside other apps' sentences (my best in my best customers). A scratch audit laid every tool's phrases over the routing corpus and the everyday phrasings and listed each that fired in a sentence meant for another domain. Most are co-offers the model sorts out; the wrong ones were narrowed: bought a (clothing), my own (ownership), what depends on (describe_app), add to my and what's in my (trackers, now reached by their own titles through register_entity_names), how far along (freedom). tests/test_trigger_hygiene.py holds both sides. Worth re-running after adding tools.
