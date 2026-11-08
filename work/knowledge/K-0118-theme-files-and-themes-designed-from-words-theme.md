---
id: K-0118
kind: implementation
title: Theme files and themes designed from words (Theme Studio steps 3-4)
status: confirmed
by: claude
created: 2026-11-08T12:35:12+00:00
concerns: core/theme_actions.py, core/theme_design.py, web/studio.js, server/app.py
from: dec:DEC-0136
---
Export: the Studio downloads what's on screen as {format: 'mia-theme/1', name, line, choices, tokens, material, room} (core/theme_actions.export has the same shape for saved themes). Import is an action, theme.import, so it's approved and undoable: core parses the file (20,000 characters at most), checks the format mark, cleans it with clean_theme (allowlisted tokens only, no CSS breakouts), takes its choices (or reads them back from its tokens with choices_of when a file has none) and rebuilds it with build_theme, so the accent and contrast checks run again whatever the file claims; the name is made unique. Design: core/theme_design.design reads the description in code with regex word lists (SCENES pick the base and field colours, COLOURS the accent, MOODS the room levels, material, font and corners), so the same words always make the same theme; warm accent words and light-theme requests go into `missed` with a reason; understood notes are merged per word. The Studio previews a design before anything is kept (POST /api/themes/design is pure); the voice tool design_theme saves it through theme.save and uses it, and says undo takes it back. Demo-mode pages can't reach the design endpoint, so the Studio test stubs MIA.designTheme with the real designer's output.
