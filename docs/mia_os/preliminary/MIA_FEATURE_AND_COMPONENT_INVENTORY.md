# MIA feature and component inventory, classified for MIA OS

> **Prompt 17 (2026-11-18):** superseded by Prompts 01 to 17 and kept for history only; `MIA_OS_FINAL_MASTER_IMPLEMENTATION_BLUEPRINT.md` governs.

*Claude, 2026-11-13. Built from the code (`docs/ATLAS.md`, `docs/MIA_MAP.md`,
`docs/CAPABILITY_CHECKLIST.md`), not from the feature list. The list isn't
exhaustive: MIA has ~378 tools and ~90 stores. This groups them into
components an OS plan has to account for.*

**Classes**

- **A**: reusable as is.
- **B**: reusable after refactoring.
- **C**: needs redesign.
- **D**: planned (not built).
- **E**: experimental (built, not settled).

## 1. Foundation

| Component | Where | State | Class | Note for MIA OS |
|---|---|---|---|---|
| Action contract (propose → approve → execute → record → undo) | `core/actions.py`, `core/undo_log.py` | Real | **A** | The gate every OS action goes through |
| Stores and atomic writes | `core/atomic_write.py`, `core/personal_data.py` | Real | **A** | Runtime owns them |
| Store lock (one writer per data folder) | `core/application.py`, server | Real | **B** | Moves into the runtime service |
| Life events, links, Life State | `core/life_events.py`, `core/links.py`, `core/context_assembler.py` | Real | **A** | The OS's picture of the person |
| Event bus | `core/event_bus.py` | Real | **B** | In-process only; needs cross-process events |
| Live counter | `core/live.py`, `/api/live` | Real | **A** | First IPC channel |
| Config and person settings | `core/config_manager.py`, `core/person_settings.py` | Real | **A** | |
| Profiles, sign-in, two-step, households | `core/profile_manager.py`, `core/two_step.py`, `core/household_manager.py` | Real | **A** | Map onto OS accounts later, don't replace |
| Communication gate | `core/communication_gate.py` | Real | **A** | Becomes the OS notification policy |
| Module discovery (Qt) | `core/module_manager.py` | Real | **B** | Keep for the classic view; needs sandboxing for third-party |
| Scheduler (10 Qt timers, ~43 daily checks) | `core/application.py` | Real | **C** | Redesign as a runtime scheduler with no Qt |
| API server | `core/phone_server.py`, `server/app.py` | Real | **B** | Hosted by the runtime, not the window |
| Headless runtime | `core_main.py`, `core/core_runtime.py` | Real, narrow | **B** | The seed of the MIA Runtime |
| Encryption at rest | `core/at_rest.py` | Real (Windows, Android) | **B** | Needs a Linux key backend (TPM2 / systemd-creds) |
| Backups | `core/backup_manager.py` | Real | **A** | Scheduled by the runtime |
| Sync | `core/sync.py` | Real | **A** | |
| Home link and heavy jobs | `core/home_link.py`, `core/heavy_jobs.py` | Real | **A** | |
| Security log, sign-in guard, secrets vault | `core/security_log.py`, `core/sign_in_guard.py` | Real | **A** | |

## 2. Intelligence

| Component | Where | State | Class | Note |
|---|---|---|---|---|
| LLM backends (Ollama, llama-server) | `core/llm_manager.py` | Real | **A** | Ollama runs on Linux with ROCm/Vulkan |
| Model registry and three levels | `core/model_registry.py` | Real | **A** | |
| Assistant turn, chat, tool routing | `core/assistant_turn.py`, `core/assistant_chat.py`, `core/matching_actions.py` | Real | **A** | |
| Tool registry (~378) | `core/assistant_actions.py` | Real | **B** | Needs capability grants for system tools |
| Presence and context | `core/presence.py` | Real | **A** | Gains system context (focus, running apps) |
| Self-knowledge, service map, atlas | `core/self_knowledge.py`, `core/service_map.py`, `core/code_atlas.py` | Real | **A** | The OS exposes itself through these |
| Personality, answer style, directions | DEC-0114/0138/0141 | Partly real | **E** | |
| Conversation modes, Game Master | `core/conversation_modes.py`, `core/game_master.py` | Real | **A** | |
| Safety floor | `core/safety_floor.py` | Real | **A** | Never depends on the model |
| Fix-It Log | `core/failure_log.py` | Real (new) | **E** | |
| Council, work agents, dev lab | `core/council*.py`, `core/work_agents.py`, `core/dev_lab.py` | Real | **E** | The template for OS agents and permission tiers |
| Browser with a commit gate | `core/browser*.py` | Real (Edge, Playwright) | **B** | Edge is Windows-first; Chromium on Linux |
| Inspection | `core/inspection.py` | Real | **A** | |
| Taught procedures | DEC-0123 | Proposed | **D** | |

## 3. Interfaces and devices

| Component | Where | State | Class | Note |
|---|---|---|---|---|
| Web front end and frame | `web/`, `web/shell.js` | Real | **A** | Becomes the MIA OS shell |
| Eight destinations | `core/web_areas.py` | Real | **A** | |
| Qt desktop (classic view) | `gui/`, `modules/` | Real | **B** | Kept; runs as a client |
| Desktop host window | `gui/main_window.py` web mode | Real | **B** | On Linux, replaced by a kiosk browser session |
| Voice (Vosk, Piper, Kokoro) | `core/voice_manager.py` | Real | **A** | All run on Linux |
| Wake word "Hey MIA" | checklist | Not built | **D** | |
| Phone app | `android-phone/` | Real | **A** | Stays an Android app |
| Glasses (toolkit, relay, cards) | `MetaGlasses.kt`, `relay/`, `core/glasses_cards.py` | Real, gated | **A** | Unchanged by MIA OS |
| Autofill | `MiaAutofillService.kt` | Real | **A** | |
| Device framework, port scanner | `core/device_framework.py`, `core/port_scanner.py` | Real | **B** | Behind the hardware layer |
| Cameras | `core/security_cams.py` | Real | **A** | |
| GPIO push-to-talk | `core/push_to_talk_source.py` | Real | **A** | Pi |
| Device fabric | DEC-0128 | Proposed | **D** | Becomes the hardware layer's model |
| Kiosk deployment | `deploy/` | Real (Pi) | **B** | The pattern the PC image reuses |
| Windows install and stay-up | `install.ps1`, `pc_stay_up.ps1` | Real | **A** | Kept for Windows |

## 4. Zac's named features

| Feature | Where | State | Class | Note |
|---|---|---|---|---|
| Workout Tracker | `core/workout_manager.py`, `modules/workout` | Real | **A** | |
| Smart Closet | none | Not built | **D** | Not in the repo; would be a new store and screen |
| Memory Vault | `core/memory_vault.py`, `core/vault_captions.py` | Real | **A** | Phone photos; captions need the model |
| Finances (budget, Plaid, summaries) | `core/finance_manager.py`, `core/budget_manager.py` | Real | **A** | Bank read-only |
| Businesses | `core/business_book.py`, `core/web_businesses.py` | Real | **A** | |
| Homestead, greenhouse, aquaponics | `homestead/`, `core/greenhouse_*.py`, `core/homestead_manager.py` | Real (simulation-first) | **A** | Self-contained subproject; nodes are hardware |
| Life Enrichment Protocol | none by that name | Not built | **D** | Related pieces exist: learning paths (`core/paths.py`), Natural Momentum (DEC-0148), the Loop. Needs a definition from Zac |
| Multi-Person / Shared Conversation Mode | checklist item, unchecked | Not built | **D** | Needs speaker identification (also not built) |
| Inspect skill | `core/inspection.py` | Real | **A** | |
| Game Master / Dungeon | `core/game_master.py`, `core/work_dungeon.py`, `core/the_loop.py` | Real (new) | **E** | DEC-0046/0047 |
| Living Worlds / Convergence | `core/living_worlds.py`, `core/web_nexus.py` | Phase 1 data models | **E** | DEC-0134, DEC-0153 |

## 5. Everything else, in brief

Kitchen, calendar, inbox, maintenance, garage, property, rentals, notes,
journal, relationships, classroom, guitar, learning paths, Trade Master,
missions and projects, XP and character: real, engine-side, served on the
web: **A**. None depends on the OS. The Qt modules for them are **B**
(kept as the classic view).

## 6. What this means

About 85% of MIA is **A**: it moves to an OS unchanged because it never
knew what OS it was on. The work is concentrated in five places:

1. the scheduler (**C**);
2. the runtime host (**B**);
3. the key backend (**B**);
4. capability grants for system tools (**B**);
5. the desktop host window (**B**).

None of Zac's named features blocks or is blocked by MIA OS. The **D**s
(Smart Closet, Life Enrichment, Shared Conversation, wake word) can be
built now on the current engine and carry over.
