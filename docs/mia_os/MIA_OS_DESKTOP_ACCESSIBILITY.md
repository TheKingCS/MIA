# MIA OS: accessibility (Prompt 10 §17)

*Claude (Opus), 2026-11-17. Planning only.*

| Need | How | Exists |
|---|---|---|
| Keyboard only | every control reachable by Tab; shortcuts (Ctrl+K, "/", Meta+Space); focus visible | partial |
| Screen reader | the web shell's ARIA roles (`aria-labelledby`, `sr-only` text); Orca over AT-SPI via Qt WebEngine | partial |
| High contrast, text scaling | a high-contrast colour scheme; rem-based type following the system scale | partial |
| Colour independence | states carry a word or icon with the colour (Diagnostics' dots have text) | partial |
| Reduced motion | `prefers-reduced-motion` honoured; KDE's animation setting | partial |
| Captions | her spoken replies shown as text in Talk | yes |
| Touch, stylus | targets ≥ 44 px; KWin's touch gestures | partial |

**Usable without AI:** every function has a screen control (DEC-0125); the model being down never hides a control.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DSK-026 | The shell shall be fully usable by keyboard and with Orca, and no state shall be shown by colour alone. | Must | MVP | PC | Partial | T: an accessibility check per page | DEC-0228 → 10, 11 |
