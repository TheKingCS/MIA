---
id: K-0259
kind: implementation
title: A theme from a picture, and 'make it darker / warmer' (appearance A7, first part)
status: confirmed
by: claude
created: 2026-11-16T08:16:23+00:00
concerns: core/theme_picture.py, core/theme_design.py, core/assistant_accessibility_actions.py, server/app.py, web/studio.js, web/studio.css, web/mia.js, apps/settings/manifest.json, tests/test_theme_picture.py
from: dec:DEC-0184, dec:DEC-0186, dec:DEC-0183
---
What: core/theme_picture.from_image reads a picture's palette in code and returns the same shape core/theme_design.design does ({name, line, base, choices, understood, missed}), so the Studio previews it and theme.save keeps it unchanged. The Appearance page's From a Picture sends a photo as a data URL (or a painting's id) to POST /api/themes/picture; nothing is kept until Save. By voice, theme_from_picture finds one of the person's paintings by its words (core/art_studio.find) and saves and uses it; adjust_theme nudges the theme in use with core/theme_design.adjust (darker, lighter, warmer, cooler, brighter, calmer, more contrast). Both tools are act_within_grant in apps/settings/manifest.json, like design_theme, and undoable through theme.save.

How the colours are chosen: Pillow's median cut on a 160 px thumbnail (12 main colours), and separately on just the vivid pixels (saturation 0.35 or more, lightness 0.22 to 0.85; 6 colours). The field takes the hue of the most common dark colour that has one (saturation 0.08 or more), at lightness 0.05 and 0.10; the accent is the most common vivid colour that passes themes.accent_problem, at lightness 0.62 or more until it reads 4.5:1 on the field; a meaning colour goes into the room's palette and into `missed`. With under 1% vivid pixels the most colourful main colour is brightened. Docs' reference picture (docs/design/reference/prompt24_glass_dashboard.jpg) gives #69a6d3 on #0b0d0e, close to the hand-made Aquatic, and is a test fixture.

Why this way: prompt 24 §9 and the plan say the model may name a theme but never choose its numbers; reading in code makes the same picture always give the same theme and keeps every result inside build_theme's checks.

What went wrong or nearly did: (1) A near-black's hue is noise: the reference's #060707 made the field 'red'; only colours with saturation 0.08 or more choose the hue, else the field is neutral. (2) A grey picture borrowed a false red from the same noise for the accent; the muted fallback now needs saturation too, and a picture with no colour keeps Aquatic's accent with its own sentence. (3) Near-duplicate accents filled the room's palette; one per 12 degrees of hue. (4) Image.getdata is deprecated (Pillow 14); get_flattened_data when present. (5) The phone's build may lack Pillow: the import failing is a sentence, not a crash. Also: the description designer and tweak_theme still refused gold from before DEC-0186; gold, champagne and bronze are accents now (Aurelia's values), vivid orange still refused.
