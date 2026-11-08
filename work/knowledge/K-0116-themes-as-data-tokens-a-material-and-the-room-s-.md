---
id: K-0116
kind: implementation
title: Themes as data: tokens, a material and the room's light (DEC-0136)
status: confirmed
by: claude
created: 2026-11-08T11:42:00+00:00
concerns: core/themes.py, web/themes.css, web/shell.js, web/nexus3d.js, web/concept.css
from: dec:DEC-0136
---
core/themes.py holds each theme as data: CSS tokens from an allowlist (TOKENS: field, panels, lines, text, accent, radii, fonts, label tracking, motion, --theme-backdrop), a material (solid, glass, chrome, wire; drawn in web/themes.css with :root[data-material=...]:not([data-contrast=high]) selectors, which beat the base .glass rule by specificity, so the file's load order doesn't matter) and the room's light (accent, back_top/back_bottom, a vapor and mist palette, fire, bloom, mist, scan, grain; read by web/nexus3d.js as opt.theme). clean_theme() is the one gate for built-in, custom and imported themes: unknown tokens dropped, values with url(, braces, semicolons, angle brackets or backslashes dropped, room colours #rrggbb only, levels clamped. Meaning colours (attention, bad, ok, win, soon, rarity) aren't in the allowlist, so no theme can hide a warning. web/shell.js applies the tokens as inline custom properties on <html>, sets data-theme and data-material, and caches the theme in localStorage, applied when shell.js loads, so the next page opens already themed instead of flashing Stark. The derived tokens in tokens.css (--glass, --surface, --mod...) are var() of the --rgb-* triplets on the same element, so setting the triplets reskins them too. The page backdrop's first layer is var(--theme-backdrop) in concept.css body::before.
