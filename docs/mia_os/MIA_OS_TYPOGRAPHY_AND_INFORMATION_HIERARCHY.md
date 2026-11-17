# MIA OS: typography and hierarchy (Prompt 11 §5)

*Claude (Opus), 2026-11-17. Planning only.*

| Use | Face | Today | On MIA OS |
|---|---|---|---|
| Interface and reading | system sans (`--font`) | Segoe UI Variable on Windows | Inter (shipped in the image, open licence) or Noto Sans; offline, no web fonts |
| Technical labels, numbers | mono (`--font-mono`), tabular | Cascadia/Consolas | JetBrains Mono or Noto Sans Mono |
| Display (large numbers, ambient clock) | the sans, light weight | — | same |

**Scale:** sizes from a base times `--scale` (follows the system's text scaling): caption, body, title, headline,
display. **Hierarchy:** one headline per screen; labels uppercase mono with `--label-track`; numbers tabular so
columns align. **Density** compact reduces spacing, never type below body size. **Language:** plain words
(`docs/design/MIA_VOICE.md`); a technical term only where he'd use it.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-VIS-005 | Type shall scale with the system's text size and never fall below body size in compact density. | Must | MVP | All | Partial | T | DEC-0234 → 11 |
| REQ-VIS-006 | MIA OS shall ship its fonts in the image; no screen loads a font from the internet. | Must | MVP | PC | Exists (system fonts) | T | DEC-0234 → 11, 14 |
