---
id: K-0250
kind: decision
title: Prompt 24's appearance engine extends the theme engine; it doesn't replace it
status: confirmed
by: claude
created: 2026-11-16T05:40:46+00:00
concerns: core/themes.py, web/tokens.css, web/themes.css, docs/mia_os/MIA_OS_APPEARANCE_ENGINE.md
from: dec:DEC-0183, dec:DEC-0184, dec:DEC-0136
---
What: the plan for glass as MIA OS's look (docs/mia_os/MIA_OS_APPEARANCE_ENGINE.md). The audit found most of the handoff already built: themes as data (core/themes.py, DEC-0136) with clean_theme and build_theme (allowed tokens only, accent not a warning hue, 4.5:1 text), the Theme Studio (preview, 12 custom themes, approved actions), combine(), painted backdrops (DEC-0140), a glass material (web/themes.css; blur off on phones), Spatial and Cards (DEC-0135), focus presets, glasses orb states.
Plan: split a theme into display.theme (environment, surfaces), display.scheme (accents, chart palette, orb colour) and display.layout (nav, density, sidebar, experience, Home), composed by an appearance() function; five surface tiers with clamped opacity and blur; an effective-contrast check (panel mixed with the backdrop at the tier's transparency); effects levels and reduced transparency; the orb's state from runtime events. Meaning colours stay out of schemes (DEC-0136), against the handoff's 'status colors' in a scheme: only hue tuning through a checked function.
What to know: DEC-0023 (Stark, one cyan accent) is superseded as the default look by DEC-0183 but its token rules stay; Muse owns the values (Q-38); the reference image never arrived (Q-39).
