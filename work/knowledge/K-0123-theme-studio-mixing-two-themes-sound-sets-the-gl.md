---
id: K-0123
kind: implementation
title: Theme Studio: mixing two themes, sound sets, the glasses' accent
status: confirmed
by: claude
created: 2026-11-08T15:53:48+00:00
concerns: core/themes.py, web/studio.js, web/sound.js, web/glasses.css, core/glasses.py
from: dec:DEC-0136
---
core/themes.combine overlays chosen PARTS (colours, shape, room, sound, backdrop) of a second theme's Studio choices on the first and runs build_theme as a dry check, returning the refusal sentence as problem instead of raising, so the Studio can show why a mix can't be kept before Save. A theme's sound is one of SOUND_SETS, kept by clean_theme only by name (else classic), and every built-in starts classic so the chimes only change when someone picks a set (the 'opt-in' of step 5). web/sound.js voices the same tunes by the set (pitch, time, wave, glide). The glasses get glasses_accent: the theme accent mixed toward white until 9:1 against black, since dark colours vanish on a see-through lens; glasses.css had 40 literal cyans, now all var(--rgb-accent)/--accent-soft/--accent-deep.
