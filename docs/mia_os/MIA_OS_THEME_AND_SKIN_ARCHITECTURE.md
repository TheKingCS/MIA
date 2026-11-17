# MIA OS: themes and skins (Prompt 11 §10; DEC-0236)

*Claude (Opus), 2026-11-17. Planning only.*

## 1. The set

| Prompt's direction | MIA's theme | Exists |
|---|---|---|
| MIA Signature | **Aquatic** (default, DEC-0183) | yes |
| Minimal | Glass | yes |
| Classic | Stark (the engineering look) | yes |
| Neon Cyber | Cyberpunk; Y2K Cyber | yes |
| Graffiti | Graffiti | proposed (Q-85) |
| Light | Light | proposed (Q-85) |
| High Contrast | the high-contrast setting, over any theme | yes |
| Ambient | the ambient mode's layout on any theme (DEC-0231) | planned |
| Others | Nebula, Evergreen, Aurelia, Glacial, Eclipse | yes |

## 2. A theme is a file of data (the Theme Studio's, built)

```
{ "id": "my-garage", "name": "...", "description": "...",
  "tokens": { "--rgb-bg": "6,10,14", "--accent": "#35d4ff", ... },   // only TOKENS
  "material": "glass", "tiers": {...},                                // clamped
  "backdrop": "backdrop.jpg",                                         // an image file, checked
  "room_light": {...}, "orb": {"tint": "accent"}, "sounds": "soft" }
```

**Validated in code** before use, as `core/themes.clean_theme` and `build_theme` already do: only known keys;
values that could break out of CSS refused; numbers clamped; text contrast at 4.5:1 and an accent that can't read as
a warning (`accent_problem`); a backdrop only as one of his own pictures, by id; **no CSS, no script, no URLs**.
Saved, exported and imported in the Theme Studio as a `mia-theme/1` file (`theme.save`, `theme.import`,
`theme.delete`: approved and undoable), up to 12 of his own. **To add:** the contrast check over every surface tier
(REQ-VIS-003), the orb's style, and a bundled image when a theme is given to someone else's MIA. A theme can't change
behaviour because the engine reads only values from it.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-VIS-013 | A theme shall be data only (known tokens, clamped tiers, checked images) and be refused, with the reason, if it fails a contrast check or holds anything else. | Must | R1 | All | Partial (tokens, clamps) | T | DEC-0236 → 11, 13 |
| REQ-VIS-014 | MIA shall offer a Light theme alongside the Signature, and high contrast over any theme. | Must | R1 | All | Partial (high contrast) | T | DEC-0235 → 11 |
