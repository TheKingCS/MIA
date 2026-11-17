# MIA OS: the design system's architecture (Prompt 11 §3; DEC-0234)

*Claude (Opus), 2026-11-17. Planning only.*

## 1. Layers

| Layer | What | Where | Exists |
|---|---|---|---|
| Primitive tokens | raw values: colours as triplets, sizes, durations | `web/tokens.css` | yes |
| Semantic tokens | meaning: `--accent` (MIA), `--ok`, `--attention`, `--bad`, `--win`, `--text-dim`, tiers | `web/tokens.css` | yes |
| Theme | which values the semantic tokens take, material, backdrop, light of the 3D room | `core/themes.py` (data) | yes |
| Scheme, layout, effects | accent family; density, sidebar; effects level | `core/appearance.py` | yes |
| Components | frame, card, panel, card of approval, toast, rows, orb | `web/components.css`, `shell.css`, `shell.js` | yes |
| Pages | each app's screen | `web/*.html/js` | yes |
| Platform adaptations | phone (< 720 px), glasses (600×600, black see-through), Qt host | the same pages; `glasses.js` | yes |

**Rules (already enforced):** a style sheet never gains a literal colour (`tests/test_appearance.py`,
`tools/css_colours.py`); a theme may set only `TOKENS`; meaning colours aren't tokens a theme can set; tiers are
clamped (`TIER_RANGES`).

## 2. Platforms

| Platform | Renders | Token set |
|---|---|---|
| Desktop (MIA OS, Windows today) | the web front end in its host | full |
| Phone | the same pages | full; effects "auto" means light |
| Glasses | `glasses.js` composition | reduced: accent, ink, meaning, black; no glass, no blur |
| Future wearables (Zeta Astralis) | the same pages in a compact layout | reduced |
| Conventional Linux apps | their own toolkit | a KDE colour scheme and Kvantum theme generated from MIA's tokens (§ application integration) |

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-VIS-001 | Every visual value shall come from a token; a style sheet with a literal colour shall fail a test. | Must | MVP | All | Exists | T: appearance tests | DEC-0234 → 11 |
| REQ-VIS-002 | The glasses and compact wearables shall use a reduced token set (accent, ink, meaning colours, black) derived from the active theme. | Should | R1 | Glasses | Partial | T | DEC-0234 → 11, 12 |
