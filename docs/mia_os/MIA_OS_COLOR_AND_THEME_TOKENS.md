# MIA OS: colour and theme tokens (Prompt 11 §4)

*Claude (Opus), 2026-11-17. Planning only. Values are Muse's; meanings are fixed.*

## 1. Colour roles

| Role | Token | Meaning | Theme may change |
|---|---|---|---|
| Field and depth | `--bg`, `--rgb-panel` to `-3`, `--surface-solid` | the room and its layers | yes |
| Ink | `--text`, `--text-dim`, `--text-faint` | reading | yes, within contrast |
| MIA | `--accent`, `-soft`, `-deep` | her, active, selected, progress | yes (scheme) |
| Second and third accents, charts | scheme tokens | data series | yes |
| App atmosphere | `--mod-*` | an app's own data and header motif only (DEC-0187) | yes |
| Done | `--ok` green | healthy, finished | **no** |
| Needs you | `--attention`, `--soon` amber | approval, due | **no** |
| Error | `--bad` red | real errors, destructive | **no** |
| Earned | `--win` gold; legendary orange for rewards (DEC-0186) | celebration only | **no** |

## 2. Rules

- **Contrast:** body text 4.5:1 and large text and controls 3:1 against every panel tier it can sit on, checked in
  code for every theme (a test over `THEMES`).
- **Never colour alone:** each meaning colour comes with a word or icon.
- **Light and dark:** a light theme sets the field light and the ink dark; meaning colours keep their hue with
  adjusted lightness for contrast.
- **High contrast:** solid surfaces (alpha 1, no blur), ink pure, accent at full saturation, borders 2 px.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-VIS-003 | Every theme shall meet 4.5:1 for body text and 3:1 for large text and controls on every surface tier, checked by a test over all themes. | Must | R1 | All | Partial (AA proposed) | T | DEC-0235 → 11 |
| REQ-VIS-004 | Meaning colours (done, needs you, error, earned) shall not be settable by a theme or a person. | Must | MVP | All | Exists | T | DEC-0236 → 11 |
