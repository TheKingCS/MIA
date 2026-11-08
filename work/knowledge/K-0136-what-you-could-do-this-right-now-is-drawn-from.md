---
id: K-0136
kind: implementation
title: What 'you could do this right now' is drawn from
status: confirmed
by: claude
created: 2026-11-08T16:21:56+00:00
concerns: core/capability_reminders.py
from: dec:DEC-0143, commit:d0ba9ba2
---
capability_reminders.on_hand() gathers only true, right-now abilities, each a (verb phrase, honest reason): a started learning path with an open check, a project begun and parked, a built-in plan whose materials are all on the shelf (plan_library.shopping_list against material_manager), a recipe with nothing missing (kitchen.recipes_makeable_now), and the homestead's next doable step, offered only when the person already has something from the homestead catalog so nobody else is told to build a compost bin. Empty in, empty out.
