---
id: K-0255
kind: implementation
title: Appearance A4 and DEC-0186: six glass presets, Aquatic the default; gold accents allowed, rewards li
status: confirmed
by: claude
created: 2026-11-16T06:51:24+00:00
concerns: core/themes.py, web/tokens.css, web/themes.css, web/studio.js, core/theme_actions.py, tests/test_appearance.py, tests/test_themes.py
from: dec:DEC-0186, dec:DEC-0183, dec:DEC-0184
---
What: core/themes.THEMES gains aquatic (the default: DEFAULT_THEME), nebula, evergreen, aurelia, glacial, eclipse, each material glass with its field and panel colours, three accents and chart colours, tier tokens, a backdrop of radial lights and --frame-glow (web/themes.css draws it as an inset accent edge on body::after, off when effects are none or contrast is high). Aquatic's values come from Zac's picture (accent #35d4ff, #3f79e5, #5955cb; panel #28323e). Q-41 'Allow gold': MEANING_HUES carry a saturation from which each reads as its meaning; amber's is 0.8, so soft gold (#e8c27a, 0.71), champagne and bronze pass while vivid amber and orange stay refused; the reward colour moved from gold to a deep legendary orange (#ff8a1f, hue 29; Zac's follow-up, after lime was tried), inside amber's band so a vivid orange accent is refused; web/studio.js's live check reads the same saturation (meaning_hues[].vivid).
Why orange: Zac asked for Borderlands legendary orange (lime and magenta were tried first; magenta clashed with Y2K's and Cyberpunk's accents). It is redder than the amber that means 'needs you', and both carry their words. Evergreen keeps emerald in its environment only (green means done); Eclipse's crimson #e0306a sits 22 degrees from error red. Tests that assumed Stark as the default now expect Aquatic.
