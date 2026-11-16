---
id: K-0253
kind: implementation
title: Appearance A2: five glass surface tiers as tokens, clamped; a hard-coded colour baseline
status: confirmed
by: claude
created: 2026-11-16T06:15:34+00:00
concerns: web/tokens.css, web/themes.css, core/themes.py, tools/css_colours.py, tests/test_appearance.py
from: dec:DEC-0183, dec:DEC-0184
---
What: web/tokens.css gains --surface-<tier>-<part> for tiers primary, secondary, floating, deep, interactive and parts alpha (panel colour under the glass), tint (sheen; its bottom is a third), blur (px), border, light (inner top line), shadow; --rgb-light and --rgb-shadow; --accent-2, --accent-3, --gradient-accent, --chart-1 to -6. web/themes.css's glass material is generated from them per tier (primary .glass; secondary .row .figure .asset-card .stat-tile .strip .cell; deep .holo .n3-card; floating .confirm .account-menu #mia-status; interactive .btn-ghost and chips except .chip-ok/.chip-soon/.chip-bad, whose borders carry meaning), blur only above 860 px, solid under prefers-reduced-transparency. core/themes.py: TIER_TOKENS join TOKENS; clean_theme clamps each by TIER_RANGES (floating alpha 0.80 to 0.97). tools/css_colours.py counts literal colours per sheet against work/css_colour_baseline.json (203 in 11 sheets; themes.css fell from 18 to 11).
Why this way: tiers only under the glass material, so Stark is unchanged by construction (screenshots compared); defaults reproduce the old Glass theme except stat tiles lose their blur (secondary tier) and dialogs and chips gain glass. What went wrong: clamping by the '--surface-' prefix swallowed the existing --surface-solid token; it now matches only TIER_TOKENS.
