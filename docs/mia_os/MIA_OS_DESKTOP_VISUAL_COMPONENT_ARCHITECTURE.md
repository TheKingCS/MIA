# MIA OS: the shell's component architecture (Prompt 10 §20)

*Claude (Opus), 2026-11-17. Planning only. The look is Prompt 11's; glass and Aquatic are DEC-0183.*

| Primitive | Today | Role |
|---|---|---|
| Frame | `web/shell.js` | sidebar, Talk, search, act, presence, theme |
| Layout containers | `layout-main`, `home-main`, two-column grid | responsive regions |
| Card | `glass`, `dash-*` | one thing with its status and action |
| Panel | Talk, details panels | slide-over, collapsible |
| Dialog | the approval card (`confirmBox`) | the only place a change is approved |
| Toast | undo toast | after a change |
| Lists and rows | `dx-row`, `dx-list` | records |
| Menus, toolbars | buttons in pages | per app |
| Status | dots with words | never colour alone |

**What a theme may change:** tokens (colour, type, radius), material (the five glass tiers, DEC-0186, clamped by
`TIER_RANGES`), density, motion, icons, the 3D room's light. **What it may not:** data, actions, order of steps,
meaning colours (`tests/test_appearance.py`).

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DSK-029 | A theme shall change only tokens, material, density, motion and icons, never data, actions or meaning colours. | Must | MVP | All | Exists | T: appearance tests | DEC-0184 → 10, 11 |
