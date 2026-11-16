---
id: K-0258
kind: implementation
title: Each app's own colour (DEC-0187): --rgb-atmo-* per <body data-app>
status: confirmed
by: claude
created: 2026-11-16T08:00:54+00:00
concerns: web/tokens.css, tests/test_appearance.py
from: dec:DEC-0187, dec:DEC-0113, dec:DEC-0186
---
What: Zac approved six app colours (Q-42): Workout rose, Kitchen soft cream gold, Workshop steel (also business and made), Finance indigo (data-app budget), olive for the estate and the homestead (real_estate, greenhouse, flock), Skills plum (skills, taught_skills). Each is a --rgb-atmo-<name> triplet in web/tokens.css; a body[data-app] rule picks it into --rgb-atmo, and one shared rule derives --atmo, --mod-glow and --mod-dim from it, so the app's own data (.atmo, chart bars, stage bars) and the faint header glow take it. --mod-line, buttons, selection and states stay the accent. High contrast resets all of it to its cyan and no glow.

Why this way: DEC-0113 already had the --atmo mechanism, with workout orange, kitchen cream and workshop steel; workout's orange became the reward's colour (DEC-0186), and the 2026-11-07 proposal's leaf green sat on --ok. The body[data-app] selector outranks the older .mod-* classes, which sit on the same body, so their cyan --mod-glow no longer wins on these pages.

Checked: tests/test_appearance.py reads every --rgb-atmo-* triplet and requires accent_problem to pass and 4.5:1 or better on every built-in theme's background (the lowest is rose on Glacial, 5.9). Screenshots of six pages in demo mode showed the colour only in each app's own data, as intended; the header glow is faint, and Muse may turn it up.
