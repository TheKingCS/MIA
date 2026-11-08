---
id: K-0117
kind: implementation
title: The Theme Studio: choices in, tokens out, with checks in core
status: confirmed
by: claude
created: 2026-11-08T11:57:17+00:00
concerns: web/studio.js, core/themes.py, core/theme_actions.py, web/nexus3d.js
from: dec:DEC-0136
---
web/studio.js lets a person start from any theme and tweak a few choices (five colours, corners, font from FONTS, material, room levels and palette). The live preview mirrors core/themes.build_theme's arithmetic (mix toward white or black by fixed amounts, triplets for --rgb-*) and applies it with MIAShell.previewTheme (applyTheme without caching, so leaving the page restores the real theme). On save, theme.save (core/theme_actions.py) rebuilds the tokens in core from the same choices and stores the theme with its choices in person_settings display.custom_themes (max 12, ids my_<slug>). Core refuses an accent within 20 degrees of amber, red, green or gold hues unless it's pale or grey, and text under 4.5:1 contrast on the background or panels; the page shows the same messages early and greys out Save. Settings' theme options become context-aware (options_for(setting, context)), and account_actions._setting accepts the person's own theme ids. The Studio page uses refreshOnChange: false so a change elsewhere doesn't wipe your tweaks; after a save it reloads and selects the saved theme by name. Found on the way: on the first frame nexus3d's clock can be a hair below zero, which made the mist palette index negative (undefined colour, a thrown error each frame) in any theme with a palette; clamped. The 3D preview remounts on a fresh canvas each time, since stop() loses the WebGL context.
