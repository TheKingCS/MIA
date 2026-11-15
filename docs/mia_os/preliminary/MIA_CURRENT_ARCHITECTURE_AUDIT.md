# MIA's current architecture: an audit for MIA OS

> **Superseded (2026-11-15)** by `../MIA_OS_EXISTING_SYSTEM_AUDIT.md`. Correction: the phone does **not** seal data with the Android Keystore yet; `core/at_rest.py` seals only under Windows DPAPI.

*Claude, 2026-11-13. Every claim here was checked against the code at
commit `c0a71610` (origin/master), not only against the docs. Where a
doc and the code disagree, the code wins and the gap is noted.*

## 1. Size and shape

- 1,380 files, ~307,000 lines (`docs/ATLAS.md`, generated from the code
  by `python -m core.code_atlas`; a test keeps it current). 16,853 of
  16,947 functions and classes are documented.
- `core/` 521 files (~151k lines): the engine. `modules/` 93 Python
  files (the Qt desktop apps), `gui/` 123 (the Qt shell), `server/`
  (the FastAPI API), `web/` (the one web front end), `android-phone/`
  (the Android app: 19 Kotlin files plus the bundled engine),
  `relay/` (a Cloudflare Worker for the glasses), `homestead/` (the
  greenhouse/aquaponics subproject: firmware, drivers, scenarios;
  DEC-0145), `tools/` (CLIs), `tests/` (~4,600 tests), `work/` (the
  development platform's ledger and knowledge).
- ~150 logged decisions (`docs/DECISIONS.md`), ~378 assistant tools
  (`docs/ASSISTANT_CAPABILITIES.md`), 45 personal and 41 household
  stores, 50 sealed at rest (`docs/MIA_MAP.md`).

## 2. Layering (the property that makes an OS possible)

`core/` never imports `gui/` or `modules/`; modules reach the screens
only through `ModuleBase.get_widget()`; the web talks to the engine only
through `web/mia.js` and the API (`docs/ARCHITECTURE.md`, held by
convention and by tests). **Verified:** `core_main.py` boots a headless
engine that never imports PySide6 (`core/core_runtime.py`), and the
Android app runs the same `core/` under Chaquopy. The intelligence is
already OS-independent at the code level.

## 3. Processes and runtime (the main finding)

| Deployment | Entry point | What runs | Status |
|---|---|---|---|
| PC (Windows) | `main.py` → `core/application.py` `MIAApplication` | Qt app; the web front end in a Qt web view (DEC-0124); the API server (uvicorn) on a thread (`core/phone_server.py`); **10 Qt timers**, one of which runs ~43 daily checks every 5 minutes (the Loop, backups, occasions), plus finance and homestead snapshots, inbox, alarms, power, online and mission checks | Real, daily use |
| Pi / headless | `core_main.py` → `core/core_runtime.py`, `core/voice_loop.py` | push-to-talk voice loop over the engine | Real but narrow: **no API server, no scheduler** |
| Phone | `android-phone/` (Kotlin + Chaquopy) | the engine and the API inside the app; web front end in a WebView; voice, places, gallery, glasses toolkit, autofill | Real (test builds) |
| Glasses | Meta Wearables toolkit via the phone + a Web App over `relay/` | read-only Home and selected cards (DEC-0062, DEC-0066) | Real, gated |
| Greenhouse nodes | `homestead/firmware` | sensor/actuator nodes reporting to MIA | Partial |

**Finding 1: MIA's runtime is the desktop window's process.** Background
work (scheduling, reminders, backups, the server) lives inside
`MIAApplication` and its Qt event loop. Close the window and MIA stops
serving the phone, reminding and backing up. The headless runtime lacks
both the server and the scheduler. This is the first thing an OS needs
fixed, and it is valuable on Windows too.

**Finding 2: one writer per data folder.** Stores are JSON/JSONL files
written through `core/atomic_write.py` under one store lock shared by
the server and the timers ("one MIA per data folder", K-0218 era
commits `bfc18243`). That suits a single runtime process that owns the
data, with every interface as a client: the target shape.

**Finding 3: the event bus is in-process and synchronous**
(`core/event_bus.py`, deliberately not thread-safe). Cross-process
notification today is `core/live.py` (a counter bumped by every write)
polled or streamed over `/api/live`. An OS runtime needs a real IPC
story; the API plus `/api/live` is a workable start.

## 4. Subsystems

**Intelligence and personality.** Facts assembled in code, the model
phrases (DEC-0004). Context in every turn (`core/presence.py`), the
reasoning layer (DEC-0052), self-knowledge from records
(`core/self_knowledge.py`, DEC-0142), what she runs on
(`core/service_map.py`, DEC-0151), personality (DEC-0114 proposed,
answer-style learning DEC-0138, standing directions DEC-0141), Game
Master and the Loop (DEC-0046/0047).

**Models.** `core/llm_manager.py`: `OllamaBackend` (PC, default) and an
OpenAI-compatible backend for `llama-server` (phone); three levels picked
automatically (DEC-0022): the phone's model, the PC's over the home link
(`core/home_link.py`), online lookups when asked (DEC-0053).
`core/model_registry.py` reads the live runtime's facts. The PC model is
qwen2.5:14b on an RX 7900 XTX (24 GB). The owner-only development
council also reaches cloud AI accounts (`core/council*.py`).

**Memory and persistence.** Per-store JSON/JSONL in `data/` (personal
under `data/profiles/<id>/`, household shared), atomic writes with undo
(`core/undo_log.py`), history beside the stores (`core/life_events.py`,
DEC-0006), links (`core/links.py`), the Life State read model
(DEC-0005), sealed at rest with AES-256-GCM (`core/at_rest.py`, keys
under Windows DPAPI / Android Keystore, DEC-0126), nightly encrypted
backups (`core/backup_manager.py`). SQLite only in the development
platform (`core/council.py`, `core/dev_store.py`) and two device stores.

**Voice.** `core/voice_manager.py` with backend interfaces: Vosk (STT)
and Piper (TTS) on CPU, Kokoro as the PC's voice (DEC-0051); the phone
uses Android's recognizer and TTS (`Voice.kt`, `PhoneVoice.kt`); heavy
speech falls back to the PC (`core/heavy_jobs.py`). Push-to-talk can be
a GPIO pin (`core/push_to_talk_source.py`). A phone-call conversation
mode is planned (`docs/CONVERSATION_MODE_PLAN.md`), not built.

**Interfaces.** One web front end (`web/`, DEC-0012/0017) for the PC,
the phone and the glasses' Web App; the frame `web/shell.js`; the eight
destinations (`core/web_areas.py`, DEC-0153); two looks and themes as
data (DEC-0135/0136); parity measured app by app (`core/parity.py`,
DEC-0125). The Qt screens remain as the "classic view".

**Phone ↔ PC.** Sync (`core/sync.py`: three-way JSON merge, file blobs
by hash, line-merged histories), the home link, heavy jobs, Tailscale
serve for reach away from home (the server listens on 127.0.0.1).

**Glasses.** Meta toolkit in the phone app (`MetaGlasses.kt`,
`GlassesService.kt`, `GlassesCamera.kt`), the sealed relay for the
display (DEC-0062), glasses cards (`core/glasses_cards.py`).

**Tools, skills and capabilities.** The action contract
(`core/actions.py`: propose → approve → execute → record → undo), the
assistant tool registry (`core/assistant_actions.py`, domain-scoped
attachment, child/tool gating), the capability registry and limits
(`core/capabilities.py`), parity twins (every action a tool and a
control), the browser with a commit gate (DEC-0117/0122), taught
procedures (DEC-0123 proposed), inspection (`core/inspection.py`,
DEC-0056).

**Agents.** Not a general runtime agent system. What exists is the
**development platform** (MIA-DII, DEC-0068–0083): a council of models
(`core/council*.py`), work agents and runners (`core/work_agents.py`,
`core/work_runner.py`), an isolated lab in a git worktree
(`core/dev_lab.py`, DEC-0058), six permission tiers (DEC-0069),
specialists (DEC-0109), Night School (DEC-0100). These are the best
existing model for OS-level agents and their permissions.

**Hardware.** `core/device_framework.py` (USB/serial devices),
`core/port_scanner.py`, cameras on the LAN (`core/security_cams.py`),
GPIO push-to-talk, the greenhouse nodes, the glasses' camera, the PC's
GPU through Ollama. The device fabric (perceive, identify, speak,
extend) is proposed (DEC-0128).

**Security.** `docs/SECURITY.md`: PBKDF2 600k passwords, sign-in guard,
30/90-day tokens, CSP, two-step sign-in, a security log, sealed stores,
encrypted password vault and journal, secrets vault, no secrets in logs
(tested), dependency audit (OSV), MIA drafts but never sends, bank
read-only. **Gaps it records:** modules aren't sandboxed; the PC's drive
isn't encrypted; some features reach outside services by nature.

**Configuration and deployment.** `config/default_config.json` merged
with the person's `config/config.json`; per-person settings
(`core/person_settings.py`). Windows: `install.ps1`, `setup_home_pc.ps1`,
`pc_stay_up.ps1` (restart hours, autologon), `pc_remote_control.bat`.
Pi: `deploy/install_kiosk.sh` (a systemd **user** service and kiosk).

**Testing and CI.** ~4,600 pytest tests; CI on Windows (installer +
tests), the Android build (a published test APK), Pages (the preview),
the model check, the food table; `tools/page_check.py` opens every page;
a turn harness with a scripted model; a test guard on writes into the
real tree; the atlas regenerated from a clean checkout.

**Documentation and self-documentation.** The atlas, the map, REBUILD,
decisions, knowledge entries (`work/knowledge/`), improvement loops
(94, DEC-0094/0101), the operating journal.

## 5. Strengths to build on

1. Engine-first layering, already proven headless and on Android.
2. One action contract with undo for every change, from every surface.
3. One web front end for every device.
4. A security baseline well above typical hobby projects.
5. Self-description (atlas, map, service map) an OS can expose to MIA.
6. A permission-tiered, sandboxed development platform: the template
   for OS-level autonomy.

## 6. Problems an OS would expose (documented, not fixed)

| # | Problem | Why it matters | Where |
|---|---|---|---|
| P1 | Runtime lives in the Qt window | closing the window stops MIA; no service identity | `core/application.py` |
| P2 | Headless runtime lacks server and scheduler | Pi and a future OS service can't host her fully | `core/core_runtime.py` |
| P3 | Background jobs are Qt timers | can't run without Qt; not supervised or observable | `core/application.py` (10 timers) |
| P4 | Key protection is DPAPI / Keystore only | no Linux key path; sealed stores won't open on Linux | `core/at_rest.py` |
| P5 | Windows-specific scripts carry deployment | nothing reproducible for a Linux image | `install.ps1`, `pc_stay_up.ps1` |
| P6 | Modules run with full privileges | an OS can't allow that for third-party code | `core/module_manager.py` |
| P7 | No capability permissions beyond child gating and the contract | OS actions need per-capability grants | `core/assistant_actions.py`, `core/actions.py` |
| P8 | In-process synchronous event bus | no cross-process events | `core/event_bus.py` |
| P9 | Duplicate sources of truth (pay, training days, chores) | an OS-wide user model needs one owner per fact | `docs/BODY_AND_RELATIONSHIP_PLAN.md` |
| P10 | Docs drift (e.g. DEC-0115/0119 vs DEC-0050/0127 on who MIA is for) | planning assumptions conflict | `docs/DECISIONS.md` |
