# MIA OS: existing capability inventory (Prompt 01 §7)

*Claude, 2026-11-15, at `c0a71610`. These are the status words from the
system audit (Verified, Implemented, Partial, Experimental, Documented
only, Planned, Unverified, Deprecated, Broken).*

*"Verified" here means its tests passed in this audit's run
(`MIA_OS_TESTING_AND_QUALITY_AUDIT.md`). A test passing in the cloud is
not the same as working on the PC, the phone or the glasses. Nothing
needing hardware or the live model is marked Verified.*

*"Tests" counts the test files whose names match, a rough measure of
coverage and not a quality score. Readiness for MIA OS is in
`MIA_OS_MIGRATION_READINESS.md`. Prompt 02 will extend this file; it
must keep these statuses evidence-based.*

## Core assistant and intelligence

| Feature | Front end | Back end | Tests | Status | Limits and notes |
|---|---|---|---|---|---|
| Conversation (Talk) | `web/shell.js` Talk, Qt assistant | `core/assistant_turn.py`, `assistant_chat.py` | many | Verified (scripted model) | live-model quality unverified here |
| Tool routing (~378 tools) | — | `core/assistant_actions.py`, `matching_actions.py` | many | Verified | phrase and domain matching, not semantic |
| Conversation modes, support choice | Talk | `core/conversation_modes.py`, `talk_it_out.py` | yes | Verified | |
| Game Master | Talk | `core/game_master.py` | via dungeon tests | Implemented | new (DEC-0046) |
| Memories about the person | Memories app | `core/user_memory_manager.py` | yes | Verified | LLM pulls them out; keyword match |
| Self-knowledge, capabilities, service map | Talk answers | `core/self_knowledge.py`, `capabilities.py`, `service_map.py` | yes | Verified | built from code, not a brochure |
| Model registry, three levels | Settings | `core/model_registry.py`, `home_link.py` | yes | Verified (no live model) | |
| Fix-It Log | `web/issues.html` | `core/failure_log.py` | 1 file | Verified | new (DEC-0049) |
| Safety floor | all turns | `core/safety_floor.py`, `core/region.py` | yes | Verified | never uses the model |
| Communication gate | — | `core/communication_gate.py` | yes | Verified | 5 a day limit |
| Development council, agents, lab | `web/dev*.html` | `core/council*.py`, `work_agents.py`, `dev_lab.py` | 4+ files | Implemented / Experimental | owner only; cloud accounts |
| Inspection ("Inspect skill") | Talk | `core/inspection.py` | 1 file | Verified | read-only audits |
| Browser with commit gate | Talk | `core/browser*.py` (Playwright, Edge) | 1+ | Implemented | Edge on the PC; not run here |
| Online lookup | Talk | `core/online_lookup.py` | yes | Implemented | only when asked (DEC-0053) |
| Wake word "Hey MIA" | — | none found | — | Planned | `docs/CAPABILITY_CHECKLIST.md` |
| Speaker identification | — | none found | — | Planned | needed for shared conversation |
| Phone-call conversation mode | — | `docs/CONVERSATION_MODE_PLAN.md` | — | Documented only | |

## Life management

| Feature | Back end | Tests | Status |
|---|---|---|---|
| Dashboard (Today, Your Week, weather, mission in play, Agent Activity) | `core/web_surfaces.py`, `core/agent_activity.py`, `core/weather.py` | yes | Verified (weather fetch needs the network) |
| Calendar, reminders, alarms | `core/calendar*`, alarm tool | 2+ | Verified |
| Notes, private journal | notes and journal managers | 5 | Verified |
| Missions, projects, XP, character | `core/mission_manager.py`, `projects`, DEC-0152 | 9 + 5 | Verified |
| The Loop, Sunday check-in | `core/the_loop.py`, `core/weekly_checkin.py` | 1 + via loop | Verified |
| The Dungeon (work as runs, loot, bosses) | `core/work_dungeon.py` | 1 | Verified (calculations); bank link by Plaid unverified |
| Learning paths, guitar, Trade Master, Classroom | `core/paths.py`, `guitar.py`, `trade_jobs.py`, classroom | 1, 1, 3, 3 | Verified |
| Natural Momentum (mornings) | DEC-0148 code | yes | Implemented |
| Inbox, email drafts (never sends) | `core/email_drafts.py`, inbox | 3 | Verified; sending only by a person |
| Life notes ("keep it") | `core/life_notes.py` | yes | Verified |

## Home, homestead, finance, health

| Feature | Back end | Tests | Status |
|---|---|---|---|
| Kitchen (pantry, recipes, food table) | kitchen managers, `data/foods.tsv` | 3 | Verified |
| Maintenance and upkeep missions | `core/upkeep_missions.py`, maintenance | 3 | Verified |
| Garage, property, rentals, inventory | managers and modules | 1+ | Implemented |
| Homestead, greenhouse, aquaponics | `homestead/` (own suite of 245 scenarios), `core/greenhouse_*.py`, `homestead_manager.py` | 4 + 3 + own | Implemented, simulation-first; its own suite wasn't run in this audit |
| Smart devices, cameras | `core/device_framework.py`, `security_cams.py` | yes | Implemented; hardware not run here |
| Finances (budget, Plaid, snapshots) | `core/finance_manager.py`, `budget_manager.py`, `plaid_manager.py` | 2 + 4 | Verified offline; Plaid is a cloud service |
| Businesses, orders, quotes | `core/business_book.py`, `web_businesses.py` | 6 | Verified |
| Workout Tracker | `core/workout_manager.py`, `modules/workout` | 2 | Verified |
| Health › meals | — | — | Planned (NEXT_SESSION) |

## Recreation and worlds

| Feature | Back end | Tests | Status |
|---|---|---|---|
| Music, media | music module, `web/sound.js` | yes | Implemented |
| Memory Vault (phone photos and captions) | `core/memory_vault.py`, `vault_captions.py` | 1 | Implemented; captions need the model |
| Living Worlds (universes, campaigns) | `core/living_worlds.py`, `web_nexus.py` | 1 + 1 | Experimental (Phase 1 data models) |
| The Convergence | named in `core/living_worlds.py` | — | Planned ("Phase 4") |

## Devices and platform

| Feature | Where | Status |
|---|---|---|
| Phone app with its own engine | `android-phone/` | Implemented; CI test builds |
| Companion app (thin client) | `android/` | Implemented; overlaps with the above |
| Glasses: toolkit, camera, display cards, relay | `MetaGlasses.kt`, `GlassesCamera.kt`, `core/glasses_cards.py`, `relay/` | Implemented, gated by Meta's toolkit |
| Autofill | `MiaAutofillService.kt` | Implemented |
| Phone ↔ PC sync | `core/sync.py` | Verified (tests) |
| Encryption at rest | `core/at_rest.py` | Verified on the Windows code path in tests; **not available on Linux or Android** |
| Nightly encrypted backups, restore | `core/backup_manager.py` | Verified (tests) |
| Parity (every action a tool and a control) | `core/parity.py` | Verified |
| Pi kiosk | `deploy/` | Implemented; hardware unverified |

## Updated by Prompt 02 (2026-11-15)

- **Smart Closet**: Committed (DEC-0162); a minimum version is being built. See `docs/specs/SMART_CLOSET.md`.
- **Life Enrichment Protocol**: Committed (DEC-0161). The spec is in `docs/specs/LIFE_ENRICHMENT_PROTOCOL.md`; not built.
- **Speaker identification and shared conversation**: Committed (DEC-0163); not built.
- **Send to MIA on a selection**: Proposed (DEC-0164); not built.
- **The Companion app (`android/`)**: Deprecated and **removed** (DEC-0160).

How these relate is in `MIA_OS_FEATURE_ECOSYSTEM.md` and `MIA_OS_CAPABILITY_CLASSIFICATION.md`.

## Zac's named features not in the repo (as found by Prompt 01)

These were checked by searching the code for their names on 2026-11-15:
- **Smart Closet**: Documented only. The single code hit is a chore name, "Clear out a closet".
- **Life Enrichment Protocol**: Documented only. Related code exists: `core/paths.py`, Natural Momentum and the Loop.
- **Multi-Person / Shared Conversation Mode**: Planned (an unchecked checklist item). It needs speaker identification, which also doesn't exist yet.

## Overlaps found

- Two Android apps (`android/`, `android-phone/`).
- Two front ends for the same apps: the Qt classic view and the web. `docs/WEB_PARITY.md` tracks the gap.
- Pay and shift data in the Dungeon versus the Loop's work rhythm. Both are reconciled in code, but each keeps its own record (`docs/BODY_AND_RELATIONSHIP_PLAN.md`).
- Several "what can MIA do" sources (`capabilities.py`, `self_knowledge.py`, `service_map.py`, `docs/ASSISTANT_CAPABILITIES.md`). Each is built from code, but they cover overlapping questions.
