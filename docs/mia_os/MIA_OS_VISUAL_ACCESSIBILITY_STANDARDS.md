# MIA OS: visual accessibility (Prompt 11 §19)

*Claude (Opus), 2026-11-17. Planning only. Desktop accessibility: Prompt 10.*

| Standard | Rule |
|---|---|
| Contrast | WCAG 2.2 AA on every theme and tier (REQ-VIS-003) |
| Colour independence | every state has a word or icon (REQ-DSK-026) |
| Motion | `prefers-reduced-motion` and her own setting; no flashing over 3 Hz |
| Focus | a visible focus ring in every theme, 2 px, accent or ink |
| Text size | follows the system; layouts reflow to 200 % |
| Transparency | a "reduce transparency" choice = effects none |
| Targets | 44 px desktop, 48 dp phone |
| Glasses | high contrast by construction (light on see-through black) |
| Themes | a theme that fails these is refused (REQ-VIS-013) |

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-VIS-025 | Every theme shall show a visible focus ring and reflow without loss at 200 % text size. | Must | R1 | All | Partial | T | DEC-0235 → 11 |
