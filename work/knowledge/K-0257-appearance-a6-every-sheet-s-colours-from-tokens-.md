---
id: K-0257
kind: implementation
title: Appearance A6: every sheet's colours from tokens, the glasses page excepted
status: confirmed
by: claude
created: 2026-11-16T07:51:25+00:00
concerns: web/tokens.css, web/components.css, web/concept.css, web/home.css, web/shell.css, web/ui.css, web/spatial.css, web/glasses.css, web/studio.css, web/themes.css, tools/css_colours.py, work/css_colour_baseline.json, tests/test_appearance.py
from: dec:DEC-0183, dec:DEC-0184, dec:DEC-0186, dec:DEC-0187
---
What: the web sheets had 203 hard-coded colours. Now every sheet but glasses.css reads every colour from a token (tools/css_colours counts 0; the baseline in work/css_colour_baseline.json fell to 40, all glasses.css's own token block). Pure black and white became rgba(var(--rgb-shadow), a) and rgba(var(--rgb-light), a) (125 by a script); the rest were mapped by hand: dark panel tints to --rgb-bg, --rgb-panel and --rgb-panel-2, near-white highlights to color-mix of the accent (or --win) with --rgb-light, dark text on accent fills to the new --on-accent, the green and amber buttons (components.css, shown by label.html and selection.html) to --ok, --attention and --soon-deep, and spatial.css's var(--attention, #f2b33d) fallbacks dropped since tokens.css always defines it.

How it was checked: a pixel comparison. A git worktree of the commit before was served beside the working copy, and fourteen pages were rendered in demo mode by headless Edge (Playwright, animations off, Math.random and Date.now fixed) and compared pixel by pixel. glasses and selection were identical; the others differed only in the brand mark's centre (a near-white now mixed from the accent), the reward orb on presence (max 17 of 255), and the Label page's Print button, now the theme's green rather than its own brighter one. nexus differs over the whole frame by its 3D scene, which isn't deterministic; side by side it's the same.

Why this way: tokens are what themes, schemes and high contrast change (DEC-0183, DEC-0184), so a literal is a spot no theme reaches. color-mix keeps a highlight's relationship to the accent, so it follows a theme instead of staying cyan-white.

What went wrong or nearly did: (1) glasses.html doesn't load tokens.css, so the converted rgba(var(--rgb-light)...) would have been invalid there; its own :root now defines --rgb-light and --rgb-shadow (pure, since the lens shows black as see-through), and a test checks it. (2) A token read without a fallback that nothing defines silently drops the whole declaration; tests/test_appearance.py now fails on any var(--x) a sheet reads that tokens.css or the sheet doesn't define, except --hue and --tile-rgb, which hub.js, glasses.js and apps.js set per element. (3) The old per-app atmosphere proposal (orange, amber-cream, leaf green) now collides with the meaning colours, so DEC-0187 proposes others (Q-42).
