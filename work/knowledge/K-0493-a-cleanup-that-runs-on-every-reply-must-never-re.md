---
id: K-0493
kind: lesson
title: A cleanup that runs on every reply must never rewrite one
status: confirmed
by: claude
created: 2026-11-25T15:03:59+00:00
concerns: core/personality.py, core/response_composer.py, core/first_aid_floor.py
from: commit:603dedab, commit:5c602ba9
---
The eighth review found that a check meant to drop a humor example copied loosely (core/personality.without_copied_example, through response_composer.polish) split every model reply into sentences and rejoined them: lists and line breaks ran together, and sentences with a plain word like cord or remote were cut, a space-heater answer losing its extension-cord warning. It now touches only an opening line in an example's own distinctive words. A filter on all of her replies takes the narrowest match and leaves the rest byte for byte; and widening an emergency's words (bare family names) needs its false alarms checked the same day (mom passed out the cookies).
