# MIA OS: personalisation (Prompt 11 §11)

*Claude (Opus), 2026-11-17. Planning only.*

| He can change | Within | Exists |
|---|---|---|
| Theme, scheme, density, sidebar, effects | the sets | yes |
| Backdrop picture (his photo, art) | a theme's backdrop, faded where he reads | yes (DEC-0136) |
| His own palette, corners, font, material, the room's light | the Theme Studio, contrast-checked | yes |
| Orb colour and style | accent tint; rings, particles or glyph | new |
| Icon pack | interface glyphs only | new |
| Layout presets | per dashboard: pinned, hidden, order (REQ-DSK-006) | new |
| Sound profile | the theme's chime set (`SOUND_SETS`), on or off | yes; interface sounds new |
| Animation intensity | the effects setting | yes |
| An app's look | its atmosphere colour | new |
| Workspace look | a theme per project workspace | new |

**MySpace without the mess:** the Theme Studio is already his "make it mine" page (save, export, import his own
themes). Added (Q-83): start from one of his pictures, MIA suggests a palette from it that passes the checks, and he
picks the orb's style.
**Boundaries:** readability, meaning colours, the approval card's look (always recognisable as a decision) and the
orb's state shapes can't be changed.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-VIS-015 | The approval card and the orb's state shapes shall stay recognisable under every theme and personalisation. | Must | MVP | All | Partial | T | DEC-0236, DEC-0237 → 11 |
| REQ-VIS-016 | From one of his pictures, MIA shall suggest a palette that passes the contrast checks, which he can save as his own theme. | Could | R1 | All | New | T | DEC-0236 → 11 |
