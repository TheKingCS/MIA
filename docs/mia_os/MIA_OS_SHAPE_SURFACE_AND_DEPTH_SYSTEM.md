# MIA OS: shape, surface and depth (Prompt 11 §6)

*Claude (Opus), 2026-11-17. Planning only. The tiers are DEC-0186's.*

| Surface tier | Used for | Alpha | Blur (px) |
|---|---|---|---|
| deep | the field behind everything, the backdrop's veil | 0–0.95 | 0–32 |
| primary | the main content panel | 0–0.92 | 0–24 |
| secondary | cards inside it | 0–0.85 | 0–16 |
| floating | Talk, menus, the approval card | 0.80–0.97 | 0–28 |
| interactive | buttons, chips, inputs | 0–0.80 | 0–12 |

(the clamps in `core/themes.TIER_RANGES`; a theme's values outside them are pulled in.)

**Shape:** `--radius` and `--radius-sm` per theme (Stark 6 px, Glass wide curves); the orb is the only circle of its
size. **Depth:** layers read by tier and shadow, not borders; elevation order: deep < primary < secondary < floating;
the approval card is always floating, above all else. **Effects off** (`effects: none`): every tier solid, no blur,
shadows kept; the layout is unchanged.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-VIS-007 | With effects off, every surface shall be solid with no blur, and nothing shall move or disappear. | Must | MVP | All | Exists (effects) | T | DEC-0235 → 11 |
