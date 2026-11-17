# MIA OS: icons and symbols (Prompt 11 §7)

*Claude (Opus), 2026-11-17. Planning only.*

| Set | Style | Source | Exists |
|---|---|---|---|
| Interface icons | one line weight, round joins, 24 px grid, currentColor | `web/icons.js` | yes |
| App icons | the manifest's emoji today; a line glyph per app proposed, tinted with its atmosphere | manifests | partial |
| Status symbols | dot + word (ok, look, unread, bad) | Diagnostics, cards | yes |
| Kind marks | Real / Simulated / Game (REQ-DSK-021) | new | no |
| The orb | her mark; the app icon of MIA itself | `shell.js` | yes |

**Rules:** an icon never stands alone for an action without a label or tooltip; meaning icons (warning, error) pair
with their colour and a word; icon packs (personalisation) replace interface glyphs only, never the orb or meaning
symbols. On Linux, MIA's apps ship a matching icon in the freedesktop icon theme so the launcher and KDE show them.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-VIS-008 | Every icon-only control shall have a visible label or tooltip and an accessible name. | Must | MVP | All | Partial | T | DEC-0235 → 11 |
