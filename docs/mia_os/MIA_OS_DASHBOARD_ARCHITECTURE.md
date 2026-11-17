# MIA OS: dashboards (Prompt 10 §5)

*Claude (Opus), 2026-11-17. Planning only.*

## 1. What exists

Home (`core/web_surfaces.py`: the day, what's due with its suggested action, her messages), and each area's
dashboard (`core/web_areas.dashboard`: a card per app with its headline and count). The data is assembled in core and
the page only formats it.

## 2. The widget contract

| Field | Meaning |
|---|---|
| id, title, area | which card, in which dashboard |
| source | the engine call it reads (`/api/state` section or an app's assembler) |
| status | REAL, DERIVED, SIMULATED, STATIC or PLANNED, as the Life State does (`docs/schema/life_state.schema.json`) |
| as_of | when its data was read; stale past its refresh interval is shown as such |
| refresh | re-read on `/api/live`'s signal, never polled faster |
| action | the suggested action on the one change path, if any |
| failure | "couldn't read" with why, never an empty card that looks like nothing to do |
| who | person or household store (privacy below) |

## 3. Personal without clutter

- **Ranked, not piled:** Home shows what's due and what changed first; a card with nothing new is collapsed.
- **Chosen, not added:** each dashboard's cards are the area's apps; he can pin, hide and reorder them (a setting
  per person), not paste in unrelated widgets.
- **Several dashboards:** Home, each area, and the ambient display (Q-80).
- **Shared views** show household stores only (calendar, kitchen, maintenance), never a personal store
  (`HOUSEHOLD_STORES` vs `PERSONAL_STORES`).

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DSK-005 | Every dashboard card shall carry its status (real, derived, simulated, static, planned) and the time of its data, and show "couldn't read" with why instead of an empty card. | Must | R1 | All | Partial (Life State statuses) | T | DEC-0228 → 10 |
| REQ-DSK-006 | Dashboard cards shall be re-read on the live signal, never polled, and pinned, hidden and ordered per person. | Should | R1 | All | Partial (live re-read) | T | DEC-0228 → 10 |
