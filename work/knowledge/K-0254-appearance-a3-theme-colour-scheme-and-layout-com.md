---
id: K-0254
kind: implementation
title: Appearance A3: theme, colour scheme and layout composed independently
status: confirmed
by: claude
created: 2026-11-16T06:25:15+00:00
concerns: core/appearance.py, web/shell.js, web/shell.css, web/themes.css, core/assistant_accessibility_actions.py, tests/test_appearance.py
from: dec:DEC-0184, dec:DEC-0136, dec:DEC-0014
---
What: core/appearance.py. SCHEMES (cyan with the picture's blue and violet, turquoise, violet, champagne, ice, rose) set --accent and its soft/deep, --accent-2/-3, --chart-1 to -6 (three accents, three greys) over the theme (compose); 'theme' keeps the theme's own. scheme_problem refuses an accent of the three that reads as a meaning colour (themes.accent_problem) or a primary under 3:1 on the panel. LAYOUT: density comfortable/compact (--gap 10px), sidebar full/icons (a 76 px rail; Home keeps its Talk column through .layout:has(.home-mia)). effects auto/full/light/none and reduce_transparency become data attributes web/shell.js sets; web/themes.css drops blur on light and makes tiers solid on none or reduced. readability_problems mixes field, panel at the tier's alpha and the sheen at its tint and requires 4.5:1 for text. for_shell is what /api/shell sends (web_surfaces._display).
Why this way: one composed theme dict keeps shell.js's applyTheme unchanged; each choice is its own person setting so none can move another. What went wrong: a warm gold scheme was refused by the meaning-colour rule (Q-41; champagne instead); the icons rule first replaced Home's three columns with two and hid Talk; the sidebar's headings are .side-head, not .pw-label; a CSS escape sent through the shell became a control character again (fixed with a script file).
