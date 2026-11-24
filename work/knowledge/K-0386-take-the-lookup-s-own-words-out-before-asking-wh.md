---
id: K-0386
kind: debugging
title: Take the lookup's own words out before asking what else a question names
status: confirmed
by: claude
created: 2026-11-24T08:46:30+00:00
concerns: core/assistant_actions.py
from: commit:6ae551f3
---
A fifteenth fresh review of 6ae551f3: blocking a direct lookup whenever the question named another app's record dropped the flagship how many eggs this week, because eggs is a pantry item too (the groceries entity names). The check now takes the lookup's own trigger phrases and subjects out first. And naming a lookup for a command that starts with its phrase named get_eggs for egg count is 12 today; a command with a number, or with a change of the same app on offer, no longer names a lookup.
