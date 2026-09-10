# MIA Roadmap

**See also: `docs/VISION.md`** — the long-term, four-project mission
behind MIA (this device is "Project 1: The Brain" of that larger
picture). This document is the near-term execution plan; VISION.md is
the North Star. Keep them separate — see VISION.md's "why this is a
separate document" section for why that distinction matters.

This is the living plan for MIA beyond v0.1. It exists so scope
decisions made in conversation don't get lost — update it whenever the
plan changes.

## Design principles carried forward from the original brief

- Offline-first for everything possible; network features (wifi,
  bluetooth, mesh, SDR) are additive, never required
- No unnecessary redundancy — shared core services over duplicated
  per-domain logic (see "Shared core services" below)
- Don't reinvent the wheel — integrate proven offline-first tools
  (Kiwix for reference content, MAVLink for drones, Meshtastic for LoRa
  mesh) rather than building equivalents from scratch
- Keep Pi 5 hardware limits in mind: budget CPU/RAM/storage
  deliberately, especially around the AI assistant (see
  `docs/HARDWARE.md`)
- Every feature is a module wherever practical; core stays generic

## Shared core services (built once, used everywhere)

These exist to eliminate redundancy across the ~15 domain sections.
Building these as core services rather than per-module logic is what
keeps the module count manageable as the feature list grows:

| Service | Used by |
|---|---|
| **Reference Library** (indexed/searchable document + PDF + Kiwix ZIM viewer) | Wiki, manuals, first aid, electronics datasheets, schematics, repair manuals, species ID, knot guide, mechanical references, programming docs, man pages, Bible, ham cheat sheets |
| **Calculator Engine** (pluggable formula registry, one UI) | Unit converter, calculator, resistor/Ohm's Law/voltage divider/wire gauge, antenna calculator, fuel estimates, coordinate conversion |
| **Data Logger + Charts** (timestamped readings → graphs) | Multimeter logging, soil moisture, power usage, Lab experiments/calibration, sensor testing, vehicle diagnostics |
| **Connected Device Framework** (discover/identify/pair/telemetry/control) | Robots, Drones, Smart Home, Vehicle OBD, Power monitoring, Field Kit's Connected Device Manager. Starts with physically-attached USB/serial devices (v0.11); wifi/Bluetooth discovery is a planned later extension of the same framework, not a separate one — added when that transport is actually built rather than speculatively now |
| **Notes/Journal Engine** (dated, searchable, taggable rich text + voice memo transcription) | Daily journal, Project Manager notes, Lab notes, vehicle notes |
| **Activity/Memory Log** (system-wide event history via the event bus) | Memories section, "what did I do on Project X" queries, Diagnostics history |
| **Global Search** | One search bar over docs, notes, files, inventory, settings, everything |
| **Notification Center** | Any module can raise an alert (low battery, weather warning, medication reminder, backup complete) |
| **Voice Interface (STT/TTS, push-to-talk)** | Assistant, hands-free control of any module |

## Top-level module sections (post-consolidation)

Character and Global Search are system-wide / ambient, not sections
themselves — everything below is a menu section. (Memories was
originally grouped with them here too; promoted to a real section,
#19, per the 2026-07-14 wearable-companion vision update in
`docs/VISION.md` — the user explicitly wants a visitable "Memories
section," not just an ambient widget.)

1. **Assistant** — conversational AI, voice interface, device help, character
2. **Reference Library** — manuals/wikis/guides/PDFs/datasheets/Bible/man pages
3. **Toolbox** — calculator engine, calendar, alarm/stopwatch, journal, inventory, project manager
4. **Files** — browse (USB/SSD/SD/NAS), search, tags, favorites, encryption, compression, preview
5. **Workshop & Electronics** — component DB, MCU flashing, PCB viewer, soldering notes, 3D printer/CNC/laser, STL/CAD library
6. **Fleet** (Robots + Drones + Vehicle) — connected device framework: battery, firmware, sensors, RC, logs, calibration, FPV/camera, GPS, mission planning, maintenance
7. **Communications** — wifi/BT tools, packet sniffer, LoRa/mesh (Meshtastic), SDR, APRS, radio, antenna calc
8. **Navigation** — offline maps, GPS, compass, waypoints, trails, elevation, celestial nav/sun-moon
9. **Power** — battery bank, solar, UPS, generator, charge controllers, usage, fuel
10. **Agriculture** — greenhouse, soil, water tanks, crop planner, plant DB, livestock, chores
11. **Medical** — first aid checklists, symptom lookup, medication log, allergies (personal tracking; reference material lives in Reference Library)
12. **Media** — music, audiobooks, podcasts, ambient sounds, movies, photos
13. **Smart Home** — lights, cameras, locks, blinds, thermostats (local-protocol only, e.g. Zigbee/Z-Wave hub or local Home Assistant — no cloud dependency)
14. **The Lab** — sensor testing, experiments, calibration, graphs (UI home of the Data Logger service)
15. **Diagnostics** — CPU/RAM/storage/temp/network/UPS/sensors, always accessible
16. **System** — settings, user profiles, module manager, notifications, backup/restore, update manager
17. **Field Kit** — connected device detection/identification (USB/serial now, wifi/BT planned), per-device actions (browse files, eject, flash OS + auto-install MIA), useful scripts library, security/network recon + active toolkit, MCU firmware flashing (ties into Workshop & Electronics' own planned "MCU flashing" bullet rather than duplicating it)
18. **Expeditions** — Expedition Mode (v0.12): multi-activity outing tracking (hiking/camping/fishing/kayaking/biking/etc.), gear checklists, trip journal, logged speed/distance, schematic route maps, photos. Built after this list was originally written; added here for completeness.
19. **Memories** (v0.17, built) — auto-generated Expedition recaps aggregated from Expeditions/Trips/Waypoints/Journal/photos (distance, pace, duration, waypoint categories visited), a photo gallery, location-tagged cross-linking into Navigation's route map, and "on this day" resurfacing.
20. **Missions** (v0.18, built) — gamified goals/objectives, optionally tied to a Trip (e.g. "Master Baiter" — catch 3 fish, spend 2 hours fishing) or general (not tied to any outing). Given its own standalone module rather than left ambient — see v0.18's writeup below for why that reverses this doc's earlier tentative "contextual only" note.
21. **Dashboard** (v0.19, built) — read-only at-a-glance summary (recent activity, active Missions, recent Memories, upcoming Calendar events, active Projects/open Tasks), auto-navigated to when Field Kit detects a docked Core and auto-imports its Expedition data, but also a normal always-accessible menu entry.

## Integration decisions (don't reinvent the wheel)

- **Reference content:** use Kiwix (ZIM file format) for offline
  Wikipedia, WikiHow, iFixit, Project Gutenberg, StackExchange dumps —
  don't hand-build a wiki engine or curate raw content from scratch
- **Drones:** target MAVLink (the ArduPilot/PX4 standard protocol)
  rather than a custom telemetry format
- **LoRa/mesh:** integrate with Meshtastic rather than building a mesh
  protocol from scratch
- **Smart home:** local-only — a local Home Assistant instance or
  direct Zigbee/Z-Wave hub, never a cloud-account-dependent ecosystem

## Phase plan

Each phase builds infrastructure the next phase depends on. A short
testing guide accompanies each milestone as it's built — see
`docs/testing/` (created as each milestone lands).

| Phase | Focus |
|---|---|
| **v0.2** | System layer: kiosk boot on Pi 5, user profiles, notifications, backup/restore, local update manager, global search, real Settings UI |
| **v0.3** | Toolbox: calculator engine (unit conversion, Ohm's Law, wire gauge, etc. as plugins), calendar, alarm/stopwatch, journal, inventory, real File Manager |
| **v0.4** | Reference Library engine (Kiwix integration) + initial content packs |
| **v0.5** | Assistant: offline LLM (AI HAT+ 2 / Hailo-10H) + push-to-talk voice interface |
| **v0.6** | Character/companion system — event bus driven, reacts to whatever module is active |
| **v0.7** | Diagnostics + Power monitoring |
| **v0.8** | Workshop & Electronics + The Lab (shared Data Logger) |
| **v0.9** | Activity/Memory Log (shared service) + Memories AI-query — the first v1.0+-bucket slice buildable with zero real hardware |
| **v0.10** | Navigation: Waypoints + Sun/Moon calculator — the second v1.0+-bucket slice buildable with zero real hardware (offline maps/trails/elevation wait for real GPS/mapping data) |
| **v0.11** | Field Kit — Connected Device Framework (core service, USB/serial detection+identification) + Device Manager UI, OS/MIA flashing+provisioning, useful scripts library, security/network toolkit, MCU firmware flashing tie-in — the third v1.0+-bucket slice buildable with zero real hardware beyond a spare USB drive/SD card, at the user's explicit request to turn MIA into a field engineering/programming tool |
| **v0.12** | Expedition Mode — Expedition + Trip core/CRUD with a Trip activity type (hiking, camping, fishing, kayaking, biking, etc.), campsite/waypoint categories, gear checklist (Inventory-linked or freeform), trip journal with an explicit weather/conditions field, speed & distance from logged checkpoints, a schematic (non-tiled) route map, and trip photos — the fourth v1.0+-bucket slice buildable with zero real hardware, at the user's explicit request for field-ready outing tracking across activity types (live GPS, elevation, automated weather, and real map tiles all explicitly deferred — see the v0.12 breakdown) |
| **v0.13** | Device Profile + Theme System — one codebase, config-driven Core (Pi 5 + AI HAT+ 2) vs. Home (desktop) editions, plus a selectable theme system (Dark Field, Low Energy, Colored, Anime Monochrome) applied at the QApplication level so it can differ in weight between editions |
| **v0.14** | Pi 5 + AI HAT+ 2 deployment readiness — documentation/code-audit pass only (no physical hardware yet): deploy script review, flagged the open AI-HAT-inference-path question and polling-interval power budget as real unknowns to revisit once real hardware exists |
| **v0.15** | Expedition data sync — Pi ("Core") exports Expedition Mode data (expeditions/trips/waypoints/journal/inventory/photos) to a docked USB drive via the Field Kit's existing device detection; Home merges it in by record id (no duplication on re-import) |
| **v1.0+** | Fleet (Robots/Drones/Vehicle), Communications, Agriculture, Medical, Smart Home, Project Manager — added incrementally as real hardware for each is acquired (Media/Music built as **v0.20**, 2026-09-09 — the `libpulse` blocker this row used to cite is gone, see that section) |

## Self-Modification / Dev Mode (staged, deliberately separate from the Assistant phase)

A specific, explicit goal for MIA: an assistant that can eventually
help maintain and extend its own codebase. This is the highest-risk
capability on the entire roadmap — for a kiosk-mode offline device with
no easy remote access, "the AI broke its own boot sequence" is close to
the worst possible failure mode. It is staged deliberately, and each
stage requires the previous one to be trusted in practice before moving on:

1. **Read & explain (safe).** The assistant can read the codebase and
   docs and explain what something does or suggest a fix in
   conversation. No file writes at all. Buildable cheaply once the
   Assistant module (v0.5) exists, since it's retrieval + explanation
   over the project's own docs/code.
2. **Propose, don't apply.** The assistant can draft a patch, but it is
   written to a review queue — never applied automatically. The user
   reviews and explicitly approves or rejects it, like a pull request.
3. **Sandboxed self-testing.** An approved patch is applied to an
   isolated copy of the codebase, the existing automated test suite
   runs against it, and only a passing result is promoted to the real
   install — still gated on explicit user confirmation. This is
   exactly why `tests/` and the module test harness were built early
   rather than deferred.
4. **Scoped autonomy (later, optional).** Even at this stage, hard
   scope limits apply: the assistant may create/edit files inside a
   *new* module folder (a broken new module can't take down the rest
   of the system, by the same isolation `ModuleManager` already
   provides for load failures) but should never modify `core/` or
   `deploy/` (boot infrastructure) without the user physically present.

**Supporting infrastructure that should exist regardless of when the AI
part is built:** every change — AI-authored or human-authored — should
go through git, so any regression has a one-command rollback
(`git revert`). Adopting real version control for this project now,
independent of the AI ever touching it, is the single highest-value
habit to start immediately.


## v0.2 breakdown (complete)

Splitting the System layer into small, independently testable milestones:

- [x] **2.1 Kiosk boot infrastructure** — systemd service, autologin,
      fullscreen launch, crash-restart behavior
- [x] **2.2 User profiles** — multi-user support, per-user config/data
      separation, profile switcher on the setup/login flow
- [x] **2.3 Notification Center** — core service + UI (toast/banner +
      a persistent notification list), any module can raise one
- [x] **2.4 Global Search** — index across config, notes, files,
      module metadata; search bar accessible from anywhere
- [x] **2.5 Module Manager UI upgrade** — enable/disable modules,
      reload without full restart
- [x] **2.6 System Logs viewer** — read `logs/mia.log` in-app
      (Diagnostics module's first real feature)
- [x] **2.7 Backup/Restore** — export/import config + data directory
- [x] **2.8 Update Manager (local)** — apply an update package from a
      USB drive/local file, no internet required
- [x] **2.9 Boot animation** — replaced the plain splash-screen text
      steps with a fullscreen "Jarvis-style" boot sequence: a pulsing
      glow core (`gui/boot_core_widget.py`) with "MIA" rendered in
      its center, HUD-style status text, running before the setup
      wizard / profile selector / lock screen is shown.

Each will land as its own milestone with a short manual test checklist.

## v0.3 breakdown (complete)

Splitting the Toolbox phase into small, independently testable milestones,
same pattern as v0.2:

- [x] **3.1 Calculator Engine** — pluggable formula registry
      (`core/calculator_engine.py`, `AppContext.calculators`) with one
      shared browsing UI (new `Toolbox` module); shipped with two
      calculators proving the two calculator shapes this needs to
      support — Unit Converter ("convert A to B": length, weight,
      temperature) and Ohm's Law ("solve for any one of several
      related values" given the others). Future calculator-shaped
      tools (wire gauge, voltage divider, antenna calculator, fuel
      estimates, coordinate conversion, ...) are just new plugins
      registered into the same engine, not new top-level modules.
- [x] **3.2 Calendar** — new `ToolboxTool` concept
      (`modules/toolbox/tool_base.py`), parallel to `CalculatorPlugin`
      for built-in Toolbox features that aren't calculator-shaped.
      Ships with the Calendar tool: a `QCalendarWidget` month grid
      (marked dates) + an agenda panel (Add/Edit/Delete), backed by
      `core/calendar_manager.py` (persisted to
      `data/calendar_events.json`, same durability pattern as
      notifications). Toolbox now shows a Tools section above
      Calculators.
- [x] **3.3 Alarm / Stopwatch** — two more `ToolboxTool`s. Alarm
      (`core/alarm_manager.py`, persisted to `data/alarms.json`) fires
      through the existing Notification Center via a periodic
      `QTimer` owned by `MIAApplication`, so it works regardless of
      which screen is active — no bespoke alert UI needed. Stopwatch
      is purely in-memory (no persistence rationale, unlike
      Calendar/Alarm), but keeps ticking in the background across
      navigation thanks to Toolbox's existing tool-widget caching.
- [x] **3.4 Journal** — dated, searchable, taggable notes (upgrades
      the Notes module placeholder). `core/journal_manager.py` is a
      `core/`-level shared service (per the "Notes/Journal Engine"
      row), not module-local, so future modules (Project Manager, Lab
      notes, vehicle notes) can reuse it directly. Notes is also the
      first module to register its own Global Search provider (the
      pattern `docs/ADDING_MODULES.md` documents but no module had
      used yet), resolving to `action_type="open_module"` rather than
      a deep link into a specific entry.
- [x] **3.5 Inventory** — final `ToolboxTool` of the v0.3 breakdown.
      `core/inventory_manager.py` (persisted to
      `data/inventory_items.json`) tracks name/quantity/category/
      location/notes; the tool adds quick **+1**/**−1** buttons on top
      of the usual Add/Edit/Delete for the common case of adjusting a
      count without opening the full dialog. v0.3 (Toolbox) is now
      complete.
- [x] **3.6 Real File Manager** — replaces the Files module placeholder.
      Browse/navigate (starts at home, goes anywhere the OS permits),
      create/rename/delete (permanent — no trash/recycle bin, gated
      behind a typed-name confirmation), text/image preview, and a
      live filename filter. Not yet wired into Global Search — a
      filesystem-wide search has real scope questions (how deep to
      recurse, which drives) worth designing deliberately rather than
      bolting on here.

## v0.4 breakdown (complete)

Reference Library engine (Kiwix ZIM integration), same
small-independently-testable-milestone pattern as v0.2/v0.3. Renderer
decision: article HTML is shown in a plain `QTextBrowser` (ships with
PySide6 already, no JS) rather than `QtWebEngine` (full Chromium) — a
deliberate call to keep `requirements.txt` light and stay inside the
Pi 5 resource budget per this doc's design principles, at the cost of
imperfect fidelity on JS-heavy ZIM content. Revisit only if a
must-have content pack turns out to need it.

- [x] **4.1 ZIM engine core service** — `core/reference_library_manager.py`
      (`AppContext.reference_library`) wraps the `libzim` package
      (confirmed prebuilt aarch64 wheels exist, so it's safe for Pi 5).
      Discovers `.zim` files in a configurable library folder
      (`reference_library.root_path` config key, defaults to
      `reference_library/` at the repo root — deliberately a sibling
      of `data/`, not inside it, so `core/backup_manager.py`'s
      full-`data/`-directory backup never tries to sweep multi-gigabyte
      content packs into a config/data backup; per `docs/HARDWARE.md`
      a real deployment points this at the separately-mounted bulk USB
      SSD instead, not the boot microSD). A broken/corrupt `.zim` is
      logged and skipped, never crashes the app — same defensive
      pattern as `ModuleManager`'s broken-module handling. Exposes
      pack discovery, main-page/entry content retrieval (for both
      articles and inline resources like images), and in-pack search.
      No UI yet — that's 4.2.
- [x] **4.2 Reference Library UI** — upgrades the `knowledge` module
      placeholder: a pack list (`modules/knowledge/module.py`) and,
      per pack, a reader screen with an in-pack search box and a
      `modules.knowledge.zim_text_browser.ZimTextBrowser`. That class
      resolves a custom `zim://<pack_id>/<entry_path>` URL scheme
      (`modules/knowledge/zim_url.py`) against
      `ReferenceLibraryManager.get_entry_content()` via
      `QTextBrowser.loadResource()` — relative links/images within a
      page (including `../`-style backreferences) resolve for free via
      `QUrl`'s own RFC 3986 resolution, the same mechanism
      `QTextBrowser.setSource()` already uses internally, so no
      ZIM-namespace-aware path logic was needed here. Back/forward
      history comes from `QTextBrowser`'s own built-in tracking. Also
      fixed a pre-existing bug in `tests/run_module.py` (it never wired
      `AppContext.search`/`.calendar`/etc., so running the Notes or
      Toolbox modules through it already crashed on `on_load()`/
      `get_widget()` before this milestone touched it) — needed to
      actually dev-loop on this module's widget.
- [x] **4.3 Global Search integration** — the Knowledge module
      registers a search provider (per `docs/ADDING_MODULES.md`'s
      pattern) so ZIM content is reachable from Ctrl+K, same
      `action_type="open_module"` pattern as Notes. Deliberately caps
      results (3 hits/pack, 15 total) — `gui/search_dialog.py` renders
      every result from every provider with no cap of its own, and a
      single installed pack can have hundreds of thousands of articles.
- [x] **4.4 Install content pack** — a UI flow to point at a `.zim`
      file and add it to the library, validated the same way
      `core/module_validator.py` gates module installs before
      anything is copied in. Synchronous copy, no worker thread — see
      `docs/testing/4.4_install_content_pack.md` for why that's
      consistent with the rest of the codebase rather than a shortcut.
      **2026-07-13 polish pass, closing two gaps flagged but not acted
      on when 4.2/4.4 first shipped:** (1) install existed with no way
      to uninstall a pack from the UI at all — new
      `ReferenceLibraryManager.delete_pack()` (invalidates the cached
      `Archive`/quiet-period-guard entries before unlinking the file —
      libzim's `Archive` has no explicit `close()`, so dropping the
      last Python reference is the documented cleanup) plus a "Delete"
      button on each pack row in `modules/knowledge/module.py`, reusing
      `gui/delete_confirm_dialog.py`'s typed-name confirmation as-is
      (no trash/recycle bin for a real, possibly multi-gigabyte, file
      delete). (2) the per-pack search box re-queried libzim on every
      keystroke — added a 300ms debounce (`QTimer`, parented to the
      reader page so it lives exactly as long as that cached page does,
      the first debounce anywhere in this codebase). Verified with a
      real headless-Qt smoke test: fast simulated typing produces zero
      search calls until typing pauses, and a full pack install-then-
      delete round trip removes both the pack listing and the stale
      cached reader page, not just the file on disk.

## v0.5 breakdown (planned)

Assistant phase — offline LLM chat + push-to-talk voice interface, same
small-independently-testable-milestone pattern as v0.2–v0.4. This is
**only** the conversational Assistant module; the separate
"Self-Modification / Dev Mode" staged plan above (read-only explain →
propose-not-apply → sandboxed test → scoped autonomy) is deliberately
out of scope except where 5.4 explicitly opens stage 1 of it.

Backend decision: dev/test targets **Ollama's local HTTP API**
(`http://localhost:11434`), not `llama-cpp-python` or an in-process
runtime — this matches Hailo's own `hailo-ollama` runtime that the real
Pi 5 + AI HAT+2 deployment will run per `docs/HARDWARE.md`, so moving
from dev (WSL2, no Hailo hardware) to the real device is a config
change (base URL / model name) rather than a backend rewrite. The
client is built on stdlib `urllib.request`, not the `requests` package
— keeps `requirements.txt` light per this doc's design principles, and
a local single-endpoint JSON API doesn't need more than stdlib gives.
Neither `ollama` itself nor a model pull is assumed to exist in this
dev environment yet — 5.1 must degrade gracefully (logged, non-fatal)
when the backend isn't reachable, same defensive pattern as a
broken/corrupt `.zim` in `core/reference_library_manager.py`, so app
boot never depends on an LLM server being up.

- [x] **5.1 LLM backend core service** — `core/llm_manager.py`
      (`AppContext.llm`) defines a small backend-agnostic interface
      (e.g. `generate(prompt, ...) -> str`) with one concrete
      implementation, an Ollama HTTP client. Config-driven
      (`llm.base_url`, `llm.model`, following the `modules.<id>.*` /
      top-level-service config convention `CLAUDE.md` documents).
      Connection failures and missing models are logged and surfaced
      as a clear "assistant unavailable" state, never a crash or a
      hang at boot. No UI yet — a manual smoke test script or
      `tests/run_module.py`-style check is enough to prove it works
      against a real local Ollama instance.
- [x] **5.2 Assistant Chat UI** — upgrades the `modules/assistant`
      placeholder to a real chat screen (scrollback + input box) wired
      to `AppContext.llm`. A blocking HTTP call on the GUI thread would
      freeze the UI for the duration of every reply, so this is the
      first module to need the scoped worker-thread pattern
      `CLAUDE.md`'s "no async/threading anywhere in core" note
      explicitly carves out an exception for ("introduce a scoped
      worker-thread pattern in the specific module that needs it when
      that need actually arrives") — a `QThread`/`QRunnable` local to
      `modules/assistant`, not a change to `core/event_bus.py` or any
      other core service.
- [x] **5.3 Voice interface (STT/TTS + push-to-talk)** — core service
      for speech-to-text and text-to-speech, plus a push-to-talk
      trigger abstraction: a real GPIO button interrupt in kiosk
      deployment per `docs/HARDWARE.md`, a keybinding/on-screen button
      in dev — same dev/prod split already established for
      `kiosk_mode` fullscreen behavior. STT/TTS engine choice: Vosk +
      Piper (`core/voice_manager.py`) — decided ahead of real
      mic/speaker hardware being in hand, at the user's request, since
      both are offline/CPU-only and known to work on Pi-class hardware;
      verified here with a real Piper->Vosk round trip (no hardware
      needed for that part) and a real "no PortAudio" degrade check,
      with live mic capture/playback itself only smoke-tested for
      graceful degradation, not exercised for real. Exact mic/speaker
      part choice remains open per `docs/HARDWARE.md`'s "Open
      questions" section.
- [x] **5.4 Device-help grounding** — the Assistant answers "what does
      this do / how do I use this device" questions grounded in
      MIA's own docs (`docs/*.md`) and module metadata via
      retrieval, not open-ended chat. This is explicitly **stage 1
      ("Read & explain")** of the Self-Modification / Dev Mode staged
      plan above — read-only, no file writes, and stays that way until
      stage 1 is trusted in practice. Do not let this milestone grow
      into stage 2 (propose-a-patch) scope creep.
      `core/device_help_manager.py` (`AppContext.device_help`) does
      simple keyword-overlap retrieval (not embeddings — deliberately,
      see that module's docstring) over markdown-heading chunks of
      `docs/*.md` plus module metadata, and every Assistant prompt is
      run through `build_grounded_prompt()` before reaching the LLM.
      Found and fixed a real ranking bug during manual verification
      against the actual corpus: naive substring matching let short
      query words false-match inside unrelated words (`"do"` inside
      `"random"`/`"wisdom"`), and even after switching to whole-word
      matching, `docs/ADDING_MODULES.md` (every heading contains the
      word "module") still buried a named module's own description —
      fixed with a name-match bonus when the query names a module
      directly, verified with a real end-to-end query against the
      actual docs/modules and a headless smoke test of the full chat
      flow confirming the LLM receives the grounded prompt while the
      chat log still shows the user's original question.
- [x] **5.5 Assistant tool use / action execution** — the Assistant
      can perform ordinary app actions (open a module, add an alarm, a
      note, an inventory item), not just answer questions, via Ollama's
      structured tool-calling API (`/api/chat` + a `tools` schema).
      This is explicitly **not** the Self-Modification / Dev Mode
      staged plan above — that's specifically about the assistant
      editing MIA's own source code, gated behind a cautious
      multi-stage rollout; actions here are just normal, everyday app
      operations any user could already do by hand through the UI.
      `core/assistant_actions.py`'s `AssistantActionRegistry` is a
      pluggable registry (same shape as `core/calculator_engine.py`),
      with built-ins wired in `core/application.py`
      (`_register_assistant_actions()`, mirroring
      `_register_calculators()`): `open_module`, `add_alarm`,
      `add_note`, `add_inventory_item`. A tool call that needs to
      touch the GUI (`open_module`) goes through a new
      `"assistant.open_module_requested"` event
      (`gui/main_window.py` subscribes and navigates) rather than
      calling into Qt directly from off the GUI thread.
      `core/llm_manager.py` gains `chat_with_tools()`
      (Ollama's `/api/chat`, not `/api/generate`) with a `ToolCall`/
      `ChatReply` shape. Found and fixed a real quality issue during
      manual verification against the live model (llama3.2:3b): when
      tools are available but the query doesn't need one, the model
      sometimes emits a malformed tool-call-looking JSON string as
      plain `content` instead of either answering normally or
      correctly declining to call a tool — `chat_with_tools()`
      detects this shape and retries once without tools to get a
      clean textual answer, verified against the real Ollama server,
      not just a mocked test. Also bumped `llm.timeout_seconds`
      default 30 -> 60 after a real cold-model-load request exceeded
      30s on this CPU-only dev machine. Found and fixed a second real
      issue the same way: the model naturally says a module's
      human-readable name ("Notes") rather than its internal
      snake_case `module_id` ("notes") when asked to open it — a
      strict `ModuleManager.get()` lookup rejected a perfectly clear,
      valid request. Fixed with `ModuleManager.resolve()`, a
      case-insensitive fallback match on `module_id` or
      `display_name`, verified end-to-end through the real
      `MIAApplication`/`MainWindow` wiring (not a hand-copied test
      double) with the live model.

      **Follow-up performance fix (same day):** a real response
      measured at ~25s turned out to be almost entirely Ollama
      re-loading the model from disk, not inference — Ollama unloads a
      model after 5 minutes idle by default (`OLLAMA_KEEP_ALIVE`), so
      any real conversation with a pause longer than that pays this
      cold-load cost on the next message, which reads as "the
      Assistant is really slow" even though a warm request completes
      in under 2s. Fixed by sending `keep_alive` on every request
      (`core/llm_manager.py`, config key `llm.keep_alive`, default
      `-1` = never unload) rather than relying on server-side env
      config, so the fix travels with the app regardless of Ollama
      deployment. Hit a second real issue getting this right: Ollama's
      API rejects `keep_alive` as the *string* `"-1"` with HTTP 400
      ("missing unit in duration") — it must be a bare JSON integer for
      a seconds value, while a duration string like `"30m"` is only
      valid as an actual string. `OllamaBackend` normalizes this once
      (numeric-looking config values become a real int). Verified by
      force-unloading the model against the real server and confirming
      the next request no longer cold-loads.
- [x] **5.6 Assistant + Reference Library grounding** — the Assistant's
      grounding (5.4) previously only ever searched `docs/*.md`
      (MIA's own self-documentation), completely separate from the
      actual Reference Library content (Wikipedia/iFixit/Wikibooks/
      Appropedia packs) the Knowledge module manages — asked at the
      user's request, after using the app in practice: "I want to be
      able to ask the assistant about anything that may be in the
      knowledge base and it be able to access it." `core/reference
      _library_manager.py` gains `search_all_packs()` (fans a query out
      across every installed pack's own full-text search, using
      libzim's relevance ranking as-is rather than re-scoring, and
      reduces each hit to a short plain-text snippet via a small
      stdlib-only `HTMLParser` subclass — deliberately not a full HTML
      renderer, that's `modules/knowledge/zim_text_browser.py`'s job).
      `core/device_help_manager.py` gains `register_reference_library()`
      (same registration-callback shape as `register_module_lister()`)
      and `build_grounded_prompt()` now blends reference-library
      snippets in alongside `docs/*.md`/module chunks.

      This milestone took much more real-model iteration than any
      previous one — five distinct, genuine bugs found only by testing
      against the real installed packs and the live model, not mocks:
      1. **Corrupt data**: `wikibooks_en_all_nopic_2026-04.zim` failed
         to open (libzim: "Zim file(s) is of bad size or corrupted") —
         re-downloaded from `download.kiwix.org` (truncated at roughly
         half its real 3.5GB size) and verified openable before
         replacing the broken copy.
      2. **Cross-pack crowding**: `search_all_packs()` originally
         stopped as soon as it hit its total limit, so an alphabetically
         early pack's several weak hits could crowd out a later pack's
         single much-more-relevant hit ("hypothermia symptoms" got
         Appropedia's general cold-weather article, never even reaching
         WikiMed's actual "Hypothermia" article). Fixed: one hit per
         pack, every pack tried before capping the total.
      3. **Un-stripped queries confuse libzim's own ranking**: passing
         the raw question ("What are the symptoms of hypothermia?")
         instead of stopword-stripped keywords ("symptoms hypothermia")
         made libzim's full-text search rank an unrelated article
         first ("Pulseless electrical activity") — filler words diluted
         its relevance scoring. Fixed by reusing `_query_words()`.
      4. **Dilution from low-relevance results**: even with (2)/(3)
         fixed, a query with a strong, confident match (e.g. a module
         named directly, scoring >= `_MODULE_NAME_MATCH_BONUS`) got
         "I don't know" once several more tangentially-matching
         chunks/snippets were piled on alongside the one correct
         chunk — despite the model's own reasoning quoting the correct
         text verbatim. Fixed: a confident match now includes only
         that one chunk and skips Reference Library entirely, rather
         than always filling out to `limit`.
      5. **Sampling variance**: the exact same prompt, byte-for-byte,
         gave a correct answer on one live call and "I don't know" on
         another — Ollama's default temperature isn't 0. Fixed:
         `core/llm_manager.py` now sends `options.temperature: 0` by
         default (config `llm.temperature`) for deterministic,
         repeatable grounding/tool-calling answers, verified directly
         against the server that this stabilized the flip-flopping.
      Also found the module-metadata chunk template itself mattered:
      changed from a bare `"## {name}"` heading to explicitly saying
      `"The {name} module: {description}"` in the body text — the
      small model reliably needed the literal word "module" tied to
      the name in the passage, not just implied by a heading/label.

      Verified end-to-end with real questions whose answers only exist
      in Reference Library content (not `docs/*.md`), a real
      device-help question, and a real out-of-scope question (correctly
      declined, no hallucination) — all against the live Ollama server,
      not mocks.

      **Follow-up fix (same week): tools and grounding were fighting
      each other.** Real usage surfaced: "What can you tell me about
      Honda Civics?" made the model hallucinate a nonexistent module_id
      ("Reference Library: Wikibooks") and call `open_module` instead of
      answering "I don't know" — because every message got ALL action
      tools attached unconditionally, even pure information questions
      with no relevant grounded match. `modules/assistant/module.py`
      gains `looks_like_action_request()`, a simple keyword classifier
      (phrases tied to the registered actions — "open", "set an alarm",
      "add a note", etc., same simplicity level as
      `core/device_help_manager.py`'s own retrieval scoring) that
      `_on_send()` uses to decide which of two mutually-exclusive paths
      to take: information questions get the grounded prompt (5.4/5.6)
      and no tools; action requests get the user's raw prompt and the
      action tools, skipping grounding entirely. That second half of the
      split was itself found by testing the fix: with tools correctly
      gated, "Set an alarm called Wake Up for 07:00" *still* failed to
      call `add_alarm` — grounding was pulling in irrelevant doc chunks
      (`docs/ADDING_MODULES.md`, matched on the word "add") that
      convinced the model the conversation was about MIA's own
      developer docs rather than the user's request. Fixed by skipping
      `build_grounded_prompt()` for action requests too. Verified
      against the live model: the Honda Civics question now correctly
      declines with no tool call, and alarm/note/open-module action
      requests all correctly call their tool, using the exact
      `_on_send()` branching logic (not a hand-simplified stand-in).
- [x] **5.7 Assistant action-registry expansion: read/query tools** —
      at the user's explicit request ("the assistant needs to be
      supercharged... more capable than the user in using the
      program"), the Assistant gains six new read-only tools, one per
      existing domain: `list_alarms`, `list_notes` (search or list all
      journal entries), `list_inventory` (search or list all items with
      quantities), `list_waypoints` (search or list all saved
      locations), `waypoint_distance` (distance + bearing between two
      named waypoints), and `get_system_health` (live CPU/RAM/disk/
      temperature/network snapshot). Deliberately read-only and lower
      risk than write actions — this is the highest-value, lowest-risk
      slice of "more capable than the user," since it directly answers
      questions the user would otherwise have to open a module to
      check, without adding new ways to mutate state. Total registered
      tools go from 5 to 11.

      `get_system_health` needed `modules/diagnostics/module.py`'s
      `read_system_health()`/`format_system_health()`/
      `SystemHealthSnapshot` — but `core/application.py` (where
      assistant actions are registered) can never import from
      `modules/` (this project's layering rule, see CLAUDE.md). Moved
      that reader to a new `core/system_health.py` shared service
      (Diagnostics' UI now imports from there too) rather than
      duplicating it or bending the layering rule — same "promote to
      core/ once something else actually needs it" reasoning already
      behind Journal/Alarm/Inventory/Waypoint living in core/.
- [x] **5.8 Assistant tool-gating scaling fix (registry-driven
      keywords)** — done *before* 5.7's new tools were wired up, since
      it's the safety net they depend on. The gating heuristic from the
      5.6 follow-up fix (`looks_like_action_request()`) used a single
      hand-maintained keyword tuple in `modules/assistant/module.py` —
      fine at 5 actions, but a real liability once the registry was
      about to grow past that (a developer adding action #12 has no
      reason to remember a keyword list three files away). Fixed by
      moving gating phrases onto each action's own registration:
      `AssistantAction` gains a `trigger_phrases` field
      (`core/assistant_actions.py`), `AssistantActionRegistry.
      gating_keywords()` flattens every registered action's phrases,
      and `_on_send()` passes that live set to
      `looks_like_action_request()` instead of a static import. The old
      hand-written tuple stays only as `looks_like_action_request()`'s
      default argument, for standalone testing of the classifier
      itself — production code always passes the registry's real
      keywords.
- [x] **5.9 Real-model verification at the new tool count** — with 11
      tools now on the table (more than double milestone 5.5/5.6's 5),
      re-ran the exact same live-model regression check this project
      has used all along rather than trusting the design on paper: the
      original Honda Civics case still declines correctly with zero
      tools offered; `add_alarm`/`add_note`/`open_module` still fire
      correctly; and all six new read tools (`list_alarms`,
      `list_notes`, `list_inventory`, `list_waypoints`,
      `waypoint_distance`, `get_system_health`) were exercised against
      real seeded data and called the correct tool with correct
      arguments. No new hallucination or tool-confusion observed at
      this tool count on llama3.2:3b — but this doc's standing
      guidance (5.6's writeup) still applies going forward: re-verify
      against the live model at each future batch of new actions,
      don't assume scaling stays safe by design alone.
- [x] **5.10 Assistant action-registry expansion: write/mutate tools**
      — the second half of "supercharge the Assistant," deliberately
      built after 5.7-5.9's read tools and gating rework rather than
      alongside them, since write actions carry more downside if
      mis-called. Five new actions: `delete_alarm`, `delete_note`,
      `delete_inventory_item`, `adjust_inventory_quantity` (positive or
      negative delta, e.g. "I used 5 M3 bolts" -> delta -5, clamped at
      zero by `InventoryManager.adjust_quantity()`), `delete_waypoint`.
      Total registered tools: 11 -> 16. Every one of these handlers
      resolves its target by an exact, case-insensitive name/label
      match and **fails closed** with a clear "I don't have a/an X
      called '...'" message when nothing matches, rather than guessing
      or fuzzy-matching — this bounds the damage of any future gating
      false positive by construction: worst case is a no-op with a
      clear message, never a wrong deletion.

      Live-model verification found two more real gating gaps, in the
      same vein as 5.9's, plus a subtler one this time:
      1. **Name-inserted-before-the-noun phrasing**: "Delete my Wake Up
         alarm" doesn't match any combo phrase like "delete an alarm"
         (the label sits between "my" and "alarm"). Fixed for
         `delete_alarm` with a bare, word-boundary-safe `"alarm "`
         trigger (trailing space so it doesn't match inside
         "alarming") — deliberately *not* done the same way for
         `delete_note`, since bare "note " collides with extremely
         common unrelated phrases ("please note that...", "of note");
         `delete_note` only gets combo phrases ("delete the note",
         "delete my note", ...), so a "delete my [title] note"
         construction remains a known, accepted gap rather than a
         fixed one — the risk/reward of a bare trigger isn't the same
         for every word.
      2. **"Got more" doesn't survive an inserted quantity either**: "I
         got 10 more M3 bolts" doesn't match the `"got more"` trigger
         phrase (same shape as gap #1) — left as a known, accepted gap
         rather than chasing every possible increase-quantity phrasing;
         the safe failure mode (the model just chats, no tool called)
         made this low-priority relative to the decrease/delete paths.
      3. **"I used" collides with "used to"**: `adjust_inventory_quantity`'s
         working trigger for "I used 5 M3 bolts" also fires on "I used
         to live in Ohio" — verified this is a bounded, not dangerous,
         false positive: the model called a harmless read-only
         `recall_recent_activity` rather than anything destructive, and
         every delete/adjust handler's fail-closed exact-match lookup
         (above) means even a wrongly-triggered `adjust_inventory_quantity`
         call couldn't touch real data without an exact existing item
         name. Accepted as a documented trade-off (see
         `tests/test_assistant_action_gating.py`) rather than adding
         regex/numeric-lookahead complexity to the keyword matcher for
         one edge case.
      All three findings and the fixes/trade-offs made are pinned as
      regression tests, not just prose — the two write-up patterns this
      project has settled on for gating gaps: fix + pin when the fix is
      clean and low-risk (gap #1's alarm phrasing), document + pin the
      *current* behavior as intentional when the fix would introduce
      new complexity or risk disproportionate to the gap (gaps #2 and
      #3).
- [x] **5.11 Golden-set live-model regression script** — every round of
      tool-gating verification since 5.6 (the follow-up fix, 5.7-5.9,
      5.10) was a throwaway scratch script written fresh each time,
      re-deriving the same setup and occasionally re-discovering gaps
      in categories already seen. `tests/live_model_check.py` is the
      same idea kept around and extended instead of thrown away: 19
      golden (prompt, expected tool-or-none) cases covering every
      registered action plus the known false-positive/trade-off cases
      from 5.9/5.10, run against a real Ollama server, with a PASS/FAIL
      summary and non-zero exit on failure. Deliberately named without
      a `test_` prefix so pytest never auto-collects it — it needs a
      live model, unlike the rest of the suite.

      `modules/assistant/module.py`'s `_on_send()` had the gating/
      grounding decision logic extracted into a standalone
      `build_chat_request(context, prompt)` function so this script
      exercises the *exact* production decision path, not a hand-copied
      reimplementation — every prior scratch script was, in effect, its
      own slightly-drifting copy of that logic.

      **A real mistake found while building this:** every prior scratch
      script (including 5.7-5.10's) constructed real
      Alarm/Journal/Inventory/Waypoint managers *without* isolating
      their data directories, so all of that session's test fixtures
      ("Wake Up" alarm, duplicate "Groceries" notes, "M3 bolts"
      inventory items, "Home"/"Cabin" waypoints) were written straight
      into this dev machine's real `data/*.json` files across multiple
      runs. `tests/live_model_check.py` redirects every manager's data
      directory into a throwaway `tempfile.mkdtemp()` location before
      constructing anything, and never executes a tool call (only
      inspects `reply.tool_calls`, same convention every scratch script
      already used) — so it can be re-run freely without touching real
      data. The already-polluted files were left for the user to review
      rather than auto-deleted (data/*.json is gitignored personal
      data, and telling apart a test fixture from a coincidentally
      identical real entry isn't a call to make unilaterally). **Any
      future one-off verification script must isolate data directories
      the same way `tests/test_assistant_action_handlers.py` and
      `tests/live_model_check.py` do — never construct a real manager
      against the real `data/` path.**
- [x] **5.12 Assistant action-registry expansion: Expedition Mode +
      Device Profile/Theme** — closes the biggest post-5.11 gap: every
      module built since (Expedition Mode's Expeditions/Trips/gear/
      trip journal, and Device Profile/Theme) was completely invisible
      to the Assistant. 9 new tools registered in
      `core/application.py::_register_assistant_actions()`, same exact
      shape as every prior batch (co-located `trigger_phrases`,
      `@staticmethod` handler, case-insensitive by-name resolution,
      fail-closed "I don't have a/an X called '...'" on no match, never
      fuzzy-matched): `add_waypoint` (a real pre-existing gap —
      waypoints could be listed/distanced/deleted via the Assistant but
      never *added*), `add_expedition`/`list_expeditions`,
      `add_trip`/`list_trips` (resolves the parent Expedition by name,
      fails closed if it doesn't exist), `add_gear_item`,
      `add_trip_log_entry`, `get_device_profile`, `set_theme` (reuses
      the exact same `context.config.set("gui.theme", ...)` +
      `"theme.changed"` event-bus publish as
      `modules/settings/module.py`'s Theme dropdown, not reimplemented).
      Registry grew from 16 to 25 tools.

      Two collision risks were identified *before* writing any code,
      not found after the fact: (1) `set_theme` could be hallucinated
      as `open_module` since `open_module` already gates on bare
      `"switch to "` — mitigated by giving `set_theme` entirely
      non-overlapping trigger phrases, and pinned with an explicit
      golden-set case ("Switch to the Anime Monochrome theme" must call
      `set_theme`, not `open_module` with a hallucinated `module_id`).
      (2) `add_trip_log_entry` and the pre-existing `add_note` both
      ultimately write to the same `JournalManager` — golden-set cases
      confirm the model picks the trip-specific tool for trip-flavored
      phrasing and still correctly falls back to `add_note` for a
      plain "Add a note that says buy milk".

      **Unlike every previous batch (5.7-5.10), which each needed
      multiple rounds of live-model fixes** (two real gating gaps in
      5.7, a regression introduced by 5.7's own fix caught in 5.8,
      etc.) — designing trigger phrases and the two collision
      mitigations *before* running against the real model this time
      produced a clean **32/32 pass on the first run** of the expanded
      `tests/live_model_check.py` golden set, confirmed stable on a
      second independent run (not just a lucky sampling draw — this
      project's own 5.9 finding that `temperature=0` doesn't fully
      eliminate llama.cpp's sampling variance means one green run alone
      isn't sufficient evidence). Extended
      `tests/test_assistant_action_handlers.py` (fixture gained
      `ctx.expeditions`/`ctx.trips`, isolated `trips.photo_root_path`
      too) and `tests/test_assistant_action_gating.py` with full
      coverage for all 9 new tools.

      **Deliberately not attempted this pass** — Field Kit (device
      detection, script library, Expedition data sync), Calendar,
      Power, Components, and Data Logger remain unconnected to the
      Assistant. Flagged as a natural follow-up batch, not done here,
      to keep this batch's live-model verification surface reviewable
      rather than growing the registry by 20+ tools at once.

      **Also verified through the real running Assistant UI end to
      end** (not just `build_chat_request()` in isolation, which
      `tests/live_model_check.py` checks — that never calls `execute()`
      or touches Qt at all): a real `AssistantModule` widget, real
      `ChatWorker` thread, two real messages sent through `_on_send()`
      exactly as a user would type them. First caught a real prompt-
      design mistake in the smoke test itself — "log that I reached
      camp" with no trip named anywhere in the message correctly made
      `add_trip_log_entry`'s fail-closed lookup say "I don't have a
      trip called 'camp'" instead of guessing, which is the fail-closed
      design working exactly as intended, not a bug — then, with the
      trip actually named in the prompt, confirmed a full round trip:
      the gear item and the trip-linked, conditions-populated journal
      entry both landed correctly in the real managers.
- [x] **5.13 Assistant action-registry expansion: Calendar, Power,
      Components, Field Kit (read actions)** — the next follow-up batch
      flagged at the end of 5.12, closing most of the remaining
      unconnected modules: registry grows 25 -> 34.
      `add_calendar_event`/`list_calendar_events`/`delete_calendar_event`,
      `get_power_status` (read-only), `add_component`/`list_components`/
      `delete_component` (Workshop & Electronics), `list_connected_devices`
      and `list_scripts` (Field Kit, both read-only). Same exact handler
      shape as every prior batch. `delete_calendar_event` reuses the
      "alarm "-style bare trailing-space trigger trick (`"event "`) for
      real name-between-verb-and-noun phrasing ("delete my Doctor
      Appointment event"), pinned against the "eventful" substring
      false-positive the same way `"alarm "` already guards against
      "alarming."

      **Deliberately excluded: `run_script`.** Executing one of the
      user's saved Field Kit scripts via voice/text is a meaningfully
      different capability than every other action registered so far —
      real command/code execution, not CRUD on MIA's own data — and
      deserves its own explicit decision rather than being bundled
      quietly into a read-action batch. `list_scripts` (read-only) shipped;
      actually running one did not.

      Extended `tests/live_model_check.py`'s `_build_context()` with a
      real `DeviceFramework`/`PowerManager` (both read-only wrappers
      over `lsblk`/`psutil` with no JSON file of their own, so — unlike
      every other manager in that script — neither needs data-dir
      isolation). Passed **42/42 on the first run**, confirmed stable on
      a second independent run (one previously-passing "known accepted
      trade-off" case called a different, still-`"safe"`, non-destructive
      tool between the two runs — expected `temperature=0` sampling
      noise per 5.9's finding, not a regression, since that case's
      golden-set expectation is "no destructive call," not an exact
      tool match). Also smoke-tested through the real `AssistantModule`
      UI (add a calendar event, add a component) — both landed
      correctly in the real managers.

      **Still deliberately unconnected**: Expedition data sync
      (export/import — awkward for conversational use, needs a real
      physical device path), Data Logger (niche/config-heavy, not a
      natural conversational fit). Not every module needs an Assistant
      hook; these were considered and skipped, not overlooked.
- [x] **5.14 Assistant action-registry expansion: Profiles (read-only)**
      — registry grows 34 -> 35, adding only `list_profiles`.
      **Deliberately no `switch_profile`**: `gui/profile_select.py`
      requires `verify_password()` to succeed *before*
      `set_active_profile()` for any password-protected profile — an
      Assistant action calling `set_active_profile()` directly would
      bypass that check entirely (a real security hole), and the
      alternative (accepting a password argument from the LLM) would
      mean a spoken/typed password sits in plaintext chat history,
      worse than a masked password field. Excluded outright, same
      "flag it, don't silently omit it" treatment as 5.13's `run_script`
      exclusion — this one for security reasons rather than execution-
      risk reasons.

      **Found a real naming collision via live-model testing**: `"profile"`
      is overloaded in this app (user Profiles vs. the Core/Home
      `device_profile` edition setting). Since gating is all-or-nothing
      (once *any* trigger phrase matches, *all* registered tools attach,
      not just the one whose phrase matched), the model had to
      semantically distinguish `list_profiles` from the pre-existing
      `get_device_profile` — and initially picked the wrong one for
      "What profiles are set up on this device?". Fixed by sharpening
      both tools' descriptions to explicitly cross-reference and rule
      each other out ("this is about user accounts, NOT the device's
      Core/Home edition — use get_device_profile for that", and vice
      versa) rather than adjusting trigger phrases, since the collision
      was semantic (tool selection among an attached set), not a gating
      problem. A second collision-risk golden-set case was itself
      initially miswritten (didn't actually contain any registered
      trigger phrase, so nothing gated open at all — a test-authoring
      mistake, not a model failure); corrected, then passed 44/44 on
      two consecutive runs.

      **Found and fixed a real data-pollution bug while investigating**,
      unrelated to the collision above: `tests/test_assistant_action_handlers.py`'s
      `context` fixture never isolated `core.config_manager._CONFIG_FILE`
      the way every manager's own `_DATA_DIR`/`_XXX_FILE` already was —
      harmless until 5.12 added `_action_set_theme` (the first handler
      in this fixture to call a real `context.config.save()`), at which
      point that one test's `.save()` call landed in the *actual*
      `config/config.json`, not a throwaway file. Caught by noticing an
      actual pytest tmp-path string sitting in that real file's
      `trips.photo_root_path` key. Fixed at the root (isolated
      `_CONFIG_FILE` in the fixture, so any current or future handler
      test is safe by construction, not by which handler happens to get
      exercised) and the same latent gap was found and fixed in
      `tests/live_model_check.py` *before* it could bite there too
      (adding `ProfileManager` there meant `create_profile()`'s own
      internal `.save()` call would have hit the same real file).
      `config/config.json` is gitignored/never committed, so the
      already-leaked test artifact was cleaned up locally, not via git.
- [x] **5.15 Assistant action-registry expansion: Security tab tools
      (hash identifier, password strength, subnet calculator, port
      scanner)** — registry grows 35 -> 39, connecting the 11.5 Security
      Toolkit's read-only tools: `identify_hash`, `check_password_strength`,
      `calculate_subnet`, and `scan_ports` (capped to 3 fast common ports —
      22/80/443 — with a short 0.3s timeout each, so the worst case adds
      under a second to a synchronous Assistant-thread call; a full
      `COMMON_PORTS` sweep stays a Field Kit Security-tab-only,
      QThread-backed operation). **Caveat carried forward, not silently
      dropped**: `check_password_strength` puts whatever password the
      user types/speaks into the Assistant's plaintext chat history —
      same category of trade-off as 5.14's `switch_profile` exclusion,
      but accepted here (unlike that exclusion) because this tool never
      *authenticates* anything, it only scores a string's strength.

      **Found a real, reproducible tool-count regression via live-model
      testing — not sampling noise.** After connecting these 4 tools,
      `tests/live_model_check.py` settled at a stable 48/49, with the
      one failure always the same pre-existing case ("How many M3 bolts
      do I have?" -> expected `list_inventory`, got no tool call at all)
      on every run. Bisected by calling `LLMManager`'s backend directly
      with hand-trimmed tool subsets: at the pre-5.15 tool count (35)
      the model calls `list_inventory` correctly and reliably; somewhere
      past that, it instead emits `{"name": "get_inventory_quantity",
      ...}` — a hallucinated, never-registered tool name — as plain
      text content, which `llm_manager.py`'s
      `_looks_like_malformed_tool_call()` correctly detects and retries
      once *without* tools, landing on an unrelated prose answer.
      Isolating each new tool one at a time pinned `calculate_subnet`'s
      mere presence as sufficient to reproduce the failure 5/5 runs by
      itself; renaming just that one tool (identical description/
      params) also fixed it in isolation, but stopped working again once
      the other 3 new tools were present too — ruling out both "one bad
      tool name" and "a hard tool-count ceiling" as the full story, and
      pointing instead at cross-schema interference in a 3B model's
      attention over a growing tool list, consistent with this
      project's running finding that registry growth needs live-model
      re-verification every time, not just unit/gating tests. Fixed by
      spelling out the "how many X do I have" phrasing directly in
      `list_inventory`'s own tool description (rather than renaming or
      removing anything) — confirmed to hold at the full 39-tool count,
      5/5 direct-backend runs and 49/49 on two independent full
      `live_model_check.py` runs afterward.

      Smoke-tested through the real `AssistantModule` UI under headless
      Qt (widget builds cleanly with all 39 actions registered,
      including the 4 new Security tools present in the Ollama tool
      schema sent to the model).

## v0.6 breakdown (planned)

Character/companion system — event bus driven, reacts to whatever
module is active. Same small-independently-testable-milestone pattern
as v0.2–v0.5. This phase is UI/personality only — no animation assets,
sprite work, or a dedicated rendering engine; `gui/character_panel.py`'s
own "likely future implementation notes" already scoped a
QMovie/QOpenGL upgrade as a later, separate concern, not part of this
phase.

- [x] **6.1 Module-activity events** — `gui/main_window.py`'s
      `open_module()`/`show_main_menu()`/`go_back()` publish
      `"module.opened"` (with `module_id`) and `"menu.shown"` on
      `context.events`, the same event-bus mechanism every other
      cross-component reaction in this app already uses (see
      `core/event_bus.py`). Foundational plumbing only — nothing
      subscribes yet; this milestone is done when a test's own
      subscriber observes the right event firing for every navigation
      action (open a module, go back, go home).
- [x] **6.2 Reactive Character Panel** — `gui/character_panel.py`
      stops being a static "(coming soon)" placeholder: it accepts
      `context` (already anticipated in its own docstring), subscribes
      to `"module.opened"`/`"menu.shown"` (6.1) and the existing
      `"notification.created"` event, and updates its displayed
      text/icon to react to whichever module is currently active or a
      just-fired notification. A small per-module flavor-line mapping
      lives in this file (not spread across every module), falling
      back to a generic "watching over `<display_name>`" line for any
      module without a specific one, so adding a new module never
      requires touching this file. Still no animation/sprite assets —
      text + emoji only, matching this phase's stated scope.
- [x] **6.3 Idle ambient behavior** — when no relevant event has fired
      recently, the panel rotates through a small set of idle lines on
      a timer (same `QTimer`-in-the-owning-widget pattern as
      `core/application.py`'s alarm-check timer), so the panel doesn't
      look frozen during long stretches on one screen. Purely
      cosmetic; skip entirely (don't even start the timer) if
      `gui.show_character_panel` is off.

## v0.7 breakdown (planned)

Diagnostics + Power monitoring. Same small-independently-testable-
milestone pattern as v0.2–v0.6.

- [x] **7.1 System Health panel (Diagnostics)** —
      `modules/diagnostics/module.py` gains a live CPU/RAM/disk/network/
      temperature panel alongside its existing log viewer, via `psutil`
      (cross-platform, well-established — "don't reinvent the wheel").
      Stats-reading is pure functions in this module (same shape as its
      existing `tail_lines()`/`filter_lines()`), not a new `core/`
      service — this data is Diagnostics' own exclusive concern, not
      shared across sections the way Calculator Engine/Reference
      Library are, and it's stateless point-in-time reads with no
      persistence, so a core manager would be pure ceremony. A
      widget-owned `QTimer` refreshes the panel periodically while it's
      on screen — same timer-owned-by-the-widget pattern as
      `gui/character_panel.py`'s idle timer. A sensor that isn't
      exposed on a given system (e.g. no thermal zone, true in this dev
      sandbox/WSL2) degrades to a clear "not available on this system"
      state, never a crash.
- [x] **7.2 Power monitoring core service + module** —
      `core/power_manager.py` (`AppContext.power`) adds a
      backend-agnostic interface (same shape as
      `core/llm_manager.py`'s `LLMBackend` / `core/voice_manager.py`'s
      `STTBackend`/`TTSBackend`), with one concrete backend using
      `psutil`'s cross-platform battery reporting (percent/plugged/
      time-remaining) — the generic software-level backend available
      today. The real UPS HAT's voltage/current telemetry
      (`docs/HARDWARE.md`'s still-open "Battery/UPS HAT choice"
      question) needs a documented I2C interface not yet chosen — a
      second, hardware-specific backend is future work once that part
      is picked, same "engine decided now, exact part later" split as
      `core/voice_manager.py`'s STT/TTS engine choice. Degrades to a
      clear "no battery/UPS detected" state when `psutil` reports none
      (the expected case on a bare Pi 5 with no UPS HAT installed). A
      new `modules/power/module.py` (top-level module section 9 in this
      doc) surfaces current status; `MIAApplication` gains a periodic
      low-battery check (same `QTimer`-in-`core/application.py` +
      `check_due()`-style pattern as `AlarmManager`) that raises a real
      notification via the existing `NotificationManager` when battery
      drops below a threshold while unplugged — testable with a fixed
      reading, no real hardware or waiting required, same reasoning as
      `AlarmManager.check_due()` taking `now` as a parameter instead of
      calling `datetime.now()` itself.

## v0.8 breakdown (planned)

Workshop & Electronics + The Lab (shared Data Logger). Same
small-independently-testable-milestone pattern as v0.2–v0.7.

- [x] **8.1 Data Logger core service** — `core/data_logger_manager.py`
      (`AppContext.data_logger`) adds timestamped-reading storage keyed
      by a named series (e.g. "multimeter_voltage", "soil_moisture") —
      same persisted-JSON-manager pattern as `core/inventory_manager.py`
      (`data/data_logger_readings.json`, a dataclass with
      to_dict/from_dict). `add_reading()`/`readings_for()`/
      `list_series()`/`delete_reading()`. This is the shared service
      the "Shared core services" table calls out (used by Multimeter
      logging, soil moisture, power usage, Lab experiments/calibration,
      sensor testing, vehicle diagnostics) — no hardware-specific
      producer exists yet; any future real-sensor integration just
      calls `add_reading()` like a manual entry would.
- [x] **8.2 The Lab module** — `modules/lab/module.py`, the UI home of
      the Data Logger (top-level module section 14 in this doc): pick
      or create a series, a manual reading-entry form (value/unit/
      note), a line chart of that series over time via `QtCharts`
      (bundled with PySide6 already — no new dependency), and the raw
      reading list below it. Manual entry only for now — no real
      sensor/multimeter hardware exists to auto-log from yet, same
      "software now, hardware producer later" shape as other phases,
      except there's no backend to swap here: a future real-sensor
      integration is just another caller of `add_reading()`.
- [x] **8.3 Workshop & Electronics: Component DB** —
      `core/component_manager.py` (`AppContext.components`) +
      `modules/workshop/module.py` (top-level module section 5): a
      dedicated electronics-parts inventory (name, category, value,
      package, quantity, location, notes) — deliberately a separate
      manager/dataset from `core/inventory_manager.py`'s general
      household Inventory tool (mixing "kitchen supplies" and "resistor
      stock" into one list serves neither well), same
      list+add/edit/delete CRUD shape as Notes/Inventory. This is the
      one slice of Workshop & Electronics's broad scope (component DB,
      MCU flashing, PCB viewer, soldering notes, 3D printer/CNC/laser,
      STL/CAD library) buildable with zero real hardware/files right
      now; the rest waits for that hardware/tooling to exist.

## v0.9 breakdown (planned)

Activity/Memory Log (shared service) + Memories AI-query — the first
v1.0+-bucket slice buildable with zero real hardware. Per this doc's
own "Top-level module sections" note, Memories is explicitly **not** a
menu section — "Character, Memories, and Global Search are system-wide
/ ambient" — so this integrates into the Assistant's tool-use (5.5)
rather than getting its own module page.

- [x] **9.1 Activity Log core service** — `core/activity_log_manager.py`
      (`AppContext.activity_log`) subscribes to a curated subset of
      already-published events (`module.opened`, `notification.created`,
      `profile.switched` — not every event on the bus, since
      `menu.shown`/`modules.rescanned`/etc. are noise for a "what did I
      do" memory feature, not signal), building a human-readable
      summary per event and persisting to `data/activity_log.json`
      (same pattern as `core/inventory_manager.py`). Capped at a bounded
      number of most-recent entries (`_MAX_ENTRIES` = 5000) so a
      long-running kiosk device doesn't grow this file unbounded — same
      full-file-rewrite-per-mutation cost as every other persisted-JSON
      manager here, accepted for the same reason (real usage logs at
      most a few dozen events/day; reaching cap size takes months, not
      something a tight loop would produce outside a synthetic stress
      test — which is exactly how the cost was found, via this
      milestone's own test suite before it was rescoped to a smaller
      cap for the test).
- [x] **9.2 Assistant "recall activity" action** — a new
      `core/assistant_actions.py` built-in, `recall_recent_activity`,
      wired in `core/application.py`'s `_register_assistant_actions()`
      alongside the others: returns the most recent matching activity
      log entries as a plain timestamped list, shown directly as the
      tool-call confirmation (no second LLM round-trip to phrase a
      summary — simpler and consistent with 5.5's "no second round-trip"
      design, and a short recent-activity list reads fine as-is; the
      breakdown originally planned an LLM-summarized answer here, but
      that would need the tool-result-feeds-back-into-a-second-chat-call
      pattern 5.5 deliberately avoided, so this was rescoped to match
      what's actually simple to keep correct). Verified end-to-end
      against the live model: simulated real `module.opened` events,
      then asked "what have I been doing recently" and confirmed the
      Assistant's reply reflected the actual logged activity, not a
      hallucinated answer.

## v0.10 breakdown (planned)

Navigation: Waypoints + Sun/Moon calculator — the second
v1.0+-bucket slice buildable with zero real hardware (no GPS chip
needed for either piece; "offline maps, trails, elevation" wait for
real GPS/mapping hardware/data this project doesn't have yet). Media/
Music was considered first but was blocked at the time: `PySide6.QtMultimedia`
failed to import in this dev sandbox at all (missing `libpulse.so.0`, a
system package, same "no sudo" wall as `sounddevice`/PortAudio in
milestone 5.3) — confirmed blocked, not just deferred, at the time, so
nothing in that section could be verified here then. **2026-09-09: no
longer true** — the sandbox now has `libpulse0`/`libportaudio2`
installed; see the Music module built as v0.20.

- [x] **10.1 Waypoints core service** — `core/waypoint_manager.py`
      (`AppContext.waypoints`): named locations (name, latitude,
      longitude, notes), same persisted-JSON-manager pattern as
      `core/inventory_manager.py`. `distance_and_bearing()` (haversine
      formula, pure math) between two waypoints — genuinely useful even
      without real GPS hardware (e.g. entering known coordinates from
      a paper map or another GPS device by hand).
- [x] **10.2 Navigation module** — `modules/navigation/module.py`:
      waypoint list UI (add/edit/delete, same CRUD shape as
      Notes/Inventory/Components) plus a Sun/Moon panel (sunrise/
      sunset + moon phase for a given lat/lon, defaulting to a selected
      waypoint) via the `astral` package (pure Python, no network
      calls, no heavy dependency — "don't reinvent the wheel" per this
      doc's design principles). Only needs latitude/longitude, not a
      separate timezone configuration — `astral`'s `Observer` computes
      in UTC and `datetime.astimezone()` converts to the system's local
      time automatically, verified directly against real coordinates.

## v0.11 breakdown (planned)

**Field Kit** — requested directly by the user to turn MIA into "the
most useful offline engineering and field programming tool": detect and
identify devices physically plugged into the Pi, act on them (browse
files, flash an OS + auto-install MIA, flash MCU firmware), plus a
useful-scripts library and a security/network toolkit. This is the
third v1.0+-bucket slice buildable with zero hardware this project
doesn't already have (just a spare USB drive/SD card for real-world
verification) — same "software-buildable now" reasoning as v0.9/v0.10.
Scope decisions made with the user before writing this breakdown:
device detection starts with physically-attached USB/serial devices
only (wifi/Bluetooth discovery is an explicit planned extension of the
same Connected Device Framework, not a separate mechanism, added when
that transport is actually built rather than speculatively now); the
security/network toolkit is scoped to both recon *and* active tooling
(hash cracking, packet crafting, exploit-framework launching), which
this document frames throughout as testing devices/networks the user
owns or is explicitly authorized to test — same standard any real
pentesting toolkit assumes of its operator.

- [x] **11.1 Connected Device Framework (core service)** —
      `core/device_framework.py` (`AppContext.devices`): `list_block_devices()`
      shells out to `lsblk -J` for storage devices (USB drives, SD
      cards, other Pis in USB mass-storage mode) and `list_serial_devices()`
      uses `pyserial`'s `serial.tools.list_ports.comports()` for serial
      devices (MCU boards) — both filtered to *external* devices only
      (`BlockDevice.is_external`/`SerialDevice.is_external`), identified
      via `lsblk`'s MODEL/TRAN/SIZE/FSTYPE fields and a small built-in
      VID:PID table for common boards (FTDI/CH340 → Arduino-family,
      CP210x → ESP32 — good-enough identification, not an exhaustive
      hardware database) respectively. `DeviceFramework.refresh()`
      diffs the current poll against the previous one and publishes
      `"device.attached"`/`"device.detached"` on the existing event
      bus — same cross-component mechanism every other module already
      uses. `DeviceFramework` owns no timer itself (core/ services
      don't do async/threading); `refresh()` is meant to be called from
      a widget-owned `QTimer` once Field Kit's Device Manager (11.2)
      exists. Detection only in this milestone — no actions yet.

      Real integration testing (not mocked) against this dev sandbox
      found two real "internal noise" categories that would have made
      every device look permanently "attached" if not filtered:
      1. **WSL2's virtual disks** report as ordinary `disk` entries in
         `lsblk` with no transport and `rm: false` — `is_external`
         (removable flag or `tran == "usb"`) excludes these and the
         Pi's own boot media the same way.
      2. **WSL2's virtual legacy COM ports** (`/dev/ttyS0`-`/dev/ttyS7`)
         are *always* reported by `pyserial`, whether or not anything
         is plugged in, with no vid/pid at all — without a filter,
         "no serial devices attached" could never actually happen in
         this dev sandbox. `SerialDevice.is_external` (vid is not
         `None` — a real USB-attached board always has one from its
         USB descriptor, a native/virtual UART never does) fixes this,
         verified against the real environment: both device lists
         correctly return empty with nothing plugged in.
- [x] **11.2 Device Manager module + actions menu** (partial — see
      deferred item below) — `modules/field_kit/module.py`: live list
      of currently-attached devices (name, type, identification)
      sourced from 11.1's `context.devices.refresh()` on a
      widget-owned `QTimer` (same pattern as
      `modules/diagnostics/module.py`'s System Health panel), with a
      per-device actions menu.

      Storage devices get **"Browse Files"** (publishes
      `"files.browse_path_requested"`; `gui/main_window.py` subscribes,
      opens the Files module, then calls its new public
      `navigate_to_path()` — Files already supports browsing arbitrary
      mounted filesystems per its own docstring, this just gives it a
      device-aware entry point instead of requiring the user to know
      the mount path) and **"Eject Safely"**
      (`core/device_framework.py`'s new `eject_storage_device()`:
      unmounts every mounted partition of the disk via `udisksctl`
      where available, falling back to plain `umount`).

      **Deferred, not forgotten: "Open Serial Monitor" for serial
      devices.** A raw read/write console needs a background-thread
      serial read loop (same `QThread`-worker shape as
      `modules/assistant/llm_worker.py`'s `ChatWorker`) — and this dev
      sandbox has no real serial hardware attached to verify that loop
      actually works against. Serial devices currently show
      identification only, with a "coming soon" label; building the
      actual monitor is left for whenever real MCU hardware is
      available to test against, rather than shipping unverifiable
      I/O-threading code.

      **What was and wasn't verified here**: `core/device_framework.py`'s
      `eject_storage_device()` and its partition-lookup helper are unit
      tested with mocked `subprocess` calls, but — like 11.1's
      detection — have **no real-hardware verification**; this dev
      sandbox has no removable media to actually eject. The module
      itself was smoke-tested headlessly (construct the widget, force
      a refresh, confirm no crash and correct empty-state rendering
      with zero devices attached — the only state actually reachable
      here) rather than through `tests/run_module.py` interactively,
      since that harness blocks on `app.exec()` with no user present
      to close the window in this environment.
- [x] **11.3a Flashing confirmation flow — safety rails (design +
      implementation)** — write a Raspberry Pi OS image plus a
      first-boot script that auto-installs MIA to a selected storage
      device, turning this Pi into a field provisioning station for a
      fleet of others, is the one genuinely destructive operation in
      Field Kit (writing to the wrong device destroys its data with no
      undo, and writing to the *boot* device bricks the running Pi) —
      so before writing a single byte of the actual flashing engine, the
      safety design was worked out and built as its own reviewable
      piece, layered (any one rail alone isn't enough):
      1. **Hard boot-device exclusion.** `core/device_framework.py`'s
         new `is_boot_device()` (resolves `findmnt -no SOURCE /` back to
         its parent disk via `lsblk -no PKNAME`) is applied inside
         `list_block_devices()` itself, so a boot device can never even
         appear in a device list to select from — not a UI-layer filter
         that a future code path could bypass. Fails **closed** on any
         lookup error (treats an unknown device as *if* it were the
         boot device). This is a **retroactive fix to already-shipped
         11.2**: `BlockDevice.is_external`'s removable-flag check alone
         isn't sufficient — SD/MMC card readers commonly report the
         boot microSD itself as `rm: 1`, which could have let "Eject
         Safely"/a future "Flash" target the running boot device.
      2. **Full device identity shown before commit.** `gui/flash_confirm_dialog.py`'s
         `FlashConfirmDialog` displays model, size, raw `/dev/` path,
         and current filesystem/mountpoint state alongside the image
         being written — plain language, not an abstract "Device 1".
      3. **Type-to-confirm, not Yes/No.** Same proven pattern as
         `gui/delete_confirm_dialog.py` (used for permanent file
         deletion), one step more rigorous: the user types the device's
         own Linux name (e.g. "sdb") to enable the Flash button — a
         much higher bar against habit-clicking than any fixed phrase.
         The match check (`core.device_framework.flash_confirmation_matches`)
         is its own unit-tested function, not an inline comparison —
         the more dangerous of this project's two "type to confirm"
         flows gets an extra testing seam.
      4. **Re-validate the device is still the same physical drive
         immediately before writing.** `device_still_matches()` re-queries
         current model/size against what the user confirmed against —
         device names aren't stable across hotplug (a different drive
         can take over `/dev/sdb` between dialog-open and write-start),
         so this catches a stale selection rather than writing to
         whatever now answers to that name.
      5. **Re-check not-boot-device immediately before writing, too** —
         cheap, and protects against any reconfiguration between
         selection and confirm.
      Verified: all of the above with unit tests (mocked
      `subprocess`/`lsblk`) and a headless smoke test of the dialog's
      button-gating (starts disabled; rejects partial text, wrong case,
      and trailing whitespace; enables only on an exact match).

      **What's deliberately NOT built yet — 11.3b, the actual write
      engine** — held back on purpose, not an oversight: (a) writing
      raw bytes to a block device typically needs either the operating
      user to already have write access (varies by distro/udev
      config) or elevated privileges, and MIA runs as a systemd
      **user** service, not root — whether the target Pi OS deployment
      has the right permissions out of the box is genuinely unknown
      until tested on real hardware; (b) Raspberry Pi OS images ship
      `.img.xz` compressed, raising a streaming-decompress-while-writing
      vs. decompress-then-write design choice; (c) the actual first-boot
      MIA auto-install mechanism (what gets written into the image's
      boot partition) needs its own design pass. Rails 1/4/5 above are
      real safety infrastructure regardless of how 11.3b resolves these
      questions, which is why they were built and shipped now instead
      of waiting for the whole feature to be ready at once.
- [x] **11.4 Useful Scripts library** — a categorized library of
      user-authored shell/Python scripts with a run-and-view-output
      pane, added as a "Scripts" tab in `modules/field_kit/module.py`
      alongside 11.2's Device Manager (`docs/MODULE_SPEC.md` allows
      only one `ModuleBase` subclass per module folder, so this is the
      first module in the app to need a `QTabWidget`). No sandboxing
      (matches this project's existing stance: single-user offline
      tool, no plugin sandboxing already accepted elsewhere) — these
      are the user's own trusted scripts.

      `core/script_library_manager.py` is the same persisted-JSON CRUD
      pattern as `JournalManager` (script content stored inline, not as
      a path to an external file — one JSON blob to back up, no
      scripts/ directory to keep in sync). `core/script_runner.py`
      starts a script as a real subprocess (stdout+stderr merged,
      line-buffered) and `modules/field_kit/script_worker.py`'s
      `ScriptWorker` streams its output back line-by-line via Qt
      signals, same scoped `QThread`-per-run pattern as
      `modules/assistant/llm_worker.py`'s `ChatWorker` — a script can
      run indefinitely, so reading it on the GUI thread would freeze
      the whole app. `gui/add_edit_script_dialog.py` (name/category/
      interpreter/content) and reusing the existing
      `gui/delete_confirm_dialog.py` for deletion round out the CRUD
      UI, same shape as Notes/Inventory/Waypoints.

      **Unlike this milestone's flashing-engine/serial-monitor siblings
      (11.2/11.3b), a script's execution needs no special hardware or
      permissions this dev sandbox lacks — so this was verified with
      genuine subprocess runs and a real, running Qt event loop, not
      mocks or a "can't test this here" deferral.** That real testing
      caught an actual bug: a "Stop" button click
      (`process.terminate()`) killed only the directly-started `bash`
      process, not a *child* process the script itself spawned (e.g.
      `sleep 30`) — that orphaned child kept the merged stdout pipe
      open, so `ScriptWorker`'s output-reading loop blocked for the
      rest of the script's runtime (measured at the full ~30s) instead
      of stopping promptly. Root-caused with a series of direct
      reproductions (bypassing Qt entirely to isolate the process
      layer), then fixed: `start_script_process()` now starts the
      script in its own process group (`start_new_session=True`), and
      a new `terminate_process_tree()` signals that whole group
      (`os.killpg`), not just the one PID Python knows about — verified
      the fix drops stop time from ~30s to under 1ms, and re-verified
      through the actual GUI (`ScriptWorker`/"Stop" button), not just
      the isolated process-management function.
- [x] **11.5 Security/Network Toolkit (partial — recon tools only, see
      below for what's blocked)** — a third "Security" tab in
      `modules/field_kit/module.py`, alongside 11.2's Device Manager and
      11.4's Scripts (the same `QTabWidget` reasoning as those). Wires
      up three pure-Python tools that were already sitting in the repo
      untracked from an earlier session (`core/hash_identifier.py`,
      `core/password_strength.py`, `core/subnet_calculator.py` — the
      last of these is also where this session's WSL-VM-crash root
      cause was found and fixed, see the "root cause found" note
      earlier in this doc) into a real UI for the first time, plus one
      genuinely new tool: `core/port_scanner.py`, a pure-Python TCP
      connect-scan port scanner (`socket.connect_ex()`, no `nmap`
      needed — confirmed `nmap` isn't installed in this dev sandbox and
      can't be added without root, so a connect scan is what's
      buildable here, not a SYN scan or OS fingerprinting, both of
      which genuinely need `nmap`/raw sockets). Runs via
      `modules/field_kit/port_scan_worker.py`'s `PortScanWorker`, same
      scoped-`QThread` pattern as the Scripts tab's `ScriptWorker` —
      scanning even the short common-ports default can block for
      several seconds. Verified with a real headless-Qt smoke test
      driving all four tools through the actual tab widgets, including
      the port scanner's real `QThread` against a real local TCP
      server bound to an ephemeral port (deterministic, no network/
      internet dependency).

      **Wi-Fi/network analyzer and all "active tooling" (hash cracking
      via John/Hashcat, packet crafting via scapy, exploit-framework
      launching) are explicitly NOT implemented** — confirmed blocked,
      not just deferred: none of `nmap`/`john`/`hashcat`/`scapy`/
      `aircrack-ng`/`hydra` are installed in this dev sandbox, and none
      can be added without root, the same "no sudo" wall Ollama's
      portable-binary install once hit (Media/Music's own `libpulse`
      wall — cited here previously — is gone as of 2026-09-09, see the
      Music module built as v0.20; these tools remain genuinely
      blocked). The Security tab itself shows this limitation
      directly to the user rather than silently omitting those
      features. See `docs/KNOWN_ISSUES.md`. Network-facing recon
      (packet sniffer, wifi/BT scanning) remains reconciled with, not
      duplicated from, the still-unbuilt Communications section
      (`docs/ROADMAP.md`'s v1.0+ bucket) when that section is
      eventually built.
- [ ] **11.6 MCU firmware flashing** — ties Workshop & Electronics'
      already-planned (but unbuilt) "MCU flashing" bullet to 11.1's
      serial-device detection: flash firmware via `esptool`/`avrdude`
      wrappers to an identified, currently-attached board, rather than
      inventing a second, separate device-detection mechanism for it.
      **Investigated 2026-07-13, deliberately left untouched (user's
      call, not a build attempt that failed)**: `avrdude` is a genuine
      apt package, not installed, and blocked the same "no sudo" way as
      11.5's `nmap`/`hashcat`; `esptool` is pip-installable without
      sudo, so tooling isn't the blocker for ESP32/ESP8266 specifically
      — but zero serial devices exist in this dev sandbox
      (`/dev/ttyUSB*`/`/dev/ttyACM*` don't exist) either way, so even
      an `esptool`-only slice couldn't be verified end-to-end here, same
      as 11.3b's disk-write engine and Field Kit's already-deferred
      "Open Serial Monitor." Revisit once a real ESP32/AVR board (and,
      for `avrdude`, a machine with root) is available to test against.

## v0.12 breakdown (planned)

Expedition Mode: field-ready outing tracking — hiking, camping, fishing,
kayaking, biking, and more (`core/trip_manager.py`'s `ACTIVITY_TYPES`) —
at the user's explicit request. An **Expedition**
(`core/expedition_manager.py`) is the top-level dated outing container;
it can hold multiple **Trips** (`core/trip_manager.py`, one activity/leg
each, e.g. a weekend Expedition with a Saturday hike and a Sunday
fishing trip as two separate Trips). Everything buildable
with zero extra hardware/data landed this pass — live GPS position/
speed, an elevation profile, automated weather fetch, and real tiled
offline maps did **not**, and are called out explicitly below rather
than half-built, same reasoning as 10.x's "offline maps, trails,
elevation... wait for real GPS/mapping hardware/data" and 11.3b's
deliberately-deferred disk-write engine.

- [x] **12.1 Expedition + Trip Manager core, module CRUD** —
      `core/expedition_manager.py` (`Expedition` dataclass + manager,
      `AppContext.expeditions`) and `core/trip_manager.py` (`Trip`
      dataclass + manager, `AppContext.trips`; `expedition_id` is a
      required FK, and `activity_type` is a fixed-vocabulary field —
      Hiking/Camping/Fishing/Kayaking/Biking/Other, same "plain str, not
      an enum" reasoning as `Waypoint.category` below), same
      persisted-JSON pattern as `core/waypoint_manager.py`
      (`data/expeditions.json`/`data/trips.json`). New
      `modules/expeditions/module.py`: an Expeditions list at the top,
      the selected Expedition's Trips below it, same CRUD shape as
      Notes/Inventory/Waypoints
      (`gui/add_edit_expedition_dialog.py`/`gui/add_edit_trip_dialog.py`,
      reusing `gui/delete_confirm_dialog.py` as-is). Selecting a Trip
      opens `gui/trip_detail_dialog.py`, which every later 12.x
      milestone below adds its own section to rather than spawning a
      separate screen. This milestone's slice of that dialog is just
      the Route section: pick an existing Waypoint, add it to the
      trip's ordered planned route, remove one,
      `TripManager.planned_route_distance_km()` (reuses
      `haversine_distance_km()`, doesn't reinvent it) shows the
      upfront-estimate distance. Deleting an Expedition unlinks, not
      cascade-deletes, its Trips (confirmed via an in-app warning
      dialog before delete) — consistent with this project's
      non-destructive bias elsewhere (delete/adjust actions in
      `core/inventory_manager.py`).
- [x] **12.2 Campsite/waypoint categories** — additive `category: str
      = ""` field on `Waypoint` (backward-compatible default for
      existing `waypoints.json` entries missing the key), a fixed
      suggested vocabulary (Campsite, Trailhead, Water Source,
      Viewpoint, Other) via a `QComboBox` in
      `gui/add_edit_waypoint_dialog.py` — stored as plain `str`, not an
      enum, so an unrecognized/blank value just means "uncategorized."
      `modules/navigation/module.py`'s `format_waypoint_row()` shows
      the category when set.
- [x] **12.3 Gear checklist per trip** — `GearItem` (label, optional
      `item_id` linking to `core/inventory_manager.py`, `packed: bool`)
      embedded on `Trip`. `add_gear_item()`/`toggle_gear_packed()`/
      `remove_gear_item()` on `TripManager`. The Trip detail dialog's
      Gear Checklist section supports both "Add From Inventory" (a
      picker over `context.inventory.all_items()`) and a freeform
      custom item not tracked in Inventory at all. Packing/unpacking a
      gear item deliberately does **not** adjust the linked Inventory
      item's quantity — packing a listed item isn't "consuming" it,
      unlike the M3-bolts use case `adjust_inventory_quantity()` was
      built for in milestone 5.10.
- [x] **12.4 Trip journal integration with explicit weather field** —
      additive `trip_id: Optional[str] = None` and `conditions: str =
      ""` fields on the existing `JournalEntry`
      (`core/journal_manager.py`), both backward-compatible defaults.
      `conditions` is a first-class, structured field — not folded into
      `body` — per the user's explicit call-out that weather should be
      trackable on its own. New `JournalManager.entries_for_trip()`
      filters/sorts the same way `all_entries()` already does. The Trip
      detail dialog's Journal / Weather Log section lists linked
      entries and adds new ones via a title/body/conditions form,
      calling the *existing* `context.journal.add_entry()` (extended
      with `trip_id`/`conditions` kwargs) rather than an add-then-update
      round trip.
- [x] **12.5 Speed & distance via logged checkpoints** — `Split`
      (waypoint_id, `logged_at` ISO datetime) embedded on `Trip`.
      `TripManager.record_split()` is a one-tap "arrived at this
      waypoint now" log — the field-buildable stand-in for live GPS
      tracking: the user checks in at each waypoint as they reach it,
      same mental model as a compass-and-map hiker logging times at
      trail junctions. `leg_summaries()` derives distance (haversine)
      and elapsed time between consecutive logged splits, guarding the
      same-second/out-of-order edge case by returning `speed_kmh=None`
      rather than dividing by zero or a negative number;
      `total_distance_km()`/`average_speed_kmh()` aggregate across all
      legs. Kept distinct from 12.1's **planned** route distance (an
      upfront estimate from the route alone, independent of whether/
      when it's actually walked) — the Trip detail dialog's Speed &
      Distance section shows both.
- [x] **12.6 Schematic trip map view** — `gui/trip_map_view.py`:
      `QGraphicsView`/`QGraphicsScene` plot of a trip's route
      waypoints, positioned by plain equirectangular projection
      (`project_to_scene_xy()`, a free function — testable without Qt),
      connected in route order, each pin labeled with its name and
      colored by category (12.2). Embedded directly under the Trip
      detail dialog's Route section; wheel-to-zoom + click-drag pan via
      a small `QGraphicsView` subclass. Deliberately **not** a real
      tiled basemap — no bundled offline map imagery exists in this
      project (same gap `modules/navigation/module.py`'s own docstring
      already flagged) — so this is a visualization of already-entered
      coordinates, not click-to-place: a click on blank schematic space
      has no real-world meaning without underlying map imagery to
      anchor it. Verified with a real headless-Qt (offscreen QPA)
      smoke test exercising the actual dialog/widgets end to end, not
      just the pure-function unit tests.
- [x] **12.7 Trip photos** — new top-level `trip_photos/` directory
      (config key `trips.photo_root_path`, `_resolve_photo_root_path()`
      mirroring `core/reference_library_manager.py`'s
      `_resolve_root_path()` exactly), kept out of `data/` entirely so
      `core/backup_manager.py`'s `data/` rglob never sweeps binary
      photo files alongside small JSON documents (same reasoning as the
      Reference Library/voice models gitignore entries).
      `TripManager.add_photo()` copies an existing image file in (via
      `QFileDialog.getOpenFileNames` — import-only, no camera capture,
      that needs real Pi camera hardware this dev sandbox doesn't
      have); `remove_photo()` deletes the stored copy (not the user's
      original) and unlists it. Trip detail dialog shows a thumbnail
      grid (`QListWidget` in icon mode), double-click to preview at
      full size in a plain `QDialog`.

**Explicitly deferred, not half-built (flagging so it isn't mistaken for
an oversight later):**
- **Live GPS position/speed** — no GPS receiver in this dev sandbox, and
  `docs/HARDWARE.md` itself still lists GPS module choice as an open
  decision for the Pi 5 target. 12.5's logged-checkpoint speed/distance
  is the buildable-now substitute; swapping in live GPS later is an
  additive follow-up (auto-log a split instead of a manual tap), not a
  redesign.
- **Elevation profile** — needs a bundled offline DEM/elevation
  dataset; none chosen. `astral` (already a dependency) has no
  elevation data.
- **Automated weather fetch** — needs either a live API call (in
  tension with offline-first) or a bundled/cached-forecast design.
  12.4's manual `conditions` field ships now; automated fetch is a
  separate future pass.
- **Real offline map tiles / trail rendering** — a standalone GIS
  subsystem (bundled map data + a tile-rendering widget). 12.6's
  schematic plot covers "labeled points on a map" without this.

## v0.13 breakdown (planned)

Device Profile + Theme System, at the user's explicit request to
prepare MIA for its real target hardware (a Pi 5 + AI HAT+ 2, which
"this AI is going to live on") as one codebase serving two editions —
**Core** (the Pi, resource-constrained, a field data-gathering tool)
and **Home** (a desktop workstation, more storage/resources) — rather
than two separate packages, plus a selectable theme system that can
differ in weight between the two editions.

- [x] **13.1 Device Profile** — `"device_profile": "core"` added under
      `config/default_config.json`'s existing `"system"` block (values
      `"core"`/`"home"`; confirmed the merge is safe for existing users
      via `tests/test_config_manager.py`'s existing new-default-key
      coverage). New `core/device_profile.py` — a thin helper (no state
      of its own beyond the one config value, so plain functions, not a
      manager class): `get_device_profile()`/`is_core_profile()`/
      `is_home_profile()`. Deliberately **not** auto-detected from
      hardware (e.g. `platform.machine()`) — explicit config is more
      robust and matches this project's existing preference for
      explicit config over inference. Viewable/changeable via a new
      "Device Profile" dropdown in `modules/settings/module.py`;
      `deploy/install_kiosk.sh` sets it to `"core"` (alongside
      `kiosk_mode`) in its existing templated-config-writing step.
- [x] **13.2 Theme system** — nothing like this existed before this
      milestone: every dialog/screen (24+ call sites) hardcoded
      `gui.styles.DARK_FIELD_THEME` directly, and `config.gui.theme` sat
      completely unread. New `gui/theme_manager.py`: a `THEMES` registry
      (`dark_field` — the pre-existing theme, kept as-is; `low_energy` —
      minimal flat styling for Core/Pi's constrained hardware;
      `colored` — a brighter saturated accent variant; `anime_monochrome`
      — black-and-white, high-contrast, stylized borders, the user's
      explicit "anime style" ask) plus `get_theme_stylesheet()`
      (falls back to `dark_field` for an unrecognized id). Applied
      **once, at the `QApplication` level** in
      `core/application.py`(`self.qt_app.setStyleSheet(...)`) — Qt's
      stylesheet cascade means every widget/dialog inherits it
      automatically, which is why the ~24 old per-widget
      `self.setStyleSheet(DARK_FIELD_THEME)` calls (and their now-unused
      imports) were removed from every dialog/screen across `gui/*.py`
      and `tests/run_module.py` as part of this same milestone — leaving
      them would have silently frozen every dialog on the old theme
      regardless of what's selected, since a widget's own stylesheet
      call overrides inherited cascade. The one deliberate exception:
      `modules/knowledge/zim_text_browser.py` still forces its own
      plain white background, since ZIM content is third-party HTML
      that assumes a light background — documented in its own docstring
      as the one intentional case that must *not* inherit the app-level
      theme. New "Theme" dropdown in `modules/settings/module.py`
      publishes `"theme.changed"` on the existing event bus;
      `MIAApplication` subscribes and re-applies the stylesheet live, no
      restart required. Verified with a real headless-Qt (offscreen
      QPA) smoke test: booted a real `MIAApplication`, cycled all four
      themes via the event, and confirmed both that the QApplication-
      level stylesheet actually changed each time and that a
      freshly-opened dialog (`AddEditTripDialog`) no longer sets its
      own competing stylesheet — the concrete regression this
      milestone's cleanup step exists to prevent.

      **A real visual check (not just the stylesheet-string-equality
      smoke test above) caught a genuine bug the string checks
      couldn't:** rendering each theme against a sample window built
      from the exact widget/object-name structure `gui/main_window.py`
      actually uses (`QLabel#TitleLabel`/`QLabel#SubtitleLabel` both
      nested inside `QFrame#HeaderBar`) and grabbing a real `QPixmap`
      via Qt's offscreen platform showed `anime_monochrome`'s app
      title/greeting rendering as **black text on that theme's solid
      black header bar — completely invisible** (both defaulted to
      black for contrast against this theme's white body background
      elsewhere, e.g. a module's own page header; nothing wrong when
      not nested inside `#HeaderBar`). Fixed with a descendant selector
      (`QFrame#HeaderBar QLabel#TitleLabel, QFrame#HeaderBar
      QLabel#SubtitleLabel { color: #ffffff; }`) scoped to just that
      nesting case. **Lesson reinforced**: this project's own established
      pattern (5.6's grounding bugs, 11.4's Stop-button bug) held again
      here — a mocked/string-equality check proved the *mechanism*
      works, but only looking at actual rendered pixels caught a real
      user-facing defect the mechanism-level check was blind to.

**Profile <-> theme relationship kept as a deploy-time convention, not
runtime magic**: `gui.theme`'s unconditional JSON default stays
`dark_field` (no conditional-default-based-on-another-key logic to
maintain); `deploy/install_kiosk.sh` sets both `device_profile="core"`
and `theme="low_energy"` together for real Core deployments. A user can
always override either independently via Settings.

## v0.14 — Pi 5 + AI HAT+ 2 deployment readiness (audit pass, no hardware)

No physical Pi 5/AI HAT+ 2 exists in this dev sandbox, so this pass is
**documentation and code-audit only** — not a real deploy attempt, and
not fabricated fixes for problems that can't be verified without the
hardware:
- Reviewed `deploy/install_kiosk.sh`/`deploy/mia.service` against
  everything shipped since (Expedition Mode's `trip_photos/`, new
  config keys) — no changes needed: every new persisted-JSON manager
  and `trip_photos/`'s root already creates its own directory lazily
  in its own `__init__` (same pattern as `core/reference_library_manager.py`),
  so deploy scripts never needed to pre-create them; `mia.service` has
  no Expedition-specific paths hardcoded.
- Flagged (`docs/KNOWN_ISSUES.md`, "Open" section) the real open
  question the user's "this AI is going to live on that HAT" framing
  raises: `core/llm_manager.py` currently targets Ollama's generic HTTP
  API, and whether Ollama can drive the AI HAT+ 2's NPU accelerator (or
  a different runtime/model format is needed) is genuinely unresolved
  without the real hardware to test against.
- Flagged (same file) Field Kit's and Diagnostics' 3-second polling
  timers as a "revisit power/CPU budget once real Core hardware exists"
  item — not changed now, since adjusting intervals blindly without
  real hardware to benchmark against would be exactly the kind of
  unverified guess this project avoids elsewhere.

## v0.15 — Expedition data sync (Pi -> Home via physical docking)

At the user's explicit request: the Pi ("Core") is a field
data-gathering tool that, when docked, exports its Expedition data to
the Home desktop. Sync is **physical storage transfer**, not network —
`docs/HARDWARE.md`'s storage-split section already anticipated exactly
this ("the same drive can be pulled and mounted on a desktop
directly"), reusing the Field Kit's existing Connected Device Framework
(USB storage detection, milestone 11.1) rather than building a new
mechanism.

New `core/expedition_sync.py`, mirroring `core/backup_manager.py`'s
proven zip-bundle pattern (`manifest.json` + payload files, staged
extraction via the newly-public `safe_extract_zip()` — renamed from
`_safe_extract_all()` specifically so this module could reuse it
verbatim instead of reimplementing the same path-traversal defense)
but differing in two ways: **scoped to Expedition-relevant data only**
(`expeditions.json`/`trips.json`/`waypoints.json`/`journal_entries.json`/
`inventory_items.json` plus the `trip_photos/` tree — everything a Trip
detail view references, not a full app backup), and **merges by record
id on import rather than overwriting** (`restore_backup()`'s full-replace
is right for restoring one machine to a prior state; a Home desktop
likely already has its own data from other sources, so merging is the
only sane semantic — a record whose id already exists at the
destination is skipped, since ids are independently-generated UUIDs and
a real match means "already imported," not a coincidence).

`modules/field_kit/module.py`'s existing per-device action row (which
already had "Browse Files"/"Eject Safely") gained "Export Expedition
Data Here" (writes a timestamped `.zip` to the device's mountpoint) and
"Import Expedition Data From Here" (`QFileDialog` to pick a bundle off
the device), same not-mounted guard and same shape as the existing
Eject button calling `core/device_framework.py` directly.

Like `restore_backup()`, this module only touches files on disk — an
already-running `TripManager`/`ExpeditionManager`/etc. won't see
imported records until restart, same "restart to see the change" UX
already used for backup restore, not a new pattern to learn.

Verified with a real headless-Qt (offscreen QPA) smoke test that
exercises the actual `FieldKitModule` button handlers end to end (not
just the core functions in isolation): a simulated Pi instance
(isolated data/trip_photos dirs) with a real Expedition/Trip/Waypoint/
Journal-entry/photo exported through a fake docked `BlockDevice`, then
imported into a completely separate simulated Home instance — confirmed
every record and the photo file arrive correctly, and re-importing the
same bundle a second time adds nothing further (no duplication).

## v0.16 — Project Manager (v1.0+ bucket, zero-hardware slice)

The next v1.0+-bucket slice buildable with zero real hardware (same
rationale as Activity Log/Navigation/Field Kit/Expedition Mode before
it) — the "Project Manager" tool listed under Toolbox in this doc's
"Top-level module sections" table. Two-level CRUD, deliberately the
same shape as `modules/expeditions/module.py`: `core/project_manager.py`
(`Project`: name/status — fixed vocabulary `PROJECT_STATUSES` =
Planning/Active/On Hold/Complete, same pattern as `Trip.activity_type`
— /due_date/description) holds multiple `core/task_manager.py` `Task`
records (title/done/due_date/notes). Deleting a Project unlinks (does
not cascade-delete) its Tasks, same non-destructive bias as
Expedition/Trip. Lives as a new `ProjectTool` (`modules/toolbox/tools/
project_tool.py`) inside the existing Toolbox module rather than a new
top-level module — auto-discovered with a one-line addition to
`ToolboxModule._tools`, no registry changes needed elsewhere.

Assistant-connected from the start, following this project's now-
established conservative-first-pass convention (read + add only, no
delete/update — see 5.12's Expedition Mode batch for the same
approach): `add_project`, `list_projects`, `add_task`, `list_tasks`.
Registry grows 39 -> 43. `tests/live_model_check.py` extended with a
seeded Project/Task fixture and 5 new golden-set cases (one per new
tool, plus a false-positive check that ordinary use of the word
"project" — "This project is taking forever" — doesn't gate anything
open, the same "trip"/"event" false-positive pattern already pinned
elsewhere). Passed **54/54 on two independent full runs**.

**Found and immediately fixed a real data-pollution slip while
smoke-testing**: an ad hoc verification script (checking the real
Assistant handler round-trip through `AssistantModule`) isolated
`config_manager_module._CONFIG_FILE` but forgot `project_manager_module`/
`task_manager_module`'s own `_DATA_DIR`/`_PROJECTS_FILE`/`_TASKS_FILE` —
the exact gotcha this project has hit before (see the memory notes on
scratch-script data isolation), repeated on a brand-new pair of
managers. Caught immediately by checking `data/` for stray files after
the smoke test and confirmed via `git log`/`git check-ignore` that the
two leaked files had never been tracked and contained nothing but the
test's own "Kitchen Remodel"/"Pick tile" fixture data before deleting
them outright.

Verified with a real headless-Qt smoke test through the actual
`ProjectTool` UI (add project, select it, add a task, toggle it done —
all round-tripping through the real managers, not mocks) and a separate
full-app-boot + `ModuleManager.discover()` check confirming `ProjectTool`
shows up under Toolbox with zero registry edits, exactly as
`core/module_manager.py`'s documented auto-discovery behavior promises.

### Project Manager CRUD follow-up: delete_project, delete_task, mark_task_done

Follow-up batch to v0.16 (registry 43 -> 46), completing Project
Manager's Assistant coverage the same way 5.13 followed up 5.12's
Expedition Mode first pass. `delete_project` (unlinks, does not
cascade-delete, its Tasks — same non-destructive bias as
`delete_expedition`), `delete_task`, and `mark_task_done` (a boolean
`done` toggle by title — the "check off a to-do" case, not covered by
`update_task`'s general field-setter). All three resolve their target
by exact case-insensitive name/title match and fail closed ("I don't
have a project/task called '...'") on no match, same pattern as every
delete handler in this file.

**Real, not just plausible, name-insertion gating gap found while
writing this batch's own tests** — caught before it ever reached the
live model, by re-deriving `test_delete_note_phrasing_gates_open`'s
exact reasoning rather than assuming it didn't apply: "project"/"task"
are exactly as common as "note" (already-pinned false-positive check:
"This project is taking forever" must not gate anything open), so
neither gets a bare trailing-space trigger the way "alarm "/"component "
do. That means "Delete my Garage Rewire project" (name inserted
before the noun) doesn't gate open on `delete_project`'s own triggers —
a real gap, deliberately accepted, same trade-off `delete_note` already
made. `delete_project`/`delete_task`/`mark_task_done` trigger phrases
instead cover "delete/mark the X called Y" phrasing (name after the
noun), and their gating/golden-set tests use that phrasing rather than
papering over the gap.

Also added `TaskManager.all_tasks()` (mirrors `TripManager.all_trips()`)
and used it to simplify `_action_list_tasks`'s cross-project case,
which previously did its own per-project loop.

57/57 on two independent live-model runs (3 new cases: delete project,
delete task, mark task done — plus all 54 prior cases still green).
Verified with a real handler-level smoke test against real (properly
isolated this time) managers: mark done, mark not done, delete task,
delete project, and a fail-closed delete of a nonexistent project, all
round-tripping correctly with no `data/` pollution afterward.

## v0.17 — Memories (built)

The first of three new subsystems from the 2026-07-14 wearable-companion
vision update (see `docs/VISION.md`'s Mission section and
concept-mapping table) — picked to build first because it's the lowest
new-design-risk piece: almost entirely read-only aggregation over data
Expedition Mode/Toolbox already capture, no new hardware required for
a first version.

- [x] 17.1 `core/memory_manager.py` — read-only aggregation service, no
      persisted file of its own. `recap_for_expedition()` computes an
      `ExpeditionRecap` on demand (never stored, so it can't go stale
      relative to the underlying records): `duration_days` (from the
      Expedition's own dates, falling back to its Trips' date span if
      unset), `activity_breakdown` (distance/pace grouped by
      `Trip.activity_type`, from *logged* `total_distance_km()`/
      `average_speed_kmh()` — actual data, not the planned-route
      estimate), `waypoint_categories_visited` (unions each Trip's
      logged splits with its planned route, since a Trip with no splits
      yet should still show its planned campsites), `journal_highlights`
      (entries linked via `trip_id`), and `photo_filenames`. Also
      `all_recaps()` (most-recent-first) and `on_this_day()`.
- [x] 17.2 `modules/memories/module.py` — new top-level module (#19 in
      this doc's module list above, auto-discovered with zero registry
      edits), a scrollable list of past Expeditions each showing its
      recap, a photo thumbnail strip (reuses `trip_detail_dialog.py`'s
      `QIcon(path)`-into-`QListWidget` pattern), and a per-Trip "View
      Route Map" button, most-recent-first. An "On This Day" section
      surfaces above the main list when applicable.
- [x] 17.3 Location-tagged resurfacing on Navigation's maps — solved by
      reusing `gui/trip_detail_dialog.py`'s existing `TripMapView`
      wholesale rather than building new map code: each recap's Trip
      rows have a "View Route Map" button that opens that Trip's own
      detail dialog (map + everything else), the same dialog the
      Expeditions module already uses.
- [x] 17.4 Assistant hook: **design revised from the original plan
      during implementation.** The original idea (reuse the
      `device_help` grounding pattern, since "this is a
      retrieval/summarization question, not an app action") turned out
      to be solving a problem that doesn't exist here — `list_expeditions`/
      `list_trips`/etc. already establish the pattern for exactly this
      kind of dynamic-data Q&A via the tool-calling registry, and
      `device_help`'s grounding is specifically for the app's own
      static how-to documentation/reference content, not live user
      data. Registered `recall_expedition` (registry 46 -> 47) instead,
      consistent with every other read action in this file. Found a
      real gating gap while adding its golden-set case (not while
      writing the unit-level gating test, which used safe phrasing from
      the start): "Tell me about my Field Season expedition" (name
      before the noun) doesn't gate open — same accepted trade-off as
      delete_project/delete_task/mark_task_done above; "tell me about /
      describe the expedition called X" phrasing (name after the noun)
      is supported instead.
- [ ] 17.5 (stretch, deferred unless requested) catch/tally counts and
      species-identified counts in the recap — these need the new
      per-trip tally primitive from the Missions milestone below;
      Memories can display them once that primitive exists but doesn't
      need to invent it.

60/60 on two independent live-model runs (3 new cases: recall by name,
recall most recent, and a collision-risk case against `list_expeditions`
— all passed cleanly once the gating gap above was fixed). 841 tests
passing. Verified with real headless-Qt smoke tests: the module widget
built through full app-boot module discovery with realistic seeded data
(an Expedition with a hike and a paddle, logged splits, a journal entry,
a photo), and the "View Route Map" button confirmed to actually open
`TripDetailDialog` without crashing (`context.inventory` turned out to
be a real dependency of that dialog's Gear section the first smoke-test
pass didn't wire up — not a bug in the new code, just an incomplete
test fixture, fixed before re-running).

**Deliberately NOT in this milestone**: photo-based species/plant
identification (needs a camera + vision model — see `HARDWARE.md`'s new
Camera section), live GPS-based pace/distance (needs a GPS module — see
`HARDWARE.md`'s updated GPS note), and the Missions engine itself (next
milestone — an independent consumer of Trip data, not a dependency in
either direction).

## v0.18 — Missions/Gamification (built)

Turns the user's stated goals/hobbies into tracked objectives (e.g. a
"Master Baiter" mission for a fishing trip: an objective for time spent
fishing, an objective for fish caught). Scope resolved via
`AskUserQuestion` before building, same as Expedition Mode's 3-part
scope before v0.12: (1) Assistant creation built in this same pass, not
deferred to a follow-up batch — the "AI creates a mission" moment is
core to the vision, not an afterthought; (2) a new standalone
"Missions" module (#20 in this doc's module list), not contextual-only,
so there's one place to see every active/completed mission at a glance.

`core/mission_manager.py`: `Mission` (name, optional `trip_id` link —
mirrors `JournalEntry.trip_id`'s optional-FK pattern, so a mission can
be trip-scoped like "Master Baiter" or a general goal like "finish
wiring the garage" — status) holds one or more `Objective`s (nested in
the mission's own JSON, same reasoning as `GearItem`/`Split` nested in
`Trip`). Two metric types (`METRIC_TYPES`): `"tally"` — a manually-
incremented counter (fish caught, species identified) — the one
genuinely new primitive this milestone needed, since nothing else in
the app models an arbitrary count; and `"trip_duration_hours"` —
computed live from the linked Trip's logged splits (first-to-last-split
elapsed time), never stored, so "time spent fishing" derives from
existing Trip data for free with zero manual entry, exactly the
original design goal.

New standalone module `modules/missions/module.py` (auto-discovered,
zero registry edits) — two-level CRUD (Missions, then the selected
Mission's Objectives), a "+1 Tally" button for tally-type objectives,
and a linked-trip picker at mission creation only (`gui/add_edit_mission_dialog.py`;
the link can't change after creation, same as Trip's fixed
`expedition_id`) plus an objective-adding dialog
(`gui/add_edit_objective_dialog.py`).

Assistant-connected immediately (registry 47 -> 53): `add_mission`
(optionally linked to an existing Trip by name), `list_missions`
(with live objective progress), `add_objective`, `log_mission_progress`
(the "I caught one!" moment — increments a tally objective, defaulting
to the mission's only tally objective if unambiguous, otherwise asking
which one), `delete_mission`, `complete_mission`. Domain `"missions"` —
confirmed via direct registry check that a mission-related prompt
attaches only the 6 missions-domain tools plus the 6 always-on
`system`-domain tools (12 total), never an unrelated domain, exactly
as domain-scoped attachment is designed to do.

**Known, deliberately accepted gap**: `log_mission_progress`'s trigger
phrases are generic ("log a catch", "log progress", "count that") since
they can't hard-code every possible hobby's vocabulary — literally
saying "I caught one!" with no mention of "mission"/"catch"/"progress"
won't gate open on its own. Same category of trade-off as
delete_project/delete_task/mark_task_done/recall_expedition's
name-before-noun gaps elsewhere in this file: real, documented, not
worth chasing further given the fixed-trigger-phrase gating design this
whole registry uses.

67/67 on two independent live-model runs (7 new cases: one per new
tool, plus a false-positive check that ordinary use of the word
"mission" doesn't gate anything open). 911 tests passing. Verified with
real headless-Qt smoke tests: the module widget through full app-boot
discovery (add mission, select it, add both objective types, +1 tally,
confirmed the trip_duration_hours objective auto-computed 2.5 hours of
progress with zero manual entry), and the Assistant handlers end to end
through the actual `AssistantModule` (add_mission -> add_objective ->
log_mission_progress -> list_missions round-tripping correctly).

## v0.19 — Home Dock auto-launch Dashboard (built)

Docking Core to the Home desktop auto-navigates MIA to a Dashboard
view rather than requiring the manual "Import Expedition Data" click
v0.15 built. Scope resolved via `AskUserQuestion` first, same as v0.18:
(1) build only the fully-testable "already running, auto-navigate"
half now — the original vision's "launch MIA itself from a cold,
not-yet-running state" needs a persistent Windows background watcher
(pywin32/WMI USB-arrival events), genuinely unbuildable-and-verifiable
in this Linux dev sandbox, so it's a separate, deliberately deferred
follow-up, same honest treatment as 11.3b/11.6/the AI HAT+2 question;
(2) auto-import, not just auto-navigate — docking a recognized Core
merges its Expedition data in with no manual button click needed.

**Core-detection mechanism**: `core/expedition_sync.py::find_export_bundles()`
globs a newly-mounted device's root for `mia_expedition_export_*.zip` —
the exact filenames the existing Export button already writes.
Deliberately does NOT try to read a marker file describing the docked
device's own config (e.g. its `system.device_profile`) — the real Pi 5
USB gadget-mode mount layout (`docs/HARDWARE.md`) is still unverified
against real hardware, so detection instead relies only on files this
app itself created, working regardless of how gadget-mode ends up
exposing storage. `import_expedition_data()`'s existing merge-by-id is
already idempotent, so no "already processed" bundle-tracking was
needed — re-importing a bundle on a later dock is safe and cheap.

**Removed the "restart MIA to see imported data" limitation** (both
for this new auto-import path and the existing manual Import button) by
adding a `reload()` method to the 5 managers `import_expedition_data()`
touches (`ExpeditionManager`/`TripManager`/`WaypointManager`/
`JournalManager`/`InventoryManager`) — a thin public wrapper around
each one's existing private `_load()`.

`modules/field_kit/module.py`'s existing device-polling `_refresh_devices()`
now calls a new `_check_for_docked_core()` per storage device (Home
profile only — a Core docking to another Core was never part of the
vision): finds bundles, imports each, reloads the 5 managers, raises a
`NotificationManager` notification summarizing what came in, and
publishes the *existing* `"assistant.open_module_requested"` event with
`module_id="dashboard"` — reusing `gui/main_window.py`'s already-wired
handler rather than inventing a new navigation mechanism, since
navigating to a module by id is exactly what that already does whether
the request came from the Assistant or here. A per-device "already
auto-imported this dock" set (pruned to currently-connected device
names each poll) stops the same still-docked device from re-triggering
the notification/navigate on every 3-second poll tick, while still
treating an unplug-and-redock as fresh.

New `modules/dashboard/module.py` (auto-discovered, module #21): a
read-only aggregation view — recent Activity Log entries, active
Missions with objective progress, recent Memories (Expedition recaps),
upcoming Calendar events, active Projects/open Tasks. **Deliberately
excludes "recently played music"** from the original vision — at the
time, Media/Music wasn't a built module yet (confirmed blocked on
missing `libpulse` in this dev sandbox then). **2026-09-09: Music now
exists (v0.20)**, but a dashboard now-playing widget remains a
separate, still-unbuilt follow-up — this exclusion is a scoping
decision, not a data-availability one anymore. Writes its own small
summary-line formatting rather than importing `modules.missions.module`/
`modules.memories.module`'s formatting helpers — modules never import
another module directly (`CLAUDE.md`'s one-directional layering rule).

No new Assistant action needed — the existing generic `open_module`
action already handles "open my dashboard"-style requests for any
module, Dashboard included, for free.

**Found and fixed a real test-isolation bug while writing the
committed tests for `_check_for_docked_core()`** (distinct from the
manual smoke test, which is what caught it): the new test file
constructed a real `NotificationManager` without isolating
`core.notification_manager`'s `_DATA_DIR`/`_NOTIFICATIONS_FILE`, so
`context.notifications.notify()` calls in both the manual smoke test
and the first pytest run landed in this dev machine's actual
`data/notifications.json` — three "Core docked" test-artifact
notifications, confirmed via `git check-ignore`/`git log` to be
untracked with no real prior content, deleted outright rather than
surgically edited. Fixed at the root in the test fixture. **Lesson for
any future test touching Field Kit's docking flow**: `NotificationManager`
needs the same isolation as every other persisted-JSON manager — easy
to forget precisely because it's one line among five other managers'
isolation setup, not because the pattern itself is unclear.

Verified with a real, full end-to-end smoke test simulating two
separate machines (a "Pi" instance seeding and exporting real Expedition
data, a fresh "Home" instance in Home profile with zero data): confirmed
the exported bundle is auto-detected, auto-imported with the Home
Expedition count going from 0 to 1 with **no restart**, the
auto-navigate event firing exactly once, a notification raised, a
second poll tick for the same still-docked device NOT re-triggering,
and the Dashboard module's widget correctly showing the newly-imported
Expedition via Memories — all in one continuous run. 936 tests passing.

## Assistant architecture: domain-scoped tool attachment (built, 2026-07-14)

At the user's explicit request to make the Assistant "the most advanced
we can make it" and use the AI HAT+2's 40 TOPS "for what it's capable
of" — investigated first, rather than guessing at HAT-specific code:
`core/llm_manager.py`'s docstring overclaimed that moving to the real
Hailo-10H runtime (`hailo-ollama`) would be "just a config change";
`docs/KNOWN_ISSUES.md` already correctly flags this as unverified
without real hardware. Softened the docstring to stop asserting more
confidence than the known-issues entry actually supports, rather than
writing speculative HAT-specific integration code that can't be tested
in this dev sandbox — same discipline already applied to 11.3b/11.6.

**What's actually buildable and verifiable now, picked as the highest-
leverage improvement**: the tool-registry itself had a real, structural
scaling problem. Every prior round of registry growth this project has
done found a live-model-only bug (5.7-5.9's gating gaps, 5.15's
`calculate_subnet` cross-schema interference) — and the root cause of
5.15's bug specifically was that `modules/assistant/module.py`'s
`build_chat_request()` attached **every** registered tool (47 by then)
to **every** action-request message, unconditionally, regardless of
relevance. That's not just token overhead — it's unbounded interference
risk that gets strictly worse every time the registry grows, with no
ceiling in sight.

**Fix: domain-scoped attachment.** `AssistantAction` gained a `domain`
field (e.g. "alarms", "inventory", "security", "expeditions", "projects"
— all 47 existing actions assigned one). `AssistantActionRegistry.
matching_actions(prompt)` (`core/assistant_actions.py`) replaces the old
"attach everything if anything gates open" behavior: it attaches only
the small always-on `system` domain (6 generic/cross-cutting actions —
`open_module`, `get_system_health`, `recall_recent_activity`,
`get_device_profile`, `set_theme`, `list_profiles`) plus whichever
domain(s) the prompt's own trigger phrases actually matched. Critically,
both members of every collision pair this project already solved
(`open_module`/`set_theme`, `list_profiles`/`get_device_profile`) live
in the same `system` domain specifically so they keep getting attached
together, exactly as before — this change narrows *which* tools get
offered, never discards a previously-solved disambiguation case.
`is_action_request` itself is unchanged (`bool(matching_actions(...))`
is mathematically identical to the old flattened-keyword check), so
`looks_like_action_request()`/`gating_keywords()` and every existing
gating test stay exactly as they were — this is purely a scoping change
on top of unchanged gating semantics.

**Found and fixed a real, previously-latent bug while verifying this
change** — not a regression it introduced, but a gap domain-scoping
finally exposed: `scan_ports`'s own trigger phrases never actually
covered its own golden-set prompts ("Scan 192.168.1.1/10.0.0.1 for open
ports"). That only ever "worked" before because gating happened to open
via `open_module`'s unrelated bare `"open "` trigger, which used to drag
in the *entire* 47-tool registry (including `scan_ports`) regardless of
which trigger actually fired. Added `"for open ports"` as an explicit
trigger. This is exactly the kind of masked gap this whole change was
meant to surface — previously silent, now impossible to hide behind
"attach everything."

**Measured result**: average 9.9 tools attached per action-request
prompt across the full golden set (max 17, min 6) — down from a flat
47 every time. 60/60 on two independent live-model runs after the fix,
847 tests passing, real headless-Qt smoke test confirming `build_chat_request()`
returns a 9-tool subset for a real alarm request through the actual
`AssistantModule` (not just the golden-set script).

## Assistant safety: skip destructive tool calls bundled with other calls (built, 2026-07-14)

Found mid-experiment, while running the model-upgrade comparison
(2026-07-14, "let's continue on the AI" thread): asked "How many M3
bolts do I have?" (a pure read question, seeded with a real "M3 bolts"
inventory item), `qwen2.5:7b` returned **two** tool calls in one reply —
the correct `list_inventory`, plus a spurious `adjust_inventory_quantity`
that would have actually mutated real inventory data. `llama3.2` has
never done this once across this project's entire live-model
verification history, but nothing about `modules/assistant/module.py`'s
design prevented it: `_on_reply()` executed **every** tool call in a
reply, unconditionally, in a loop — this app was never designed or
tested for genuine multi-intent-per-message use (every registered
action assumes one atomic operation per turn), so this was a real,
model-agnostic robustness gap, not something specific to one model.

**Fix**: `AssistantAction` gained a `destructive: bool` field
(formalizing what `tests/live_model_check.py`'s `_DESTRUCTIVE_TOOLS`
tracked only informally by hand before this — that hardcoded set is
now gone, replaced by `AssistantActionRegistry.destructive_action_names()`
derived from the real registry, same "one source of truth" fix already
applied to trigger_phrases/gating_keywords in milestone 5.9). All 9
previously-informal destructive actions marked (`delete_alarm`,
`delete_note`, `delete_inventory_item`, `adjust_inventory_quantity`,
`delete_waypoint`, `delete_calendar_event`, `delete_component`,
`delete_project`, `delete_task`). New pure function
`split_safe_tool_calls()` in `modules/assistant/module.py`: a single
tool call always executes regardless of whether it's destructive (the
normal, extensively-tested case) — only when a reply bundles **more
than one** tool call are any destructive ones skipped rather than
executed, logged as a warning, and reported to the user in the chat
log so they can ask again explicitly if they actually wanted it.

Verified with a real headless-Qt smoke test reproducing the exact
qwen2.5:7b scenario end-to-end through the actual `AssistantModule._on_reply()`
(not just the pure-function unit tests): a real seeded "M3 bolts" (qty
25) inventory item, a synthetic `ChatReply` bundling
`adjust_inventory_quantity` + `list_inventory`, confirmed the quantity
stayed at 25 (destructive call correctly skipped) while the user still
received the correct "25x M3 bolts" answer from the safe call. 856
tests passing.

## Model upgrade experiment: conclusion — keep llama3.2:3b (2026-07-14)

The "model upgrade experiment" track from the AI-advancement thread
(picked over embedding-based retrieval as the lower-risk first step).
Pulled two stronger candidates within `docs/HARDWARE.md`'s stated
realistic 1-7B ceiling for the AI HAT+2, ran the full 60-case golden
set against each (properly warmed up first, one model loaded at a time
— this dev sandbox's 11GB shared system RAM is tight for a 7B model
and produced misleading fast-failure results before that fix; see the
destructive-tool-call-safety entry above for what that same experiment
run surfaced along the way):

| Model | Golden-set result | Avg time/case |
|---|---|---|
| **llama3.2:3b (current default)** | **60/60** | **2.69s** |
| qwen2.5:7b | 58/60 | 12.01s |
| mistral:7b | 17/60 | 18.75s |

**Conclusion: keep llama3.2:3b.** It isn't just "good enough" — it's
the best performer of the three on the metric that actually matters
(tool-calling correctness), and by a wide margin the fastest. Bigger
parameter count did not mean better tool-calling here: qwen2.5:7b came
close but introduced a real new failure mode (the destructive
multi-tool-call bug documented above) and ran ~4.5x slower; mistral:7b
was outright unreliable at tool-calling in this environment (mostly no
tool call at all, "got []") and ~7x slower — plausibly because Ollama's
plain `mistral:7b` tag isn't the function-calling-tuned checkpoint,
though this wasn't chased further given llama3.2:3b's clean sweep made
it unnecessary. Speed differences this large on CPU would very likely
translate to the Hailo-10H too, even setting aside the still-unverified
question of whether `hailo-ollama` runs these specific models at all
(`docs/KNOWN_ISSUES.md`'s open item) — a slower, less-accurate model
is a worse trade at any speed. `qwen2.5:7b`/`mistral:7b` left installed
locally (not removed) in case they're useful for a future, differently-
scoped experiment; not wired into any config default.

## Embedding-based retrieval: LLM query reformulation instead of a real vector index (2026-07-14)

The last item on the AI-advancement menu. Investigated the literal ask
first rather than building blind: measured the installed Reference
Library packs directly and found ~1.8 million articles total (Wikipedia
top-mini alone is 875K, iFixit 103K, Wikibooks 118K, medicine-mini
362K). Pre-computing and storing embeddings for all of that — re-indexed
on every pack install/removal via the Knowledge module — is a
multi-hour, multi-GB undertaking that belongs on Project 2's Home
compute per `docs/VISION.md`'s own established Pi-vs-Home placement
principle ("none of the compute-heavy reasoning belongs on the Pi5"),
not something to build blind on Pi-class hardware in one pass. Resolved
via `AskUserQuestion`: build the cheap, no-new-infrastructure fix now
(LLM query reformulation), flag the real embedding index as its own
future, larger, differently-placed initiative.

**Measured the actual bug directly before writing any code** — not
assumed: `search_all_packs("hypothermia symptoms")` correctly finds the
real Hypothermia article, but `search_all_packs("my hands are freezing
and numb")` (a far more natural way to actually ask this) returned
completely unrelated hits, including an iPod Touch logic board
replacement page. Direct lexical phrasing works; any natural paraphrase
fails completely — libzim's full-text index has no way to bridge
"freezing and numb" to "hypothermia" since they share no vocabulary.

**Fix**: `core/device_help_manager.py`'s new `_reformulate_query_for_search()`
asks the already-running LLM to name the single most likely encyclopedia
article title for the question (2-3 words), then `_reference_library_chunks()`
searches with BOTH the reformulated title and the original stopword-stripped
keywords, merging and deduping by (pack, article) — reformulated results
first, since they specifically target the case where the original
keywords already fail. No new index, no new dependency, reuses the LLM
connection that already exists for chat/tool-calling.

**Found and fixed a real prompt-engineering gap via live testing against
the real installed packs** (this project's own established discipline —
"expect several rounds of real-model iteration, not one"): the first
prompt asked for "2 to 5 keywords," which made results *worse* than not
reformulating at all in two of three test cases. Measured directly
against the real medicine pack: `search("hypothermia hypovolemia cold
stress shock")` (5 terms) returned **zero hits**, while
`search("hypothermia frostbite")` (2 terms) correctly ranked the real
Frostbite article #1. Same "more retrieved context isn't always better"
lesson this project already learned once for `docs/*.md` grounding
(this module's own `_SYSTEM_PREAMBLE` comment), rediscovered here for
Reference Library search terms specifically. Fixed by asking for "the
single most likely article title (2-3 words)" instead of "2 to 5
keywords" — verified this actually fixes the demonstrated failures:
"my hands are freezing and numb" and "body temperature dropping
dangerously low" both now correctly surface the real Hypothermia
article across two independent runs (temperature=0, deterministic), and
a full end-to-end `build_grounded_prompt()` + real LLM call for the
former now correctly identifies frostbite/hypothermia in its answer,
where it previously would have grounded on the irrelevant iPod snippet.

**Found and fixed a second, unrelated real data-pollution issue while
verifying this** — not caused by this feature, but caught while
auditing test isolation after the `NotificationManager` leak from the
v0.19 work above: `data/waypoints.json` had accumulated **1,860**
leaked test waypoints (all named "A"/"B"/"C"/"New York"/"Los Angeles" —
classic haversine-distance test fixture names) spanning from
2026-07-13 through 2026-07-14, across multiple prior milestones' ad hoc
verification scripts that forgot to isolate `waypoint_manager`'s data
path. Confirmed zero real user data mixed in (only 5 unique names, no
real place names/notes), reset to empty. **Lesson**: grepping for a
specific milestone's own expected leaked strings isn't sufficient to
catch pollution from an *earlier*, unrelated milestone's scratch
script — a periodic raw entry-count audit across every `data/*.json`
file (not just a targeted grep) is worth doing after any batch of
manual scratch-script verification, not only when a specific string is
suspected.

944 tests passing (31 in `tests/test_device_help_manager.py`, including
new coverage for reformulation success/failure/truncation and merge/
dedup behavior with a fake LLM — no live model needed for the automated
suite, matching this module's existing "no filesystem/Qt/LLM in unit
tests" convention).

## Aesthetic upgrade, part 1: main menu module cards (2026-07-14)

At the user's request for "a massive upgrade on aesthetics... clean and
cool." Investigated the real current state first — rendered actual
screenshots of all 4 themes via the established offscreen-Qt technique
— rather than redesigning blind.

**Found two real, pre-existing bugs by looking at the rendered
output**, neither previously caught by any unit test since neither is
visible from stylesheet-string equality checks:

1. `gui/widgets/module_button.py` built its button label as a single
   f-string (`f"{module.icon}   {module.display_name}"`) handed
   straight to `QPushButton`'s own text — Qt treats a bare `&` in
   button text as a mnemonic/accelerator marker, silently mangling
   "Workshop & Electronics" into "Workshop _Electronics" on screen.
2. A genuine Qt/PySide6 rendering bug, confirmed via careful bisection
   in a freshly-started process (an earlier bisection attempt inside a
   single long-running process gave contradictory, unreliable results —
   Qt's internal style caching across many rapid `setStyleSheet()`
   calls in one process is not a trustworthy test harness for this kind
   of investigation): a `:hover` compound selector targeting a
   *descendant* widget inside a `QPushButton`
   (`QPushButton:hover QLabel {...}`) can make that label's text vanish
   even in the non-hover state, not just fail to apply on hover. Found
   while giving the Anime Monochrome theme's module cards a white-text-
   on-black-hover treatment — worked around by not inverting to a solid
   background on hover for that element at all (a lighter highlight
   instead), rather than fighting the bug further. Re-verify on real
   display hardware before ever reintroducing this selector pattern.

**Redesigned `ModuleButton`** from a single icon+name line into a
richer card: a circular icon badge, bold module name, and a one-line
muted description — using `module.description`, which already existed
on every module but was never shown on the main menu. Both the name
and description are eagerly elided to one line (`QFontMetrics.elidedText()`,
measured against a font matching the actual QSS-applied size/weight —
an earlier attempt measured against the wrong font and silently
under-elided, clipping the ellipsis itself off-card) rather than word-
wrapped: an early word-wrapped version made every card as tall as its
longest description, and at this app's actual default 1100x700 kiosk
window size (not just a wider dev-convenience test size), that pushed
the full module list past the point of fitting without scrolling — a
real usability cost on a kiosk device, found only by rendering at the
real default size, not an arbitrary wider one. Added a
`QGraphicsDropShadowEffect` for real depth. Applied consistently across
all 4 themes (`gui/styles.py`'s Dark Field plus the other 3 in
`gui/theme_manager.py`), each with matching icon-badge/name/description
colors for its own palette.

**Also found new data-pollution during this work** (a third occurrence
this session, previously found and fixed twice already): `data/waypoints.json`
had again accumulated leaked test waypoints (same "A"/"B"/"C"/"New
York"/"Los Angeles" fixture names) from one of this session's own ad
hoc rendering/debugging scripts, not the committed test suite. Cleaned
up. **Standing lesson, now hit three times**: isolate every manager's
data path in *any* scratch script that constructs a real `AppContext`,
even ones that look unrelated to that manager (a UI/theme rendering
script has no obvious reason to touch Waypoints) — `ModuleManager.discover()`
and full `MainWindow` construction touch more of the app than a
script's own stated purpose might suggest.

944 tests passing (no new automated tests added for `ModuleButton`
itself — its Qt widget-construction logic follows this project's
existing convention of manual headless-Qt screenshot verification
rather than pytest coverage, same as every other module's `get_widget()`).

## Aesthetic upgrade, part 2: header bar + character panel (2026-07-14)

Continuation of part 1, confirmed by the user via an explicit "keep
going" rather than pausing. Same investigate-then-render-then-verify
approach, applied to the two remaining plain/undecorated areas found by
reading `gui/main_window.py`'s `_build_header()`: all 5 header buttons
(Back, Main Menu, Switch User, Search, Notification bell) had no object
names and no theme-aware QSS at all — just whatever generic QWidget
look Qt falls back to.

**Header bar**: gave every header button one shared `#HeaderButton`
object name, scoped in QSS to `QFrame#HeaderBar QPushButton#HeaderButton`
so the rule can never leak onto an unrelated button elsewhere in the
app. Added matching padding/border/hover/pressed/disabled treatment to
all 4 themes. The unread-notification bell gets its own accent state via
a dynamic Qt property (`hasUnread`, toggled in
`_update_notification_badge()` alongside its existing text-count logic)
and a `[hasUnread="true"]` QSS attribute selector, rather than a second
object name — this needed an explicit `style().unpolish()`/`.polish()`
call after `setProperty()`, since Qt caches a widget's QSS
property-selector match and won't silently re-evaluate it on every
property change. Also grouped the title + greeting into their own
`QVBoxLayout` for a tighter, stacked look instead of two labels floating
side by side.

For Anime Monochrome specifically, `HeaderButton` safely uses the
theme's usual solid black/white hover invert (`QPushButton#HeaderButton:hover`)
— unlike `ModuleButton`, this button's label is its own text, not a
child `QLabel`, so the descendant-selector rendering bug documented in
part 1 doesn't apply here. Left an explicit comment on why the two
buttons' hover treatments differ, so a future edit doesn't "fix" one to
match the other and reintroduce that bug.

**Character panel**: `gui/character_panel.py` had one remaining
`setStyleSheet("font-size: 48px;")` inline call on its icon label — a
holdover that violated this project's own QSS-cascade convention (every
other widget pulls its look from the QApplication-level stylesheet;
per-widget `setStyleSheet()` breaks the cascade for that widget and its
children). Replaced with a `#CharacterIcon` object name, a fixed 96x96
circular badge (same treatment as `ModuleButton`'s icon badge from part
1) styled per-theme, and a `QGraphicsDropShadowEffect` on the panel
itself. Changed the panel's border from dashed to solid across the
themes that had it dashed (Dark Field, Colored) — dashed read as an
unfinished placeholder outline now that the panel has real content
inside it.

**Found and fixed the actual root cause of this session's repeatedly-
recurring `data/waypoints.json` pollution** (previously hit 3 times and
each time misattributed to "some ad hoc rendering/debugging script,"
never pinned down): `tests/test_trip_manager.py`'s `isolated_paths`
fixture only patched `trip_manager` module's `_DATA_DIR`/`_TRIPS_FILE`,
never `waypoint_manager`'s — but its own `_make_context()` helper
constructs a real `WaypointManager(context)` for the route/distance
tests, which several tests then call `add_waypoint()` on with the exact
"New York"/"Los Angeles"/"A"/"B"/"C" fixture names seen leaking all
session. Every single `pytest` run was silently writing 20 fresh
waypoint entries straight into the real, production `data/waypoints.json`
— not any of the many one-off scripts written during this session's
aesthetic work, which were the innocent bystander each time. Fixed by
adding the missing `waypoint_manager` monkeypatch to that one fixture;
reset `data/waypoints.json` to `[]` and confirmed a full `pytest` run no
longer touches it.

944 tests passing. No automated tests added for the header/character-
panel QSS itself, same manual-screenshot-verification convention as
part 1 — rendered and visually confirmed all 4 themes at the app's real
1100x700 default window size.

## Aesthetic upgrade, part 3: Home dashboard, Apps folder, icon restyle (2026-07-14)

The user's own follow-up framing after using the app: "after logging in
the menu should display a dashboard with some info like the systems
power, the current mission, the time, currently playing song, volume
control... everything should have more of a bubble outline icon
look... all of the menu items shown now could be in a separate
container like an apps folder." Scoped via `AskUserQuestion` first
(same convention as every other multi-part vision ask this project has
taken on) rather than guessing at the two pieces with no real backing
data in this codebase:

- **Volume control**: nothing like this existed anywhere in the
  codebase, and this dev sandbox has no `amixer`/`pactl`/`wpctl` binary
  to shell out to either — confirmed the same "blocked, not just
  untested" way as 11.5's nmap/hashcat. User chose: build it for real
  (targeting Pi audio hardware), accept it's unverified here. New
  `core/volume_manager.py` — same `VolumeBackend` Protocol / concrete-
  backend split as `core/power_manager.py`, `AmixerVolumeBackend`
  shelling out to ALSA's `amixer` CLI (no Python audio binding, so it
  doesn't hit the `libpulse`/`libportaudio2` wall that blocked Media/
  Voice at the time — both are resolved as of 2026-09-09, see the
  Music module built as v0.20). `parse_amixer_output()` is a pure function, unit-tested
  against captured sample `amixer` text without needing the real
  binary. Flagged in `docs/KNOWN_ISSUES.md` alongside the existing
  Security Toolkit entry, not silently assumed to work.
- **"Currently playing song"**: zero real data source (Music is a bare
  placeholder module, no playback). User chose: omit entirely, same
  call `modules/dashboard/module.py` already made for the same reason.

**New `gui/home_dashboard.py`** — the screen shown immediately after
login, not `modules/dashboard/module.py` (that's a different, detailed
aggregation page reachable from Apps like any other module; this one is
a glanceable always-visible home screen). Live clock, a Power card
(`context.power`), a Mission card (first active Mission + objective
progress, `context.missions`), and a Volume card (slider + mute toggle,
disabled with a "Not available on this device" note when
`VolumeManager.is_available()` is `False` — same graceful-degradation
UI pattern the Power module already uses for "no battery detected").
All formatting logic (`format_clock_time`/`format_clock_date`/
`format_power_line`/`format_active_mission_line`/`format_volume_line`)
is pure and unit-tested (`tests/test_home_dashboard.py`), same split as
every other module's `format_*` helpers in this codebase.

**The Apps folder**: `gui/main_window.py`'s existing `_build_menu()`
(the module grid) moved out of being the landing screen — it's
unchanged code, just no longer the default view. The header's old
single "⌂ Main Menu" button split into two: "🏠 Home" (new
`show_home()`, publishes a new `"home.shown"` event) and "▦ Apps"
(the pre-existing `show_main_menu()`, deliberately left un-renamed so
its already-working `"menu.shown"` event and
`gui/character_panel.py`'s existing reaction to it kept working with
zero changes). `gui/character_panel.py` gained a matching Home
reaction (`_HOME_ICON`/`_HOME_LINE`, "Welcome home.") and now defaults
to it on construction, since Home — not the Apps grid — is what's
actually on screen first now.

**Icon restyle — "bubble outline" look**: presented three concrete
visual directions via `AskUserQuestion` with ASCII previews (filled
bubble refined, outlined ring with soft fill, outlined ring with
transparent center) since this was too ambiguous to build sight-unseen;
user picked the plain outlined ring. Changed `#ModuleButtonIcon` and
`#CharacterIcon` from a filled-background circle to a transparent-
center circle with a colored ring border, across all 4 themes
(`gui/styles.py` + `gui/theme_manager.py`), plus matching new
`#DashboardSectionIcon` badges for the three Home cards — one visual
language reused everywhere an icon badge appears now, not three
independent looks. Also styled `QSlider` for the first time in this
codebase (groove/handle/disabled state per theme) — left unstyled, it
would have fallen back to the native OS look, the same invisible-on-
this-background risk `gui/styles.py`'s own `QCheckBox` comment already
warned about for a different widget.

968 tests passing (23 new: `tests/test_volume_manager.py`,
`tests/test_home_dashboard.py`). Rendered and visually verified all 4
themes at the real 1100x700 default window size, both the new Home
screen and the Apps grid, with a real seeded active Mission and real
`psutil` battery data (this WSL dev sandbox reports a real "100% —
Plugged in" desktop-style battery status) to confirm the cards render
real data, not just their empty-state fallback text.

## Aesthetic upgrade, part 4: Assistant moves into the character panel (2026-07-14)

Follow-up to parts 1-3, after the user actually used the app and gave
concrete feedback: "the section on the right of the screen with the
robot icon would be a perfect spot for the Assistant Conversations,"
the Assistant should recommend questions it's good at answering, and
"I still feel like the assistant is not very helpful with using the
program." Scoped via `AskUserQuestion` first (keep both chat surfaces;
suggestions contextual to the current screen; fix the help-content
root cause too, not just the UI).

**Refactor first, to respect the app's own layering rule.** `gui/` may
import `core/` directly but must never import `modules/`
(CLAUDE.md's one-directional layering) — so before any sidebar chat
could exist, the pure request-building logic and the two `QThread`
workers `modules/assistant/module.py` owned had to move to `core/`:
new `core/assistant_chat.py` (`format_chat_line`/`split_safe_tool_calls`/
`looks_like_action_request`/`build_chat_request`, pulled out verbatim,
not reimplemented) and `core/chat_worker.py`/`core/tts_worker.py`
(same precedent as `core/push_to_talk_trigger.py` already living in
core/ despite CLAUDE.md's general "no threading in core" note, since
none of these do any actual widget/rendering work). `modules/assistant/module.py`
now imports from `core/` instead of owning these directly; its own
docstring documents the split. Test files renamed/updated to match
(`tests/test_assistant_module.py` -> `tests/test_assistant_chat.py`).

**Root cause found and fixed for "the assistant isn't very helpful":**
`core/device_help_manager.py` was grounding every "how do I..." question
on `docs/*.md` — this project's own *developer* documentation
(architecture notes, module-writing spec, roadmap phase status). A real
user asking "how do I plan a trip" got back chunks about internal
module folder structure, not usage help, because that was the entire
corpus available. Fixed by writing a genuine end-user-facing help
corpus, `docs/user_help/*.md` (10 files: getting_started, assistant,
expeditions, missions, navigation, organizing, field_kit, knowledge,
home_and_power, settings — plain language, one file per feature area)
and repointing `_DOCS_DIR` at it; `docs/*.md` itself is no longer
indexed at all. **Verified against the real running Ollama model, not
just retrieval-in-isolation**: "How do I plan a trip in this app?" went
from would-have-been dev-docs noise to a correct, concrete, step-by-step
answer citing the real Assistant phrasings. Along the way, found and
fixed a real ranking bug the same live check surfaced: near-identical
"## Asking the Assistant" boilerplate footers repeated across most of
the new files out-scored `assistant.md`'s own dedicated overview
section for the query "what can the assistant help me with," because
`score_chunk()` weighs heading-word matches double and those footers'
heading literally contained both query words — fixed by deleting the
redundant footers (assistant.md is now the one canonical place for
"what to ask") and retitling assistant.md's own overview heading to
directly match that phrasing. Also tightened `_SYSTEM_PREAMBLE` to stop
the model from emitting markdown-link-style citations that would have
rendered as ugly literal text in a plain `QPlainTextEdit` chat log —
re-verified against the real model that this didn't regress the
existing "what does the notes module do" confident-match case (a
longer preamble broke exactly this case once before, per this file's
5.6 writeup). Full 67-case golden set (`tests/live_model_check.py`)
still 67/67 after both changes.

**The sidebar chat itself**: `gui/character_panel.py` now has a
compact, text-only chat (no mic/TTS — the full `modules/assistant/module.py`
screen in Apps keeps voice, for a larger, focused session) built on the
newly-shared `core/assistant_chat.py`/`core/chat_worker.py`, so the two
surfaces can never silently drift apart in behavior. Above the input
box, a handful of clickable suggested-prompt buttons change based on
whatever screen is currently active — new `core/assistant_chat.py`
functions `suggested_prompts_for_module()`/`MODULE_ID_TO_DOMAINS`/
`DOMAIN_EXAMPLE_PROMPTS` (a small curated dict, same shape as this
file's sibling `MODULE_REACTIONS`), keyed off the same "module.opened"/
"home.shown"/"menu.shown" events the panel's reactive icon already
subscribed to. **Found a real rendering bug via screenshot, not
apparent from the code**: refreshing the suggestion buttons via the
usual `takeAt()` + `deleteLater()` clear-a-layout pattern (already used
elsewhere in this codebase, e.g. `modules/dashboard/module.py`) left
the *previous* screen's stale buttons visibly overlapping the new,
often-shorter list — `deleteLater()` only schedules the widget's actual
destruction, it doesn't hide it immediately, and `takeAt()` alone only
detaches it from the *layout*, not from the screen. Fixed by calling
`hide()` + `setParent(None)` immediately before `deleteLater()`. Worth
rechecking this exact pattern anywhere else in the codebase that clears
and repopulates a layout, if a similar ghosting bug ever gets reported.

Verified end-to-end against the real running Ollama server (not just
mocked): clicked a suggestion button, watched it round-trip through the
real `ChatWorker`/LLM and post a real reply in the sidebar log, then
switched to the Missions module and confirmed the suggestions correctly
changed to Missions-specific prompts. 973 tests passing (10 new in
`tests/test_assistant_chat.py` for `suggested_prompts_for_module()`).
Rendered and visually verified all 4 themes.

## Aesthetic upgrade, part 5: persistent memory, ChatGPT-style conversations, a companion personality (2026-07-14)

The user actually used part 4's sidebar chat and came back with the
next real ask: persistent, self-titled conversation logs (review/
delete/continue, "very much like using ChatGPT"), a visible/editable
store of what the Assistant remembers about the user, and a warmer
personality — "like a researcher dedicated to understanding and
discovering every aspect it can about the user," celebrating wins,
comforting, encouraging growth, "like a lifelong friend." Also asked
for birthdays, anniversaries, and check-ins specifically. This is the
single largest Assistant change this project has made in one pass —
new persistence layer, a rebuilt prompt-assembly pipeline, a two-pane
UI rewrite, and three new proactive-notification mechanisms.

**The concrete bug that motivated the persistence work**: tested
live before writing any code — "My name is Alex and I love hiking in
the Cascades" followed by "What's my name, and where do I like to
hike?" got *"I don't know your name... I don't have any information
about that."* Every prior chat turn (parts 1-4 included) was a single
stateless message with zero conversation history — a real, demonstrated
"not seamless" bug, not a hypothetical one.

**New persistence layer**: `core/conversation_manager.py`
(`Conversation`/`ConversationMessage`, auto-titled once an LLM call
summarizes the first exchange, one "active" conversation shared by both
chat surfaces via `get_or_create_active_conversation()`/
`set_active_conversation_id()`, publishing `"conversation.updated"` on
any content change and a distinct `"conversation.active_changed"` when
the pointer itself moves — the two had to be separate events so a
widget can tell "my current conversation's content changed" apart from
"you're looking at a different conversation entirely now") and
`core/user_memory_manager.py` (`UserMemory`, simple case-insensitive
dedup on `add_memory()`). Both are the same persisted-JSON manager
pattern as every other `core/*_manager.py` in this codebase, fully unit
tested.

**Prompt-assembly rewrite** (`core/assistant_chat.py`): `build_chat_request()`
now sends bounded real history (`trim_history()`, 12 messages/6
exchanges) and a proper system-role message
(`build_system_message()`) instead of one bare user string. The
identity/personality text is **only added to the information-question
path, not the action-request one** — this project has a documented,
measured regression from a *longer* preamble before
(`core/device_help_manager.py`'s `GROUNDING_INSTRUCTION` docstring), and
the 67-case tool-calling golden set is the most fragile, most-tested
surface in this codebase; the user never sees the action path's system
message anyway; adding personality text there was pure risk for zero
benefit. Verified: full golden set stayed **67/67, then 68/68** after
adding a `set_birthday` case, and the Alex/hiking scenario now correctly
recalls both facts across turns.

**Memory extraction was the hardest part to get right, and needed
several rounds of live-model iteration** (exactly the discipline this
project has learned to expect, not skip):
1. First attempt included the assistant's own reply in the extraction
   prompt — 100%-reproducible failure (not sampling noise): the model
   concluded "no new facts" even when the user's message plainly stated
   a name and a hobby in the same breath. Fixed by extracting from the
   user's message alone.
2. Widening the prompt to combat that then caused active hallucination
   — the model invented a birth date, a relationship status, and a
   "daily routine" that were never said, and guessed the user's gender
   inconsistently (he/she) across otherwise-identical prompts. Fixed
   with an explicit "never guess/infer anything not stated, use 'the
   user' instead of pronouns" instruction, and a bias toward missing a
   real fact over fabricating one — for a memory feature, a false
   negative is far safer than a false positive.
3. The model also doesn't reliably reply with the literal "NONE" it's
   asked for — it sometimes paraphrases the same conclusion as a full
   sentence, which would otherwise get stored as if it were a real
   memory. `parse_extracted_memories()` got a hedge-phrase rejection
   list as a belt-and-suspenders safety net on top of the prompt's own
   instruction, same "don't trust the model to follow format
   instructions perfectly" caution as `core/llm_manager.py`'s
   `_looks_like_malformed_tool_call()`.

**ChatGPT-style two-pane rebuild of `modules/assistant/module.py`**:
left-hand conversation list (`gui/widgets/conversation_card.py`'s
`ConversationCard`, same "no text of its own, QLabel children instead"
shape as `ModuleButton` — auto-titled, click-to-continue, delete via the
existing `gui/delete_confirm_dialog.py`) plus a "🧠 Memories" button
opening `gui/user_memory_dialog.py` (review/delete individual memories,
Clear All). Neither this screen nor `gui/character_panel.py`'s sidebar
own a local transcript anymore — both are live views over
`ConversationManager`, re-rendering on its events, which is what keeps
them showing the same conversation without a direct reference to each
other.

**Found a genuinely new Qt rendering bug via screenshot, not obvious
from the code, that cost real time to bisect**: `ConversationCard`'s
title/meta text silently failed to paint once placed inside the
conversation list's `QVBoxLayout` — geometry/text/visibility all
reported correct, but nothing rendered, exactly like part 4's
suggestion-button ghosting bug but with a different root cause.
Bisected by bringing in a known-good comparison (`ModuleButton`,
copy-pasted into the same minimal repro scaffold) rather than
staring at `ConversationCard` alone — the one difference that mattered
was `ModuleButton.setMinimumHeight(72)`. Every offscreen-QPA render this
whole session has logged "This plugin does not support
propagateSizeHints()"; this is almost certainly that limitation made
concrete — a custom `QPushButton` relying purely on its children's
natural `sizeHint()` (no explicit minimum size) can get laid out with a
collapsed height on this platform before its content ever paints.
Fixed with `setMinimumHeight(60)`; re-verify on real display hardware,
and reach for an explicit minimum height on any future custom card
widget rather than assuming content-driven sizing "just works" here.

**Companion features**, the parts of the ask beyond persistence/UI:
- `core.profile_manager.Profile` gained an optional `birthday` field,
  set conversationally via a new `set_birthday` Assistant action (no
  new form UI — Settings doesn't edit profile fields at all yet) and
  injected into every info-question system message alongside free-text
  memories (`build_user_context_block()`).
- New `core/daily_occasions.py` (pure logic) + a 5-minute
  `_daily_occasion_timer` in `core/application.py` (same
  always-alive-for-the-session pattern as the existing alarm/power
  timers): celebrates the active profile's birthday, digests today's
  Calendar events, and — deliberately gated to evening only
  (`should_send_checkin()`) so opening the app at 6am doesn't
  immediately get scolded for "not having chatted yet" — a gentle
  check-in notification if there's been no conversation activity that
  day. Each of the three has its own independent "already ran today"
  date tracker, since they don't share a firing condition.
  **"Anniversaries" reuse the existing Calendar module rather than
  being a new concept** — Calendar has no recurrence yet, a real,
  separate gap flagged in `docs/KNOWN_ISSUES.md`, not silently assumed
  to work indefinitely.
- `core/mission_manager.py`'s `increment_tally()`/`update_mission()`
  now fire celebratory notifications when an objective, all of a
  mission's objectives, or the whole mission newly become complete —
  living in the manager itself (not the Missions module UI or the
  Assistant's own action handlers) so every path to completion
  celebrates uniformly.

1069 tests passing (86 new). Full 68-case live-model golden set
passing. Rendered and visually verified all 4 themes. No data
pollution (one real near-miss this pass: a scratch verification script
forgot to isolate `config_manager`'s `_CONFIG_FILE` and created a real
`config/config.json` with a scratch `assistant.active_conversation_id`
— caught immediately by its mtime matching the test run exactly,
cleaned up).

## Companion philosophy: Startup Dashboard Briefing (built, 2026-07-15)

At the user's explicit request, `docs/VISION.md` gained a large
companion-philosophy update (voice-first design, intelligent UI
navigation, proactive suggestions, multi-platform architecture, and a
long list of new subsystems — Memory Palace, Workout, Kitchen, Finance,
Relationship/Pet Profiles, onboarding, tutorials, self-knowledge). Given
the scope, the user was asked via `AskUserQuestion` which piece to build
first rather than guessing at sequencing; they picked the **Startup
Dashboard Briefing** — the lowest-new-design-risk slice, since it's
aggregation over data that already exists (the same five sections
`modules/dashboard/module.py` already lists), same reasoning that put
Memories first in the 2026-07-14 vision update.

New `core/startup_briefing.py` (pure functions, no Qt/manager coupling,
same shape as `core/daily_occasions.py`): `greeting_for_hour()` (time-
of-day greeting), `build_stat_highlights()` (turns raw counts into short
phrases, skipping any that are zero), `build_startup_briefing()`
(assembles the final greeting sentence). **Deliberately template-based,
not an LLM call** — this runs once at every app launch, and boot-time
latency (or Ollama not being warmed up yet) is a worse trade-off than a
scripted-but-warm sentence; same "start boring, not clever" principle
`docs/VISION.md` already applies to Continuous Learning. Wired into
`gui/home_dashboard.py` as a new banner card above the existing Power/
Mission/Volume cards, computed once at `HomeDashboard` construction
(i.e. once per login/launch, not on the 5s data-refresh timer — this is
a "welcome back" greeting, not a live ticker), summarizing active
missions, today's calendar events, unread notifications, active
projects, and the most recent Memory. New `#DashboardBriefingText` QSS
rule added to all 4 themes.

**Weather, workout recommendations, financial updates, and smart home
status are named in the original companion-philosophy ask but have no
real module/data source yet** — omitted, same "don't build fake data"
discipline as the dashboard's already-documented missing "currently
playing song." The user separately flagged that the dashboard is
expected to keep growing as more of the vision ships — `_build_briefing_text()`
in `gui/home_dashboard.py` is the one place to extend with new
`context.*` sources as they land, and `build_stat_highlights()` takes
plain counts specifically so new sources slot in without restructuring
it.

Verified: 13 new pure-logic tests (`tests/test_startup_briefing.py`),
1082 tests passing total, no regressions. Rendered and visually
verified via a real headless-Qt screenshot in both `dark_field` and
`anime_monochrome` (the theme with a prior real text-visibility bug) —
banner text fully legible in both, no layout issues. No data/config
pollution (scratch render script isolated every manager's data dir and
`config_manager`'s `_CONFIG_FILE` up front, per the gotcha immediately
above).

## Companion philosophy: MIA speaks — spoken startup briefing + selectable voices (built, 2026-07-15)

Immediate follow-up to the Startup Dashboard Briefing above, at the
user's explicit request: "we need to get MIA talking... I want this
startup to be a spoken thing. Also I want to be able to pick through
different voices for MIA"

**Spoken briefing**: `gui/home_dashboard.py`'s `_speak_briefing()` runs
the greeting text through `core/tts_worker.py`'s existing fire-and-
forget QThread pattern (same one `modules/assistant/module.py` already
uses for spoken Assistant replies) once, right after construction.
Degrades silently (logged) if TTS/PortAudio isn't available, same
graceful-degradation stance as everything else Voice-adjacent in this
project.

**Selectable voices**: new `core/voice_catalog.py` — a curated,
hand-picked 5-voice `VOICE_CATALOG` (Lessac/Amy/Ryan — US — and
Alan/Southern English Female — British), not Piper's entire library,
same "curated, not exhaustive" discipline as the 4-theme system.
`core/voice_manager.py`'s `VoiceManager` gained `current_voice_id`,
`list_available_voices()` (only catalog entries whose `.onnx` file is
actually present in `voice_models/` — a fetch isn't guaranteed to have
run), and `set_voice()` (switches the live `PiperBackend` instance and
persists `voice.tts_voice_id` to config, same "manager owns its own
persistence" convention as every other core manager). The legacy
`voice.tts_model_path` override still wins if explicitly set.
`deploy/download_voice_models.sh` now fetches all 5 catalog voices
(hand-kept in sync with `core/voice_catalog.py`, since bash can't
import the Python module directly) — actually run in this dev sandbox
this session to verify for real, not just against mocks (confirmed:
network access works here; all 5 `.onnx`/`.onnx.json` pairs fetched,
~63MB each).

New Settings UI: `modules/settings/module.py` gained a "Voice" section
— a dropdown over `list_available_voices()`, calling `set_voice()` and
immediately speaking a short preview line ("Hi, I'm MIA This is what
I sound like.") through a new `TTSWorker` instance on selection, so a
voice change is *heard*, not just silently saved — same "make the
change felt, not just logged" instinct as `set_theme`'s live re-apply.

**Verified for real, not just against mocks**: constructed a real
`VoiceManager` against the actual downloaded models — `list_available_voices()`
correctly found all 5, `set_voice("en_US-amy-low")` switched and
persisted (confirmed surviving a fresh `ConfigManager()` reload,
simulating an app restart), and synthesizing the same sentence through
two different voices produced genuinely different audio byte content
(89,644 vs. 110,124 bytes) — not a stale/cached backend silently
reusing the old voice. Also drove a real `HomeDashboard` construction
end-to-end: confirmed the TTS `QThread` actually starts, synthesizes
the real briefing text to a 171KB wav file, gracefully logs and no-ops
on `play()` (no PortAudio in this sandbox — see the new
`docs/KNOWN_ISSUES.md` entry), and cleans up its worker reference on
finish with no crash. Rendered `modules/settings/module.py`'s new Voice
dropdown via a real headless-Qt screenshot — all 5 display names appear
correctly, consistent styling with the rest of the screen.

11 new/updated tests (`tests/test_voice_manager.py`), 1085 tests
passing total, no regressions. **Actual speaker output remains
unverified** — Piper synthesis itself is real and confirmed, but
whether it sounds *good* through a real speaker needs real Pi hardware,
flagged in `docs/KNOWN_ISSUES.md` rather than assumed.

## Self-knowledge gap: the Assistant didn't know it could speak (fixed, 2026-07-15)

Found live, by the user, immediately after the voice work above: asked
"Can you speak?" and the Assistant answered "I don't know how to speak
in the classical sense... I'm a text-based AI" — technically true of the
model itself, but wrong for what MIA actually does, since the full
Assistant module speaks every reply via the `TTSWorker` pipeline that
already exists. Root cause: `core/assistant_chat.py`'s system prompt
never mentioned voice output at all — the model only knows what's
written into its own system message, it doesn't discover new
capabilities on its own. This is the first concrete instance of
`docs/VISION.md`'s companion-philosophy "self-knowledge" principle
being a real, structural gap, not a hypothetical one: every future
capability (Memory Palace, Workout, Kitchen, ...) will need to be
explicitly taught to the model the same way, or it'll confidently deny
things it can actually do.

Fixed by adding one sentence to `_IDENTITY_WARMTH` (not `_IDENTITY_LINE`)
in `core/assistant_chat.py` — deliberately the info-question-only
constant, never the one shared with the action-request path, so the
68-case tool-calling golden set's system message stays byte-for-byte
unchanged. Verified two ways: a direct live-model call showing the
answer flipped from denial to "Yes, I can talk to you through this
interface..."; and a full `tests/live_model_check.py` run confirming
**68/68 still passing**, no regression on the fragile tool-calling
surface. 1085 tests passing (no test changes needed — nothing asserts
the info-question system message's literal content).

Also investigated the same session: user reported the spoken briefing
sounded "super quiet" or possibly didn't play at all. Directly measured
the actual synthesized WAV's peak amplitude — 100% of full 16-bit
scale, not a quiet signal — ruling out Piper/MIA's own synthesis as
the cause. Most likely a system-level volume setting (Windows volume
mixer for the WSL audio session, or WSLg's own passthrough gain), not
an app bug; flagged to the user rather than guessed at further, since
it's outside what this sandbox can directly verify (see the PortAudio
entries in `docs/KNOWN_ISSUES.md` for the broader "can't verify real
speaker output here" limitation this falls under). Separately confirmed
`libportaudio2`, once actually installed, resolves the *import*
failure but this specific sandboxed tool-execution context still has
zero audio devices (`sd.query_devices()` returns empty,
`Error querying device -1` on playback) — a distinct, narrower gap than
originally documented, updated understanding but same practical
conclusion: real speaker verification needs a real interactive/hardware
session, not this one.

## Notification popup theming fix + Home dashboard widget framework "part 1" (built, 2026-07-15)

At the user's request: fixed a real, long-standing bug where
`gui/notification_toast.py`/`gui/notification_center.py` predated the
4-theme system (milestone 13.2) and still called their own
`setStyleSheet()` with a hardcoded dark-only background — notification
popups looked wrong (and identical) regardless of the selected theme.
Fixed the idiomatic way this app already uses elsewhere (the header
bell's `hasUnread` accent): an object name (`#NotificationCard`,
reusing `#DashboardCard`'s per-theme background) plus a `level`
dynamic property so each theme's own QSS drives the level-accent
border color. No inline `setStyleSheet()` left on either widget.
Verified with real screenshots across all 4 themes.

**Then, the start of a much larger ask** — the user wants a
"JARVIS-level dashboard": more widgets (trading bot graphs, weather,
music, current project), the ability to add/remove/reorder them, and
eventual Assistant integration. Scoped via `AskUserQuestion` before
building anything (trading bot is an existing external system, not
something to build here; online-dependent widgets should degrade
gracefully offline rather than block, matching the Core/Home hybrid
decided earlier the same session; build order is framework-first, then
easy real-data widgets — all three the recommended option).

**Built "framework first"**: new `core/dashboard_widgets.py`
(`WidgetDescriptor` + `DashboardWidgetRegistry`) — deliberately mirrors
`core/module_manager.py`'s enable/disable/event-publish convention
(`is_enabled()`/`set_enabled()`, a `dashboard.disabled_widgets` config
list, a `"dashboard.widgets_changed"` event) rather than inventing a
second convention for what's structurally the same problem. `gui/`
still owns the actual widget rendering (same core/gui split as
ModuleManager vs. MainWindow) — `gui/home_dashboard.py`'s
Power/Mission/Volume cards are now *registered widgets themselves*,
not hardcoded, proving the framework with real production code rather
than a toy example. New `gui/dashboard_customize_dialog.py`: a
checkable, reorderable list (up/down buttons, not drag-and-drop —
matches this project's own "start boring" discipline) that toggles/
reorders widgets live, no restart. First new widget built to prove the
framework handles genuinely new data, not just the pre-existing three:
**Current Project**, a simple `context.projects`-backed card.

**Found and fixed a real Qt bug via a live headless-Qt test, not
assumption**: the first version of the live-rebuild logic tried to
detach/replace the container's `QGridLayout` object itself between
rebuilds (reparenting the old layout onto a throwaway widget) — this
silently left the container with *no* live layout at all after the
first rebuild: `_widget_bodies` correctly tracked all 3 remaining
widgets, but the screenshot showed a completely blank grid. Fixed by
keeping one `QGridLayout` instance alive for the container's whole
lifetime and clearing/refilling it in place instead of replacing the
layout object. A second, separate bug then surfaced the same way:
newly-added widgets reported `isVisible()=False` and a default
unlaid-out size (`640x480`) after a rebuild triggered on an
*already-shown* parent — Qt doesn't reliably auto-show a widget added
to a layout after the parent's already visible, at least not on this
platform. Fixed with an explicit `widget.show()` after each
`addWidget()` call. Both bugs were only visible via a real screenshot
+ widget-state dump, not from reading the code — consistent with this
project's whole history of Qt bugs that don't show up any other way.

Verified end-to-end via a real headless-Qt test: default view renders
all 4 widgets correctly (including live real project data — "Garage
Rewire [Active] (+1 more active)"), disabling a widget through the
dialog's logic actually removes it and the remaining widgets re-flow
live, and the change persists (`is_enabled()` reflects it, config
`dashboard.widget_order` saved). 1098 tests passing (13 new — 10 for
`core/dashboard_widgets.py`, 3 for `format_current_project_line()`).

**Not built yet, deliberately** — this was "framework first" only:
the trading bot widget (needs connection details from the user's
existing bot), weather widget (needs the online-optional design
pattern actually implemented, not just decided), music (Music module
is still a placeholder), and any Assistant-widget conversational
integration. Each is its own scoped piece of work on top of this
framework, not blocked by it.

## Widget interaction menus (built, 2026-07-15)

Immediate follow-up, picked via `AskUserQuestion` as the next piece of
the JARVIS-dashboard work over the trading bot/weather widgets
(scoping those needs details/decisions not settled yet) — the "menus
for interacting with widgets" half of the original ask.

`gui/home_dashboard.py` gained `_build_widget_header()`, a shared
icon+title+stretch+optional-"⋯"-menu row now used by both
`_build_simple_card()` and `_build_volume_card()` (previously
duplicated inline in each). Power/Mission/Current Project each got one
real menu action — "Open Power"/"Open Missions"/"Open Projects" —
reusing the *exact* navigation mechanism the Assistant's own
`open_module` action already uses (`"assistant.open_module_requested"`
on the event bus, handled by `gui/main_window.py`'s `open_module()`):
a widget menu click and a chat command now both go through the same
one path, not two. **Volume deliberately got no menu** — it already has
a dedicated mute button and no related module to open, and a "⋯" menu
with only a redundant "Toggle Mute" item would be worse than no menu
at all; not every widget needs one.

Verified for real, not just visually: a headless-Qt test found the
Mission widget's actual `QPushButton`, retrieved its attached `QMenu`,
triggered the "Open Missions" `QAction` directly, and confirmed the
real `"assistant.open_module_requested"` event fired with
`module_id="missions"` — the same call a live click would make, not a
mocked shortcut. Also confirmed via the same test that exactly 3 menu
buttons exist (Power/Mission/Current Project), not 4 — Volume's
absence is intentional, not a bug. 1098 tests passing, no regressions
(this was a UI-only change with no new pure-logic function, so no new
pytest cases — covered by the existing widget-framework tests plus
this live verification).

**Known limitation carried forward, not fixed here**: "Open Projects"
navigates to the Toolbox module generally, not directly to the Project
Manager tool tab within it — `gui/main_window.py`'s `open_module()`
has no deeper per-tool navigation for Toolbox the way Files' own
`navigate_to_path()` does. Acceptable for now; revisit if it's ever
worth a dedicated deep-link mechanism.

## AI Voice Effect (built, 2026-07-15)

At the user's explicit request: "upgrade MIA's voice" to sound like
"a futuristic awesome AI companion device," not a plain human voice.
Investigated what's actually tunable first — Piper's own
`SynthesisConfig` (`length_scale`/`noise_scale`/`noise_w_scale`) only
affects pace/expressiveness, not timbre, so it couldn't deliver a
"futuristic" character on its own. The real lever is post-processing
DSP on the raw synthesized audio.

Scoped intensity via `AskUserQuestion` before building — "Subtle,
JARVIS-like" was picked over "Noticeably robotic" and "no DSP, just an
activation tone," since an overly strong effect genuinely hurts
intelligibility (a real, well-known trade-off for effects like ring
modulation, not just a taste call). New `core/voice_effects.py`:
`apply_ring_modulation()` and `apply_chorus()` (both pure `numpy`, no
new dependency — `numpy` was already in use for
`core/voice_manager.py`'s recording/playback arrays), combined into
`apply_ai_voice_effect()` at deliberately conservative mix levels (8%
ring-mod, 18% chorus), peak-normalized against the original so mixing
effects in doesn't quietly change volume or clip.
`apply_ai_voice_effect_to_wav_file()` is the actual integration point:
`core/voice_manager.py`'s `synthesize()` now runs every synthesized
WAV through it whenever `voice.ai_voice_effect` is true (new config
key, default `true`), best-effort — a post-processing failure logs and
falls back to the unprocessed audio rather than losing speech
entirely. New Settings checkbox ("✨ AI Voice Effect", next to the
Voice dropdown) toggles it live and speaks a preview immediately,
same "hear the change, don't just save it silently" pattern the voice
picker itself already uses.

**Explicit, important caveat**: I cannot listen to audio myself, so
the specific effect parameters above are a first pass calibrated by
the *description* the user chose ("JARVIS-like," "clearly
intelligible"), not by ear — expect this to need tuning once actually
heard, same as any other subjective creative choice in this project
that can't be verified without a human's senses. If it needs
adjusting, the four constants at the top of `core/voice_effects.py`
(`_RING_MOD_CARRIER_HZ`/`_RING_MOD_MIX`/`_CHORUS_DELAY_MS`/`_CHORUS_MIX`)
are the one place to change, not the effect functions themselves.

Verified what's verifiable without ears: 11 new unit tests (shape/
dtype/no-clipping/volume-preservation invariants, plus a real WAV
round-trip and a stereo-file no-op check), and a real end-to-end run
through the actual `VoiceManager.synthesize()` path confirming the
effect measurably changes Piper's real output and the toggle actually
turns it on/off. Also confirmed, while investigating an initial
"suspicious" file-size difference between runs, that Piper's own
synthesis has genuine frame-count variance between separate calls on
identical text (nothing to do with this change) — worth remembering
before treating a similar size difference as a bug in the future.
1109 tests passing.

## Startup briefing connected to real dashboard widgets (built, 2026-07-15)

The user reported the spoken briefing "read like a script instead of
providing a startup dashboard summary" — quoting a real launch where it
said only the greeting + "nothing new to report." Root cause, found by
reading the code rather than assuming: `_build_briefing_text()`
checked a fixed, hardcoded list of data sources (missions/calendar/
notifications/projects/memory) with **zero connection** to
`core/dashboard_widgets.py`'s actual enabled-widget list — adding,
removing, or reordering a widget never changed what the briefing talked
about, because it wasn't reading from the widget system at all.

Fixed by making the briefing genuinely widget-driven:
`gui/home_dashboard.py` gained one `_<widget_id>_highlight()` method
per existing widget (Power/Mission/Volume/Current Project — Volume
deliberately returns `None`, not meaningful for a spoken summary),
registered in `self._widget_highlight_providers` alongside
`self._widget_builders`. `_widget_highlights()` iterates
`context.dashboard_widgets.enabled_widgets_in_order()` — the exact same
list `gui/dashboard_customize_dialog.py` writes to — so the briefing
now automatically tracks whatever's actually enabled, with no separate
list to keep in sync by hand. `core/startup_briefing.py`'s
`build_stat_highlights()` lost its `active_mission_count`/
`active_project_count` params (those moved to the widget providers
above) and now only covers Calendar/Notifications, which aren't Home
widgets of their own yet. Construction order in `HomeDashboard.__init__()`
had to flip — the widget grid now builds (and refreshes with real data)
*before* the briefing banner, even though it's still added to the
visible layout afterward, since the briefing needs real widget state
already computed to read from.

Verified for real, not just by reading the diff: a live headless-Qt
test added an active Mission, confirmed the briefing said "1 active
mission," then called `dashboard_widgets.set_enabled("mission", False)`
(the exact call `dashboard_customize_dialog.py` makes) and confirmed a
freshly-rebuilt briefing no longer mentioned missions at all — the
dashboard and the briefing are now provably the same source of truth,
not two systems that happen to agree by coincidence. 1109 tests
passing (test count unchanged — `build_stat_highlights()`'s existing
tests were updated for the narrower signature, not added to).

**This was picked as the concrete first slice of a much larger
sharpening of the companion-philosophy vision** — see `docs/VISION.md`'s
new "The voice-only operability test" section: the user's real target
is a device fully operable by voice alone, with MIA acting like a
game-guide-style tutor that deeply understands every module's live data
and capabilities, not just its own tool registry. This fix is a small,
concrete instance of that principle (the briefing now reflects real
app state instead of a hardcoded list) but the larger initiative — full
conversational understanding of widget/module data, voice-driven
interaction with widget menus, and a visual redesign of the Home
screen — is intentionally not started here; needs its own scoping pass.

## Core drops its GUI; Home visual identity — Presence widget (built, 2026-07-15)

Two big decisions landed in the same conversation, both now written
into `docs/VISION.md`: **Core becomes voice-first with no rich
dashboard UI at all** (only the small e-paper Receiver display,
`docs/HARDWARE.md`'s Modular Backpack section) — meaning everything in
`gui/`/`modules/*/module.py` built so far should now be understood as
"the Home app," not "the Core app," a real reframing worth reading the
VISION.md section for rather than assuming. And **Home gets a full
sci-fi companion-interface redesign** — floating panels, 3D-feeling
depth, holographic styling, modules as interactive objects, a living
"presence" that reacts through motion/lighting/animation. Both are
north-star decisions; this entry is the first concrete slice actually
built from them.

**Built: `gui/presence_widget.py`'s `PresenceWidget`**, replacing
`gui/character_panel.py`'s static emoji-swap reaction display. Extends
`gui/boot_core_widget.py`'s `PulsingCoreWidget` technique (a cheap,
timer-driven breathing glow-orb — layered translucent rings for bloom
without a real blur pass, already proven fast enough for continuous
30fps repainting) rather than inventing a new animation system: same
rendering approach, now state-driven (`idle`/`listening`/`thinking`/
`loading`/`notification`, each its own color + pulse speed, with a
rotating highlight arc reserved for "actively working" states) and
rendering an arbitrary centered glyph instead of a fixed "MIA" label
— so each module keeps its own icon identity while the orb's motion
communicates what MIA is currently doing. Falls back to `idle` for
an unrecognized state rather than raising.

Wired into `CharacterPanel`: `_set_busy()` (an Assistant reply in
flight) drives `thinking`; module-open and a new notification each
trigger a new `_start_transient_state()` helper — a short auto-reverting
pulse (`loading` for ~700ms, `notification` for ~3s) rather than
sticking permanently the way the old icon swap did, restarting cleanly
if a second transient event arrives before the first one's timer fires.

**Deliberately not wired yet: a genuine `listening` state.**
`CharacterPanel`'s sidebar chat is text-only by design (no mic — voice
lives on the full `modules/assistant/module.py` screen, which doesn't
have a presence widget at all yet). Flagged here, not silently skipped
— extending presence to the full Assistant screen (with real
push-to-talk-driven `listening`) is natural next work, not started.

**Known minor cleanup, not done**: `gui/styles.py`/`gui/theme_manager.py`
still carry `QLabel#CharacterIcon` QSS rules from the old static-icon
approach — now unused (`PresenceWidget` self-paints, doesn't pull from
the theme cascade), harmless dead CSS, not yet removed.

Verified for real, not just visually: a live headless-Qt test drove
`CharacterPanel` through the actual event bus (`module.opened`,
`notification.created`) and `_set_busy()` toggling, confirming every
state transition (`idle` → `loading` → `idle`, `idle` → `notification`
→ `idle`, `idle` → `thinking` → `idle`) fires correctly with no crash,
plus a separate render confirming all 5 states are visually distinct
side by side (screenshot, not just asserted in code) — teal breathing
idle, teal rotating-ring listening, purple rotating-ring thinking,
amber rotating-ring loading, amber fast-pulse notification. 1109 tests
passing (test count unchanged — no new pure-logic functions; this is
Qt-widget behavior, covered by the live verification above per this
project's own established test-tier split, not pytest).

## Boot sequence rewrite — "MIA waking up" (built, 2026-07-15)

The second concrete slice of `docs/VISION.md`'s Home visual-identity
brief, picked next by the user over the main dashboard layout: "the
system initializes, modules come online, sensors activate, and MIA's
personality begins loading... like powering on a futuristic device,"
not a static progress bar.

**`core/application.py`'s boot steps are now real, not cosmetic.** The
old 4-step sequence (`"INITIALIZING CORE SYSTEMS..."`, etc.) was mostly
`_noop()` filler around one real action
(`module_manager.discover()`) — replaced with 6 steps that each report
something actually true right now: `_boot_step_core_systems()`,
`_boot_step_module_array()` (real discovered count, e.g. "19 MODULES
ONLINE"), `_boot_step_assistant_core()` (a real `context.llm.is_available()`
check — reports "OFFLINE (OLLAMA NOT DETECTED)" honestly if it isn't),
`_boot_step_voice_interface()` (real STT/TTS availability),
`_boot_step_power_systems()` (real battery read or "NO BATTERY
DETECTED"), `_boot_step_personality_matrix()` (the final "she's awake"
beat). `_run_boot_steps()` simplified to a plain list of callables
returning the log line to show, rather than a list of
`(message, action)` tuples with the message written *before* the real
result was known — the displayed text now always matches what actually
happened. The now-fully-unused `_noop()` staticmethod was deleted.

**`gui/splash_screen.py` rewritten around three real changes**: (1)
`gui/presence_widget.py`'s `PresenceWidget` (built for the Presence
entry above) replaces the fixed `PulsingCoreWidget` — boot now shows
the `loading` state (amber, rotating ring) throughout, flipping to
`idle` (calm teal breathing) the instant `_boot_step_personality_matrix()`
fires, a visible "she's awake now" moment instead of the window just
closing mid-animation. (2) `set_status()` (replace the one line) became
`add_log_line()` (*append*) — boot now reads as an accumulating system
log, closer to the "watching a device power on" feel than a single
line being silently swapped underneath the user. (3) new
`show_modules()` reveals one small icon badge per *actually discovered*
module (real `ModuleBase.icon`/`display_name`, not placeholder art) —
the literal "modules come online" moment — faded in as one batch rather
than staggered per-icon (a real per-module delay would add wall-clock
boot time proportional to module count, already ~19 modules).
`gui/boot_core_widget.py` deleted outright once `PresenceWidget` fully
superseded its one caller — no reason to keep two versions of the same
rendering technique.

**Found two real Qt geometry bugs via a live headless-Qt test, not
assumption — same recurring category this session has hit before
(the dashboard grid's layout-replacement and widget-visibility bugs)**:
(1) a word-wrapped `QLabel`'s height didn't grow after `setText()`
changed its content from one line to several post-construction — the
label reported a single-line-tall size while actually holding 5 lines
of text. Fixed with `adjustSize()` + re-activating the parent layout.
(2) A `QGraphicsOpacityEffect`-wrapped container reported a real
`(0, 0)` size even after the same `activate()` fix that resolved (1) —
needed an explicit `QApplication.processEvents()` to force the
geometry pass immediately, since effect-wrapped widgets apparently
don't get one from a plain layout-invalidation call alone. Also bumped
the splash window from 480×460 to 480×640 — the old size was tuned for
one status line and clipped badly once boot could show a multi-line
log plus a module-icon row.

Verified for real, not just visually: constructed a real
`MIAApplication` (not simulated data) and called all 6 boot-step
methods directly, confirming genuinely real output (19 modules found,
"ASSISTANT CORE... ONLINE" because Ollama is actually running here,
"VOICE INTERFACE... ONLINE", "POWER SYSTEMS... NOMINAL (100%)"), that
the log accumulates correctly, that all 19 real module icons render,
and that the presence orb correctly lands on `idle` at the end. Also
rendered real before/after screenshots (loading vs. ready) confirming
the visual transition. 1109 tests passing, no data/config pollution.

## "Master Baiter" example renamed to "Master Angler" (2026-07-15)

The user, live-testing the app, hit the placeholder text in the New
Mission dialog and flagged it — funny, but not something that should
be the default example shown in the real app. Fixed everywhere it
appeared as live example text, not just the one dialog: the New Mission
placeholder itself (`gui/add_edit_mission_dialog.py`), `core/mission_manager.py`'s
docstring, the `add_mission` Assistant action's description
(`core/application.py` — regenerates into `docs/ASSISTANT_CAPABILITIES.md`,
fixed there too), `docs/VISION.md`'s concept-mapping table, and every
test fixture using it as example data (6 test files). Picked "Master
Angler" over inventing a new pun — it's a real term US state fishing
programs use for a trophy-catch achievement, so it's not just clean,
it's a more authentic example than the original joke was.

**`docs/ROADMAP.md`'s own historical entries were deliberately left
alone** — those are dated records of what was actually built/said at
the time, not live reference text; rewriting them would misrepresent
history. Only this document's *live* content (test fixtures, source
descriptions, the capabilities doc) got the rename.

Verified for real: full pytest suite (1109/1109, one real casualty of
a bulk find-replace caught and fixed — a lowercase `"master baiter"`
variant specifically testing case-insensitive mission-name lookup,
missed by an exact-case replace) and a fresh 68/68 run of the live-model
golden set, confirming the renamed trigger phrases still gate and
resolve correctly against the real model, not just that the test
fixtures were internally consistent.

## "ForMIA" design handoff, pass 1: color tokens + widget card restyle (built, 2026-07-15)

After the boot-sequence animation redesign was rejected outright, the
user brought a real, high-fidelity design handoff instead of more
guessing — `ForMIA.zip` (a `README.md` with exact design tokens, a
`WIDGET_STENCIL.md` copy-paste card pattern, and `Dashboard.dc.html`/
`Dashboard Options.dc.html` HTML mockups of the chosen design and its
earlier explored directions). The handoff's own instructions were
explicit: "design references... not production code to copy directly...
recreate this design inside your program's existing environment...
implement pixel-close."

**Deliberately split into two passes, not one big change again** —
direct lesson from the rejected boot-sequence redesign (see the earlier
entry + `feedback_animation_taste_limits` in memory): ship one visible
thing, get it confirmed, before adding more. Pass 1 (this entry): exact
color tokens + the widget card restructure, scoped to `dark_field`
(the theme the handoff is explicitly evolving — its own README says
"restyled to match the app's existing color scheme") and just the Home
dashboard. Not yet touched: the four new widgets the mockup shows (CPU
Load sparkline, Network, Quick Bus toggles, Activity Log), the header's
pill-style nav buttons, and the assistant sidebar's restyled message
bubbles — each is its own follow-up pass.

**Exact token swap in `gui/styles.py`'s `DARK_FIELD_THEME`**: page
background `#10141a`→`#0a0e15`, header/panel background `#161b22`→
`#0c1017`, card background `#161b22`→`#101722`, border `#232b34`→
`#1b222e`, accent teal `#4fd1c5`→`#38d9c9`, text primary/secondary
updated to the handoff's exact hex values throughout. Header nav
buttons gained a filled background (`#111722`) matching the mockup's
pill treatment instead of the old transparent-bordered look.

**Real structural change, not just colors**: the handoff's widget
stencil drops icon badges entirely in favor of a small uppercase
"eyebrow" label above each card's content — `gui/home_dashboard.py`'s
`_build_widget_header()` no longer renders `DashboardSectionIcon` at
all. QSS has no `text-transform`, so the label text is uppercased in
Python before being set. The `icon` parameter is kept (not removed —
every widget still carries its real glyph) and now drives the eyebrow
label's tooltip instead of taking up card space, so a module's icon
identity isn't fully discarded, just no longer visually prominent.
`#DashboardSectionTitle`'s QSS switched to a small (10px) monospace,
letter-spaced, muted-color style matching the stencil's eyebrow spec.

Verified with a real screenshot of the actual `HomeDashboard` (not the
HTML mockup) — Power/Mission/Volume/Current Project cards all show the
new eyebrow-label pattern with real data, no icon badges, matching the
handoff's card structure. Full pytest suite (1109/1109, unaffected —
this pass touched only styling/layout, no new pure-logic functions),
confirmed the other 3 themes are untouched (only `DARK_FIELD_THEME`'s
block was edited).

## "ForMIA" design handoff, pass 2: Activity Log + Quick Bus widgets (built, 2026-07-15)

Pass 1 was confirmed to land well — continuing per the handoff's
remaining widgets, still deliberately staged rather than building
everything the mockup shows at once. Picked the two new widgets that
need **zero new data-gathering infrastructure** — both reuse fully-
existing real services — leaving CPU Load (needs a new rolling-history
sample buffer, since `core/system_health.py`'s `cpu_percent` is a
point-in-time reading, not a series) and Network (the mockup's
"round-trip ms" implies pinging something, in real tension with this
project's offline-first principle — a real design question, not just
an implementation detail) for a later pass once those are thought
through properly rather than rushed in.

**Activity Log** — a new full-width "log/feed" widget
(`_WIDGET_COLUMN_SPANS` added to `gui/home_dashboard.py`'s grid
placement, generalizing it beyond the single-column-per-widget
assumption pass 1 shipped with) showing the 3 most recent
`context.activity_log` entries as one monospace line
(`format_activity_log_line()`, "HH:MM summary // HH:MM summary" per
the stencil's log variant) — real data, the same service
`modules/dashboard/module.py` already surfaces, not a new one.

**Quick Bus** — two toggle switches (Voice input, Notifications), and
per the handoff's own explicit instruction ("wire to real feature
flags... not just visual") both drive **real behavior, not cosmetic
UI state**:
- New `notifications.enabled` config key — `core/notification_manager.py`'s
  `notify()` now returns `None` and creates/persists/publishes nothing
  at all when disabled. Checked first: no existing caller anywhere in
  the codebase inspects `notify()`'s return value, so widening its
  return type to `Optional[Notification]` is safe.
- New `voice.push_to_talk_enabled` config key — `modules/assistant/module.py`'s
  `_on_talk_pressed()` now refuses to start recording and shows "Voice
  input is turned off" when disabled.
- New `gui/widgets/toggle_switch.py`'s `ToggleSwitch` — custom-painted
  (`QAbstractButton` + `paintEvent`, same technique as
  `gui/presence_widget.py`) rather than a styled `QCheckBox`, since Qt's
  checkbox QSS can fake a pill *shape* but not a knob that visibly
  slides between two positions — that needs either an image asset
  (this project has none for UI chrome) or real paint code.

**`core/notification_manager.py` had no test file at all before this —
a real, pre-existing gap**, not something this pass tries to fully
backfill. Added a minimal `tests/test_notification_manager.py` covering
specifically the new gate (3 tests), not general coverage.

Verified for real, not just visually: a live headless-Qt test found the
actual `ToggleSwitch` instances inside a real `HomeDashboard`, flipped
one via `setChecked(False)` (the same call a real click makes), and
confirmed `context.notifications.notify()` genuinely returned `None`
and the config value actually changed — not a cosmetic switch that
merely looks toggled. Also a real screenshot confirming Activity Log's
full-width span and Quick Bus's two teal toggles render correctly with
real log data. 1115 tests passing (6 new), no regressions.

## ForMIA design handoff, pass 3: bundled fonts + closing remaining fidelity gaps (2026-07-16)

Re-compared the running app directly against the original
`ForMIA.zip`/`Dashboard.dc.html` mockup (still on the user's desktop,
re-extracted fresh) via a real screenshot, rather than assuming passes
1-2 already matched it. Found the two theme colors were already
pixel-correct, but two real gaps: **typography** and **missing
structural elements**.

**Typography**: the mockup's own CSS specifies Inter (UI text) and
JetBrains Mono (numeric/mono accents) — `gui/styles.py`'s
`DARK_FIELD_THEME` had shipped with generic system-font fallbacks
("Segoe UI"/"Consolas") the whole time, a real, visible fidelity gap
just not caught until directly re-comparing. Neither font is a default
system install on Windows/Linux/Pi, so both are now bundled
(`assets/fonts/`, 8 static-weight `.ttf` files, SIL OFL / Apache 2.0
licensed — see `assets/fonts/NOTICE.md`) and registered via
`QFontDatabase.addApplicationFont()` in `core/application.py`'s new
`_load_bundled_fonts()`, called right after `QApplication` construction
and before any stylesheet applies. Scoped to `dark_field` only, same as
every prior ForMIA pass — the other 3 themes keep their original system
fonts.

**Missing structural elements**, all present in the mockup's markup but
absent from the shipped dashboard: the "SYSTEM OVERVIEW" section label
+ "● ALL SYSTEMS NOMINAL" status pill (new `_build_overview_row()` —
the pill is static ambient copy, same precedent as
`gui/main_window.py`'s own status-bar default message, not a live
health check); the clock had shipped as a bare centered label stack
with no card/border/eyebrow at all, now a real `DashboardCard` matching
the mockup's eyebrow-label-left / date-right layout; a "WIDGETS"
section label above the widget grid. Also restyled the assistant
sidebar's suggested-prompt buttons from full-width left-aligned bars
into the mockup's actual small pill-shaped chips
(`gui/character_panel.py` now adds them with `AlignLeft` so
`QVBoxLayout` doesn't stretch them back to full width).

**Deliberately left as-is, not "fixed" to match the static mockup
literally**: Volume's real slider + mute button (mockup only shows a
static progress bar — real interactivity is a legitimate improvement
over a non-interactive prototype, not a gap); the presence-orb avatar
in the sidebar (mockup shows a plain static "M" badge — the
state-driven `PresenceWidget` is deliberate, already-decided richer
functionality, not a regression); CPU Load/Network widgets (already
deferred, see above). **Chat message bubbles** (mockup shows
alternating-alignment bubble styling; the app currently renders one
plain scrolling text box) remain a real, already-flagged gap — same
"next candidate" status noted in the pass-2 entry above, not rushed
into this pass.

Verified with real screenshots of the actual running `MainWindow` (not
the HTML mockup) before and after, side by side against the mockup's
markup. 1123 tests passing, unaffected (styling/layout only, no new
pure-logic functions).

## Boot sequence: 3 disliked 2026-07-15 elements reverted (2026-07-16)

User feedback on the 2026-07-15 boot rewrite ("the icons under MIA, the
color change of the orb, and the stacking log... all made it look
worse") is finally actioned, not just logged as a pending revert.
`gui/splash_screen.py`: the per-module icon reveal row (`show_modules()`)
is removed entirely, `add_log_line()`'s accumulating multi-line log is
reverted back to a single-line `set_status()` that replaces the text
each step, and the presence orb no longer switches to the amber
`"loading"` state during boot — it stays in the default `"idle"` state
(blue-teal breathing, no rotating ring) throughout, matching milestone
2.9's original `PulsingCoreWidget` look exactly. Splash size reverted
480x640 -> 480x380 (the extra height existed only for the now-removed
log/icon row). `core/application.py`'s boot-step call sites updated to
match (`show_modules()`/`set_ready()` calls removed, `add_log_line()` ->
`set_status()`). Verified with a real headless-Qt boot smoke test
(actual `SplashScreen` + a full `MIAApplication` boot through all 19
real modules) confirming no crash, correct 480x380 size, `idle` default
state, and status-replace-not-append behavior. 1115 tests passing
(unaffected — this is Qt-widget behavior, not pytest-covered, per this
project's established test-tier split).

## Chat message bubbles, Switch User moved to Settings, Settings headers enlarged (2026-07-16)

Three more pieces of user feedback, all built.

**Chat message bubbles** — the last remaining gap from the ForMIA
pass-3 re-comparison, closed now. New `gui/widgets/chat_bubble.py`'s
`ChatBubble` replaces `gui/character_panel.py`'s plain scrolling
`QPlainTextEdit` log with real alternating-alignment bubbles (user
right, assistant left, teal-accented border) — a `QScrollArea` +
`QVBoxLayout` of bubble widgets, rebuilt on every conversation
update/switch with the same explicit `hide()`+`setParent(None)`+
`deleteLater()` cleanup this codebase already established for
`gui/home_dashboard.py`'s widget grid. Scoped to the sidebar only —
`modules/assistant/module.py`'s full-screen chat keeps its existing
denser log, unchanged.

**Hit and fixed a real, previously-undocumented Qt layout bug**: every
wrapped multi-line bubble rendered with its first and last lines
clipped/overlapping, reproducing identically regardless of
`adjustSize()`/`layout().activate()`/explicit `show()` calls (all tried
first, all failed — confirmed via direct measurement that
`label.sizeHint()` correctly reported the full wrapped height, e.g.
75px for 5 lines, but the layout only ever actually allocated 60px, a
clean one-line shortfall). Root cause: `QVBoxLayout` doesn't reliably
negotiate `heightForWidth()` through nested layouts (a frame's own
`QVBoxLayout`, added to the chat log's outer `QVBoxLayout` with an
alignment flag, inside a `QScrollArea`) — a known, long-standing Qt
limitation, not a bug in this codebase's own layout-invalidation
conventions. Fixed by removing Qt's automatic negotiation from the
picture entirely: the label gets both a fixed width *and* a fixed
height computed directly via `heightForWidth()`, rather than trying to
coax the layout into re-negotiating correctly. Worth remembering for
any future word-wrapped label inside more than one level of nested
layout in this codebase — don't assume `adjustSize()`/`activate()`
alone will fix a wrong wrapped height the way it did for
`gui/home_dashboard.py`'s simpler (single-level) cases.

**Switch User moved from the header to Settings**, at the user's
explicit request. `gui/main_window.py`'s header bar no longer has the
button; a new "Account" section in `modules/settings/module.py` has it
instead. Modules can't import `gui/` directly (CLAUDE.md's layering),
so the button publishes a new `"profile.switch_requested"` event
instead — `MainWindow` subscribes and re-emits its existing
`switch_profile_requested` signal, so `core/application.py`'s handler
needed zero changes. Same module-isolation pattern as the Assistant's
`open_module` action. Verified end-to-end with a real headless-Qt test:
clicking the Settings button genuinely fires the same signal the old
header button did.

**Settings module's category headers enlarged** — they'd been an
inline `setStyleSheet("font-weight: 600")` with no font-size at all
(just the base 14px), too subtle to read as real section breaks
stacked five deep on one page. New `#SettingsSectionHeader` QSS class
(17px, 700 weight) applied to all five section labels (including the
new "Account" one).

Verified with real screenshots (chat bubbles rendering correctly side
by side, Settings page with visibly bigger headers, header bar with no
Switch User button). 1123 tests passing throughout — none of this pass
needed new pure-logic functions, all Qt-widget/styling behavior per
this project's established test-tier split.

## Boot orb size increased, Hold to Talk gets real press/release feedback (2026-07-16)

Two more concrete pieces of feedback from the same session as the boot
revert above. **Boot orb too small**: the 2026-07-16 revert (previous
entry) restored the original blue/single-line/no-icons boot look, but
carried over the interim redesign's 200px `PresenceWidget` diameter
without checking the *original* milestone 2.9 size — `git show` on the
pre-redesign `gui/boot_core_widget.py` shows the original
`PulsingCoreWidget` was a fixed 440×440, noticeably larger. Rather than
restore that exact value blind (440px wouldn't even fit this splash's
current 40px margins at the old 480px window width), bumped to 300px
and grew the splash window 480x380 -> 560x460 to comfortably fit it —
verified via a real screenshot, no clipping, correct proportions.
**Still judged too small on a second look, same day** — bumped again
to 380px (window 560x460 -> 680x580), and separately fixed the whole
group visibly "sitting low": the layout had equal-weighted stretches on
both sides of the orb, but the fixed content above it (just the
subtitle) was smaller than below it (status label + progress bar), so
the group rendered low rather than centered. Removed the leading
stretch entirely (subtitle now anchors near the top margin) and kept
only the stretch below the orb, pulling the whole group upward —
verified via a real screenshot.

**Hold to Talk had no visual press/release indication at all** — only
the small status label below it changed text ("Listening…"). Gave the
button its own `#TalkButton` QSS identity (previously fully unstyled)
plus a `recording` dynamic property, same re-polish pattern as
`gui/main_window.py`'s notification-bell `hasUnread` accent — solid red
(reusing this theme's existing critical-notification `#e06666`, the
universal "recording" convention) while held, reverting to the idle
teal-outline look on release. Driven from
`_set_talk_button_recording()` inside the existing
`_on_talk_pressed()`/`_on_talk_released()` handlers rather than Qt's
native `:pressed` pseudo-state, so it stays correct for both the
on-screen click and `core/push_to_talk_trigger.py`'s GPIO path, which
fires the same handlers. Verified with a real headless-Qt smoke test
(faked `VoiceManager.start_recording()`, confirmed the `recording`
property and rendered color genuinely flip on press and revert on
release, via two screenshots).

1123 tests passing throughout (no new pure-logic functions — both are
Qt-widget/styling behavior, covered by real screenshots per this
project's established test-tier split).

## MIA Home scope reconciliation (2026-07-16) — see `docs/VISION.md`

A consolidated planning handoff (`MIA_HOME_CLAUDE_CODE_HANDOFF.md`,
covering separate claude.ai conversations on dashboard architecture, a
Kraken crypto trading agent, and real estate portfolio tracking) was
folded into `docs/VISION.md`'s new "MIA Home's expanded scope" section
and its concept-mapping table (the stale "Finance -> Project 1" row
corrected to Home/Project 2, three new rows added). **Audited this repo
directly first — confirmed none of it exists here yet**: no
`mia_module_contract.py`, no `mia_home_schema.sql`, no trading-agent or
real-estate code anywhere in `core/`/`modules/`/`gui/`. Full detail
(financial widget shapes, the shared JSON export format, open ingestion-
mechanism question, workshop-hardware module-contract question) lives
in `VISION.md` — read it fresh before starting any of this rather than
relying on this one-paragraph pointer. Not scoped into concrete
milestones yet; tracked as real follow-up work, not just aspiration:

- [x] Decide the snapshot ingestion mechanism (watched folder vs. manual
      upload) for Kraken/real-estate export files — **watched folder,
      built 2026-07-16, see the dedicated entry below**
- [x] Build real estate + Kraken ingestion widgets (hardware-independent,
      safe to build now, pre-Project-2-migration) — **built 2026-07-16,
      see the dedicated entry below**
- [x] Confirm what Fidelity actually exposes before committing to a
      brokerage widget approach — **Fidelity IS supported via Plaid's
      Investments product; Pay-as-you-go tier needs a manual support
      ticket for Investments access, see the dedicated entry below**
- [x] Decide how `mia_module_contract.py`'s workshop-hardware `MIAModule`
      concept relates to this repo's existing `ModuleBase`/`MODULE_SPEC.md`
      — **a sibling concept, built 2026-07-16 as `core/workshop_machine.py`,
      see the dedicated entry below**
- [x] Decide whether `mia_home_schema.sql` gets adopted as-is, adapted to
      this project's persisted-JSON-manager convention, or something in
      between — **adapted to JSON, built 2026-07-16 (Materials slice
      only), see the dedicated entry below**

## MIA Home financial snapshot ingestion: watched-folder mechanism built (2026-07-16)

First real slice of "MIA Home's expanded scope" (see the section above
in `VISION.md`), picked deliberately as the one genuine blocking
decision — the real estate/Kraken ingestion widgets can't be built
without it. Confirmed via `AskUserQuestion`: **watched folder**, not a
manual upload button — both source tools (the Kraken trading agent, the
real estate portfolio dashboard) already require a manual export step
on the user's end, so the only remaining manual action is dropping the
file into one folder; Home picks it up from there automatically,
reusing the same "periodic scan, no user click needed" pattern already
established by v0.19's Home Dock auto-import.

New `core/finance_manager.py` (`AppContext.finance`) — a
`financial_snapshots/` folder (sibling of `data/`, same "user-provided
external content, not app-owned state" precedent as
`reference_library/`/`trip_photos/`, configurable via
`finance.snapshot_import_folder`). `core/application.py` polls it every
60s via a new `_finance_snapshot_timer` (same "always alive for the
whole session" pattern as the alarm/power/daily-occasion timers),
firing a notification for each newly-imported snapshot.
`parse_snapshot_content()` deliberately only requires `source`/
`generated_at` — every other field is accepted opaquely into
`.data` rather than validated against `VISION.md`'s one worked example,
since the real Kraken export's exact schema isn't confirmed yet and
being strict here risks rejecting a real, valid export over a guessed
field. A snapshot only replaces an existing one for the same `source`
if its `generated_at` sorts newer (plain ISO-8601 string comparison),
so a stale re-dropped file can't regress already-imported data.
Processed files move to `imported/` (kept, not deleted) or `failed/`
(so a broken file doesn't get re-logged every single poll forever) —
never left in the watched folder to be reprocessed.

Deliberately NOT built this pass — genuinely a separate, later
decision: any actual "combined net worth" computation across multiple
snapshot sources. The recommended three-widget-plus-rollup split (see
`VISION.md`) needs the real Kraken export's exact field shape first,
which isn't confirmed — this manager only stores/exposes each source's
raw snapshot (`latest_snapshot(source)`/`all_latest_snapshots()`),
leaving any cross-source math to whichever pass builds the actual
widgets next.

Verified for real: 16 new tests (`tests/test_finance_manager.py`) — the
pure `parse_snapshot_content()` validation logic, plus a real tmp_path
watched folder exercising genuine file moves/reads (same "no hardware
needed, so use the real thing, not mocks" reasoning as
`test_script_runner.py`) covering create-on-first-run, import, replace-
if-newer, discard-if-older, and persistence across a fresh manager
instance. Plus a real headless smoke test through the full
`MIAApplication` boot confirming the manager constructs, resolves to
the real `financial_snapshots/` folder, and an empty scan is a genuine
no-op (no stray `data/financial_snapshots.json` written). 1139 tests
passing (16 new).

## Boot-up sound: synthesized "growing pulsing energy" effect (2026-07-16)

Last piece of feedback from the same round — a sound to go with the
pulsing boot orb, "like a growing pulsing energy sound." New
`core/boot_sound.py`: `generate_boot_sound_samples()` synthesizes a
rising-pitch "power up" sweep (110Hz → 440Hz, proper chirp synthesis
via cumulative phase integration, not the naive/wrong
`sin(2*pi*freq(t)*t)` approach) with a pulsing amplitude envelope on
top and an overall fade-in ("growing" from silence) + short fade-out
(avoids a click). Generated programmatically with numpy (already a
dependency, via `core/voice_manager.py`'s `play()`) rather than
bundling or fetching an audio file — sidesteps both this project's
offline-first stance on network-fetched assets and any licensing
question a found sound effect would raise.

New `core/boot_sound_worker.py`'s `BootSoundWorker` plays it off the
GUI thread, same reasoning `core/tts_worker.py` already established
(`VoiceManager.play()`'s `sd.wait()` blocks for the sound's whole
duration, which would otherwise freeze the boot sequence's own
`QTimer`-chained steps). Wired into `core/application.py`'s `run()`
right after the splash screen is displayed — fire-and-forget, degrades
silently if Voice/PortAudio isn't available, regenerated fresh each
boot (a few seconds of numpy synthesis is cheap enough that caching
would be premature).

**Genuinely unverifiable end-to-end in this dev sandbox** — confirmed,
not assumed, same as every other Voice-adjacent feature here:
`core/voice_manager.py`'s own docstring already establishes this
sandbox has no system PortAudio and no audio hardware at all. What
*is* verified: 8 new tests (`tests/test_boot_sound.py`) covering the
pure synthesis function directly — correct sample count/duration,
real int16 non-silent audio, no full-scale clipping, genuine fade-in/
fade-out behavior, and a real `wave`-module round trip write/read —
plus a real headless-Qt smoke test confirming the worker starts,
finishes cleanly, and writes a correctly-sized `.wav` file through
`_play_boot_sound()` directly, and a full real boot sequence through
`MIAApplication.run()` completing without any crash with the sound
wired in. Actually *hearing* it, and whether the ~3.5s duration/pulse
rate feels right alongside the real orb animation, needs real audio
hardware to confirm.

1282 tests passing (8 new).

## Missions redesign, chat bubble overflow fix, boot orb re-centered (2026-07-16)

Three more pieces of user feedback after actually using the app.

**Missions module redesign** — replaced the plain `QListWidget` rows
(both Missions and Objectives) with big "bubbly" cards
(`gui/widgets/mission_card.py`'s `MissionCard`, `gui/widgets/
objective_card.py`'s `ObjectiveCard`), at the user's explicit request
for "bigger and more bubbly button-like choosing... and interacting."
Modeled directly on the existing `gui/widgets/conversation_card.py`'s
`ConversationCard` pattern (a `QPushButton` with `QLabel` children, a
`selected` dynamic property, nested buttons whose clicks don't also
fire the parent's) — just bigger (96/88px minimum height vs. 60px,
16px titles vs. 13px) and rounder (20px border-radius vs. 8px — the
actual "bubbly" part). Each card now carries its own inline actions
(Mission: ✎ edit / ✕ delete; Objective: real `QProgressBar` + "+1"
tally / ✕ delete) instead of a separate "select from the list, then
click a button below" two-step — a genuinely more direct interaction,
not just a visual reskin. Scoped to `dark_field` only, same as every
ForMIA-era styling addition.

**Chat bubble text overflow, sidebar** — a real bug in the
2026-07-16 chat-bubble build: longer, realistic assistant responses
had their text clipped at the bottom of the bubble. Root cause found by
direct measurement (not guessed): `QLabel.heightForWidth()` and
`.sizeHint().height()` disagreed with each other by 16px+ on longer
text, even with the correct 12px font already resolved — neither Qt
API alone is reliable for this. Fixed by taking the max of both plus a
small safety buffer, erring toward "a little extra empty space at the
bottom of a bubble" rather than clipped text.

**Boot orb re-centered** — the previous "sits low" fix (a fixed
`addSpacing(48)` before the subtitle) overcorrected into "sits too
high." Root cause: earlier attempts balanced stretch *around the whole
content block* without first checking whether the fixed content above
the orb (just the subtitle) actually matched the fixed content below it
(status + progress) — it didn't, so equal stretches still left the orb
off-center. Fixed by symmetric 20px spacing on both sides of the orb
and one equal stretch above/below the whole now-balanced group. Bumped
again per "a bit bigger" (380px → 420px, window 680x580 → 720x640).

Verified for real: existing `format_mission_row()`/`format_objective_row()`
pure-function tests still pass unchanged (both stayed valid, just no
longer literally what's on screen — MissionCard/ObjectiveCard build
their own richer display from the same data). A real headless-Qt smoke
test exercising the actual Missions workflow end-to-end (select a
mission card, click a real "+1" button, confirm progress actually
updates via `core.mission_manager`, screenshot both the unselected and
selected/incremented states) plus a real long-message chat bubble
screenshot and a re-centered boot-orb screenshot. 1274 tests passing
throughout (unaffected — all three are Qt-widget/styling behavior, not
pytest, per this project's established test-tier split).

## MIA Home production pipeline GUI: Workshop & Electronics gains 4 new tabs (2026-07-16)

The GUI for all four production-pipeline slices above, at the user's
explicit call. Scoped via `AskUserQuestion` first: **placement** —
new tabs in the existing Workshop & Electronics module (its own
docstring already flagged production/fab as future scope, and
`modules/field_kit/module.py` already established the "one module,
several tabs" pattern for exactly this "multiple sub-features, one
`ModuleBase` subclass per folder" situation) rather than a new
top-level module; **coverage** — all four (Materials/Jobs/Products/
Ledger) in one pass, not staged further, since the backend already
fully connects them and a GUI covering only part would feel oddly
incomplete.

`modules/workshop/module.py` rebuilt around a `QTabWidget` (Components
unchanged, four new tabs added). Each new tab follows the same list +
filter + Add/Edit/Delete shape Components already established, plus
their own real actions: Jobs gets "Consume Material…"/"Produce
Product…" (the actual `consume_material()`/`produce_product()`
integration points, not just CRUD); Products gets "Add Listing…"/
"Remove Last Listing"; Ledger gets "Add Revenue…"/"Record Sale…"/"Add
Expense…" plus a live Net Profit summary line. One new reusable dialog,
`gui/pick_item_quantity_dialog.py` — "pick an existing item, enter a
quantity (and optionally an amount)" is the exact same shape for
Consume Material, Produce Product, *and* Record Sale, so one
parametrized dialog replaces three near-identical ones. Five other new
small dialogs (`add_edit_material_dialog.py`/`add_edit_job_dialog.py`/
`add_edit_product_dialog.py`/`add_edit_listing_dialog.py`/
`add_revenue_dialog.py`/`add_expense_dialog.py`) all mirror
`gui/add_edit_component_dialog.py`'s established shape exactly.

Verified for real, thoroughly, given this is the largest single GUI
addition this session: 10 new pure-formatting-function tests
(`format_material_row()`/`format_job_row()`/`format_product_row()`/
`format_revenue_row()`/`format_expense_row()`, same shape as the
pre-existing `format_component_row()` test). Plus a real headless-Qt
smoke test driving the *actual* end-to-end workflow through an isolated
`WorkshopModule` instance — added a material, a job, and a product;
consumed material into the job; produced product from the job; added a
listing; recorded a sale; added an expense — then switched through all
5 real tabs and screenshotted each, confirming correct computed values
on screen (job cost, product stock, net profit) matching what the
managers themselves report. Separately verified all 7 new dialogs'
field-to-property wiring directly (set widget values, call the
dialog's own accept handler, assert the exposed `entered_*` properties
match) — the one part a screenshot alone can't confirm. Confirmed no
stray files were left in the real `data/` directory afterward.

1274 tests passing (10 new — the GUI/dialog verification itself is
Qt-widget behavior, covered by the smoke test above, not pytest, same
test-tier split this project has used throughout).

**This closes out the entire MIA Home production-pipeline arc for this
session**: backend (`18bb218`→`7a7ab9f`) + GUI (this entry), all in one
day. Only remaining open item from the original MIA Home scope:
Fidelity data-access research (the user's own external task).

## MIA Home production pipeline, slice 4 (final): LedgerManager — schema fully adapted to JSON (2026-07-16)

Fourth and final slice of the production-to-sales pipeline, at the
user's explicit call ("let's build Revenue and Expenses next"). **This
completes the entire originally proposed `mia_home_schema.sql`**
(`materials`/`material_consumption`/`cost_rates`/`labor_rate`/`jobs`/
`products`/`product_listings`/`revenue`/`expenses`), fully adapted to
this project's persisted-JSON-manager convention rather than SQLite,
across four commits this session.

New `core/ledger_manager.py` — deliberately named `ledger_manager`, NOT
`finance_manager`: `core/finance_manager.py` already exists and is a
different concept entirely (watched-folder ingestion of *externally*-
generated Kraken/real-estate snapshots, built earlier this session).
This one is MIA Home's own bookkeeping for its own workshop sales.
`RevenueEntry`/`ExpenseEntry` are two peer lists (`data/revenue.json`,
`data/expenses.json`) owned by one manager — unlike
`material_consumption`/`product_listings`, they're not a parent/child
nesting, just two sides of one simple ledger (revenue in, expenses
out, net profit is the difference).

**The real integration point**: `LedgerManager.record_sale()` — same
shape as `consume_material()`/`produce_product()` — records a
`RevenueEntry` *and* deducts the sold quantity from
`core/product_manager.py`'s `quantity_in_stock` (clamped at zero, same
stance as everywhere else in this pipeline). A sale is now a real
inventory movement, not just a dollar figure next to an unrelated stock
count. Plain `add_revenue()` stays available for revenue not tied to
moving product stock (a commission, a flat fee). `net_profit()`/
`total_revenue()`/`total_expenses()` (optionally date-ranged, plain
ISO-8601 string comparison — same reasoning `core/finance_manager.py`'s
`generated_at` comparison already uses) are computed on demand, never
persisted, same "can't go stale" precedent as every cost/reporting
function built this session.

31 new tests (`tests/test_ledger_manager.py` — full CRUD for both
entry types, date-range reporting, and `record_sale()`'s cross-manager
integration with `ProductManager`) plus a real headless boot smoke
test confirming the manager constructs cleanly with no stray files
written. 1264 tests passing (31 new).

**Whole MIA Home production-pipeline arc, one commit per slice**:
Materials → Jobs (consume_material) → Products (produce_product,
listings) → Ledger (record_sale) — a genuinely connected system end to
end, not four independent lists. Next natural step, not started: a
real GUI for any of this (still core/-layer only across all four
slices) — or the still-open Fidelity research item, the one piece of
the broader MIA Home scope this session didn't touch.

## MIA Home production pipeline, slice 3: ProductManager (2026-07-16)

Direct continuation of Jobs above, at the user's explicit call ("let's
build Products next"). New `core/product_manager.py`: `Product`
(name/description/optional `job_id` link/`quantity_in_stock`/
`base_price`/notes) holding a plain list of `ProductListing`
(platform/price/`status` — one of `LISTING_STATUSES` =
Active/Inactive/Sold Out/url) rather than a fourth separate manager for
`product_listings` — same "a record owns a list of its own sub-items"
shape as `Job.material_consumption`. A product can carry several
listings at once (Etsy, a web store, local sales), each independently
priced/tracked.

**Closes the full loop**: `core/job_manager.py` gained
`produce_product()`, the other half of `consume_material()` — a job now
records a `ProductionEntry` (product_id + quantity_produced) on itself
*and* credits the same quantity onto the product's real
`quantity_in_stock` (via `ProductManager.adjust_stock()`, clamped at
zero same as everywhere else). A job consumes raw materials and
produces finished goods, and both sides are now genuine inventory
movements flowing through all three managers, not independent lists
that happen to reference each other. `ProductManager.adjust_stock()`
also stands alone for manual stock corrections not tied to a specific
job (a recount, a sale recorded by hand before Revenue exists).

**Not built yet**: `revenue`/`expenses` — the last piece of the
originally proposed schema, a later slice once Products is proven. No
GUI wired — still core/-layer only, same pattern as every MIA Home
piece this session.

29 new tests (`tests/test_product_manager.py`'s full CRUD/listings
coverage, plus `tests/test_job_manager.py`'s new `produce_product()`
integration tests — including one exercising the *full* consume-and-
produce loop on a single job) plus a real headless boot smoke test
confirming both managers construct cleanly with no stray file written.
1233 tests passing (29 new).

## MIA Home production pipeline, slice 2: JobManager (2026-07-16)

Direct continuation of the Materials slice above, at the user's
explicit call — Materials alone has nothing consuming it yet, so this
is what actually makes the two-manager system useful. New
`core/job_manager.py`: `Job` (name/description/status — one of
`JOB_STATUSES` = Planned/In Progress/Complete/Cancelled, same
fixed-vocabulary plain-str pattern as `Project.status`/
`Trip.activity_type` — /labor_hours/notes) holding a plain list of
`MaterialConsumptionEntry` (material_id + quantity_used) rather than a
fourth separate manager for what's really just line items belonging to
one job, same shape as `Mission.objectives`.

**The real integration point**: `JobManager.consume_material()` both
records the consumption entry *and* reaches into
`core/material_manager.py` (`self.context.materials`) to actually
deduct the used quantity from `quantity_on_hand` — clamped at zero
rather than going negative, matching `MaterialManager.update_material()`'s
own stance (a real inventory count can drift from what's on hand; the
job still genuinely happened either way, so don't block it). This is
what makes Materials + Jobs a connected system, not two independent
lists — a job's consumption now visibly affects
`materials_needing_restock()`.

**`cost_rates`/`labor_rate` resolved exactly as predicted** when
Materials was built: a single `workshop.labor_rate_per_hour` config
key (defaults to `0.0`, so an unset rate doesn't silently inflate every
job's cost), not their own managers — there was never enough there to
justify more than a scalar config value. `job_material_cost()`/
`job_labor_cost()`/`job_total_cost()` are plain functions computing
over already-loaded `Job`/`Material` records (`JobManager.total_cost()`
wraps them, pulling live material prices and the configured labor rate
fresh on every call) — same "compute on demand so it can never go
stale" precedent as `materials_needing_restock()`/
`core/memory_manager.py`, replacing the proposed schema's implied
costing logic without a database underneath it.

**Not built yet, explicit next slices**: `products`/`product_listings`/
`revenue`/`expenses` (the actual sales side this production pipeline
feeds into). No GUI wired either — core/-layer only, same pattern as
every other MIA Home piece this session.

25 new tests (`tests/test_job_manager.py`) — pure cost-function tests,
full CRUD, and dedicated `consume_material()` integration tests
(isolating both `MaterialManager` and `JobManager` in the same
tmp_path, same "combined-manager fixture" pattern as
`test_mission_manager.py`'s Trip/Waypoint/Expedition isolation)
confirming stock genuinely deducts, clamps at zero, and persists
correctly across a fresh manager reload. Plus a real headless boot
smoke test confirming the manager constructs cleanly with no stray
file written. 1204 tests passing (25 new).

## mia_home_schema.sql adapted to JSON: MaterialManager (2026-07-16)

Fourth and (for now) final slice of MIA Home's expanded scope, same
day — the last open architecture question on the checklist. Presented
three real options (SQLite as-is; adapt to this project's JSON
convention; a hybrid scoping SQL just to this join-heavy domain); user
picked **adapt to JSON**, for consistency with the 40+ managers already
in this codebase, none of which have ever needed a real database
despite plenty of their own cross-references already (Missions→Trips,
Journal→Trips, resolved by ID in Python, not SQL joins).

Also scoped down deliberately, at the user's explicit call, given the
size of the full proposed schema (`materials`, `material_consumption`,
`cost_rates`, `labor_rate`, `jobs`, `products`, `product_listings`,
`revenue`, `expenses`) and that only the table *names* were ever
handed off, not literal column definitions — **built just the
foundational `materials` piece this pass**: new
`core/material_manager.py` (`Material` dataclass + `MaterialManager`),
same exact shape as `core/component_manager.py` (`data/materials.json`,
add/update/delete/get/all/search). `materials_needing_restock()` is a
plain Python function over already-loaded records — same "compute on
demand so it can never go stale" precedent `core/memory_manager.py`
already established — replacing the proposed schema's SQL view, which
has no direct equivalent once there's no database underneath it.

**Deliberately a third separate inventory-style manager, not a reuse of
`core/inventory_manager.py` (general household) or
`core/component_manager.py` (electronics)** — same "mixing unrelated
domains serves neither well" reasoning `component_manager.py`'s own
docstring already gives for being separate from Inventory; fabrication
materials want `unit_cost`/`reorder_threshold` fields neither of the
other two has.

**Not built this pass, explicit next slices once Materials is
proven**: `jobs`/`products`/`product_listings`/`revenue`/`expenses`/
`material_consumption` (the actual production-to-sales pipeline);
`cost_rates`/`labor_rate` will likely become plain `workshop.*` config
keys rather than their own managers (simple scalars, not many-record
entities) once jobs are built — not decided yet. No GUI wired either —
same "core scaffolding first" pattern as the WorkshopMachine entry
above, this is core/-layer only.

17 new tests (`tests/test_material_manager.py`, same shape as
`tests/test_component_manager.py`, plus dedicated
`materials_needing_restock()` pure-function tests) plus a real headless
boot smoke test confirming the manager constructs cleanly against the
real (currently empty) `data/` directory with no stray file written.
1179 tests passing (17 new).

## Workshop hardware module framework: MIAModule reconciled as WorkshopMachine (2026-07-16)

Third slice of MIA Home's expanded scope, same day. Resolved the
architecture question flagged since the original handoff-doc fold-in:
how does the proposed `mia_module_contract.py`'s `MIAModule` interface
(`get_status()`/`send_job()`/`pause()`/`stop()`, `StatusReport`/
`JobHandle`/`ModuleError`, a `LaserEngraverModule` stub) relate to this
repo's own `ModuleBase`? **Answer: a sibling concept, not a
specialization or replacement — renamed entirely
(`WorkshopMachine`/`MachineStatusReport`/`MachineJobHandle`/
`WorkshopMachineError`) to remove the naming collision.** Checked
`modules/module_base.py` directly rather than assuming: `ModuleBase`
answers "what discoverable app screens exist" (one per top-level
`modules/` folder, `get_widget()`-driven, `pkgutil`-scanned). A
workshop machine answers a completely different question — "what
physical fabrication device can I send a job to and poll status on" —
structurally much closer to `core/calculator_engine.py`'s
`CalculatorPlugin` (many pluggable things, registered by id, one shared
control surface) than to `ModuleBase`, so `core/workshop_machine.py`
is modeled directly on that precedent (an `ABC` + a
`WorkshopMachineRegistry`, mirroring `CalculatorEngine`'s own
register/get/all shape) rather than invented from scratch or forced
into `ModuleBase`.

New `AppContext.workshop_machines`; a `LaserEngraverMachine` stub is
registered by default in `core/application.py` so the pattern
demonstrates end-to-end (`all_machines()` isn't empty, `get_status()`
returns a real `MachineStatusReport`) without pretending to control
real hardware — `get_status()` honestly reports `state="offline"`,
every other method raises `WorkshopMachineError`, same "flag as stub,
don't fake it" discipline as 11.3b/11.6. **Deliberately no GUI wired
this pass** — `modules/workshop/module.py`'s own docstring already
flagged "3D printer/CNC/laser... waits for that hardware/tooling to
exist" before this session ever started; this is exactly the
core-level scaffolding that was waiting on, not a reason to build a
control screen with nothing real behind it yet.

10 new tests (`tests/test_workshop_machine.py`, same shape as
`tests/test_calculator_engine.py`) plus a real headless boot smoke test
confirming the registry constructs, the stub registers, and
`get_status()` returns the expected offline report through the actual
`MIAApplication` boot path. 1162 tests passing (10 new).

## Real Estate + Kraken Agent + Net Worth dashboard widgets (2026-07-16)

Immediate follow-up, same day — the widgets that actually consume
`core/finance_manager.py`'s ingestion above. Three new registered
dashboard widgets (`gui/home_dashboard.py` + `core/application.py`),
same framework every other widget uses:

- **Real Estate** — reads the `real_estate_portfolio` source's
  `summary.total_equity`/`monthly_cash_flow`, the one fully-confirmed
  field shape (directly from `docs/VISION.md`'s worked example).
- **Kraken Agent** — reads the `kraken_trading_agent` source's
  `summary.total_value`/`gain_loss_pct`. **The exact source-string tag
  is this project's own best-guess placeholder, not confirmed anywhere**
  (`gui/home_dashboard.py`'s `_KRAKEN_SOURCE` constant, flagged in a
  comment right there) — re-verify against the real Kraken export code
  once available and update it if it differs.
- **Net Worth** — sums each currently-known snapshot's own
  `summary.total_value` (deliberately *not* reusing any snapshot's own
  self-reported `combined_net_worth` field, which per `VISION.md` is
  the real-estate export's own approximation using manually-entered
  placeholder values for whatever it didn't have real data for — not a
  value meant to be re-summed across independent sources). Shows how
  many sources actually contributed rather than silently overstating
  completeness if one source has no snapshot yet.

All three degrade to "No snapshot imported yet" / "No financial
snapshots imported yet" until a real export file gets dropped in —
same graceful-degradation stance as every hardware-optional widget
already on this dashboard (Volume, the paused Companion Avatar).
No menu actions on any of the three — there's no dedicated Finance
module/screen to open yet (this pass is dashboard-only), same as
Activity Log's card.

Verified for real: 13 new pure-formatting-function tests
(`tests/test_home_dashboard.py`) plus a real headless-Qt smoke test —
built a `HomeDashboard` against an isolated `FinanceManager` (tmp_path
import folder + tmp_path data dir, real repo state never touched),
confirmed the empty state renders correctly, then dropped real
real-estate + Kraken-shaped JSON files in, called
`scan_for_new_snapshots()`, and confirmed all three widgets update to
the correct computed values via a screenshot. 1152 tests passing (13
new).

## Companion Avatar dashboard widget: VMagicMirror camera integration (2026-07-16)

Picked up where the user's last VMagicMirror/aesthetics conversation
left off — a live camera feed of a VMagicMirror-rendered avatar,
displayed as a new Home dashboard widget card (`avatar_camera`,
alongside Power/Mission/Activity Log/etc. in the same widget
framework). Researched VMagicMirror's actual current capabilities
first rather than guessing: it's a Windows-only Unity/WPF app with no
Linux port, so nothing about it can run or be tested from this Linux/
WSL2 dev sandbox. Of the four real integration paths found (virtual
camera capture, native window capture, Spout GPU texture sharing, or
just positioning VMagicMirror's own transparent/always-on-top window
over the dashboard), the user chose **virtual camera capture** — read
via Qt's own `QCamera`/`QMediaCaptureSession`/`QVideoWidget`, the same
way VMagicMirror's Virtual Camera Output already works with OBS. This
needs zero VMagicMirror-specific protocol/SDK code, and works unchanged
for any other virtual-camera source pointed at it later.

New `core/avatar_manager.py` (`AppContext.avatar`) — camera device
enumeration + config-backed selection only (`dashboard.avatar_camera_device`),
no widget/rendering code, consistent with this project's core/gui
split. New `gui/widgets/avatar_camera_widget.py` (`AvatarCameraWidget`)
— the actual `QCamera`/`QVideoWidget` construction, with a graceful
placeholder ("no cameras found" / "no camera selected" / a specific
error string) whenever there's nothing to show, same degrade-gracefully
stance as the Volume widget's missing-`amixer` handling. Registered as
a new dashboard widget in `gui/home_dashboard.py`
(`_build_avatar_camera_widget`), device selection lives in the card's
own "⋯" menu (one action per detected device) rather than a new
Settings-module page. An explicit `.stop()` call is needed whenever the
card is torn down (grid rebuild on enable/disable, or the whole
dashboard closing) since a `QCamera` has no Qt-parent-driven cleanup
the way a plain widget does.

**Verified what's actually verifiable here**: 6 new unit tests
(`tests/test_avatar_manager.py`, `QMediaDevices.videoInputs()`
monkeypatched, same "mock the OS query" pattern as
`test_volume_manager.py`/`test_power_manager.py`) plus a real
headless-Qt smoke test confirming the widget builds, shows the correct
"no camera devices found" placeholder (this sandbox has zero cameras,
confirmed), and cleanly stops/rebuilds through a disable→enable cycle
with no leak or crash. 1121 tests passing (6 new). **Not verifiable
here, flagged rather than assumed**: an actual live video frame —
VMagicMirror only runs on Windows, so the real end-to-end path (enable
VMagicMirror's Virtual Camera Output, select it from the widget's menu,
confirm the live avatar renders) needs to happen on the real Windows
machine.

**2026-07-16, same day, paused at the user's explicit call**: trying to
actually connect a real VMagicMirror instance surfaced a genuine
architecture conflict, not just a setup inconvenience — VMagicMirror is
Windows-only, but `docs/HARDWARE.md`'s Project 2 (the actual Home Cloud
machine this is meant to run on) is planned to run **Ubuntu**,
specifically for ROCm GPU-compute support, which has much weaker
Windows support. The widget is unregistered from the default dashboard
(`core/application.py`'s `_register_dashboard_widgets()`) but not
deleted — `core/avatar_manager.py`/`gui/widgets/avatar_camera_widget.py`
stay in place as real, reusable code. **Three options identified, none
chosen yet** — revisit once ready: (1) drop VMagicMirror, find/build a
Linux-native VRM avatar renderer (e.g. a web-based three-vrm.js viewer
in a Qt web view); (2) keep VMagicMirror on a separate Windows
machine/VM, stream its output to the Ubuntu box over the network
(NDI/RTSP) instead of a local virtual-camera read; (3) reconsider
Project 2's OS to Windows, accepting the ROCm trade-off. Don't resume
building against this widget without picking one of these first.

## Boot sound gets a proper ending; volume mute button fixed; text size increased app-wide; dashboard cards become click-to-navigate (2026-07-16)

Five separate fixes/polish items from the same conversation, at the
user's explicit request after praising the new boot sound but wanting
follow-through on several rough edges:

**Boot sound now ends with a "ping"**: `core/boot_sound.py`'s single
growing/pulsing sweep is now two synthesized pieces —
`_generate_sweep()` (the original "woooooooom," now with no fade-out of
its own) immediately followed by `_generate_ping()` (a short bell-like
chime: a fundamental plus two detuned harmonics, fast exponential
decay, matching the user's own description "like a woooooooom ping").
`_PING_FRACTION = 0.15` of the total duration is the ping; total
duration bumped 3.5s → 3.9s so the sweep isn't shortened to make room
for it. 7 new tests in `tests/test_boot_sound.py` (13 total).

**Volume widget's mute button finally shows real state**: it used to
show a bare, never-updated 🔇 regardless of actual mute state.
`gui/home_dashboard.py`'s `_refresh_volume()` now swaps the icon
(🔊 unmuted / 🔇 muted) and sets an explicit tooltip on every refresh —
same "state should be visible, not just clickable" bar the Talk
button's recording state already set.

**Text size increased across the whole app**: every `font-size: Npx`
value in `gui/styles.py`'s `DARK_FIELD_THEME` bumped up (roughly +1 to
+2px each, e.g. base 14→15, titles 26→28, module names 15→16) via a
single Python regex pass to avoid chained-replacement collisions — 31
values changed. Scoped to `dark_field` only, same as every ForMIA-era
addition. **Surfaced a real latent bug**: the Mission dashboard
widget's body text started clipping once it wrapped to 2 lines at the
new size — the same `heightForWidth()`/`sizeHint()` disagreement
already fixed once for `ChatBubble`. Fixed via a new
`_set_widget_body_text()` helper (`gui/home_dashboard.py`) applied to
all 8 dashboard widget body-text call sites, recomputing an explicit
minimum height on every refresh (not just once, since these labels'
text changes every 5s).

**Dashboard widget cards are now click-to-navigate, not "⋯" menus**:
at the user's explicit request ("I want to be able to click on a
widget like a button and it bring me to its page"), the Power/Mission/
Current Project cards' "⋯" menu (which only ever had one action, "Open
X") is gone — `_build_simple_card()` now optionally builds the whole
card as a `QPushButton` (same shape as `ModuleButton`/`ConversationCard`)
when an `on_click` callback is given, falling back to the original
plain `QFrame` for widgets with nothing to navigate to (Activity Log,
Real Estate, Kraken Agent, Net Worth). Confirmed via a real headless-Qt
screenshot that a bare clickable `QPushButton` card collapses to a
sliver on this platform without an explicit `setMinimumHeight()` (same
propagateSizeHints() quirk `ConversationCard`'s docstring already
documents) — fixed the same way. Avatar Camera's device-selection "⋯"
menu is untouched (a real multi-item menu, not a "go to page"
shortcut, so it doesn't fit this pattern). 1287 tests passing.

## Missions gamification: MIA-assigned quests + game-y card accents (2026-07-16/17)

At the user's explicit request ("MIA should assign me missions
sometimes... there's not much fun in having to assign yourself
missions... we want to gamify life") plus a Borderlands-style
quest-log "feel" for the cards — scoped via two clarifying questions
first: (1) keep the existing bubbly MissionCard/ObjectiveCard shape and
add game-y accents rather than a full re-skin, and (2) make MIA's
proactive assignment rule-based (fully offline, no LLM — out of scope
per this doc's own v0.5 note that no AI/assistant logic exists yet),
not activity-mined or manual-trigger-only.

**`core/mission_manager.py`**: `Mission` gains `assigned_by` ("user" |
"mia") and `task_id` (mirrors `trip_id`'s optional-FK pattern, linking
to `core.task_manager.Task`). New `"task_done"` metric type — same
"compute live from the linked record, never store it" philosophy as
the existing `trip_duration_hours` type. New
`check_for_auto_assignment()`, called from a new always-alive
`core/application.py` timer (`_mission_check_timer`, 5-minute cadence
plus one immediate run at boot, same pattern as
`_check_daily_occasions`), runs two rules in priority order and creates
at most one Mission per call:
1. **Idle rule** — no active mission exists, and either no mission's
   ever been auto-assigned or it's been ≥3 days since the last one —
   picks the next not-yet-used template from a small pool of
   self-contained, flavorful "life" goals (`_AUTO_MISSION_TEMPLATES`:
   Digital Declutter, Deep Work Streak, Tidy Up, Move Your Body, Inbox
   Zero Push), cycling back once every template's been used.
2. **Stale task rule** — otherwise, if `context.tasks` is available,
   finds the least-recently-updated incomplete Task with no Mission
   already wrapping it and, once it's sat untouched ≥5 days, turns it
   into a one-objective Mission (`task_done`) — a quietly-ignored task
   becomes a nudge instead of needing the user to notice it themselves.

**`gui/widgets/mission_card.py`**: a bright "MIA ASSIGNED" badge pill
(`#MissionCardBadge`, high-contrast gold) shows next to the title for
`assigned_by="mia"` missions, and a real aggregate `QProgressBar`
("N/M objectives") now sits under the meta line — one level up from
`ObjectiveCard`'s existing per-objective bar. `completed_objectives`/
`total_objectives` are computed by the caller
(`modules/missions/module.py`), keeping the card itself context-free.

23 new tests (`tests/test_mission_manager.py`, 46 total in that file).
Verified visually via a real headless-Qt screenshot: badge and progress
bar both render correctly, `check_for_auto_assignment()` produces a
real Mission with the right `assigned_by`/objectives. 1304 tests
passing.

## Maps module: a real waypoint schematic map, replacing the placeholder (2026-07-17)

Picked as the top item from a full project audit (roadmap/known-issues/
vision/git-log/grep sweep) of "what still needs work" — of everything
flagged, this was the one item that was both real and immediately
buildable with zero hardware or open decisions blocking it (`music` was
the only other pure-stub module at the time, confirmed blocked on
missing `libpulse` without root then — that blocker is gone as of
2026-09-09, see the Music module built as v0.20).

**Deliberately not real cartography** — `modules/navigation/module.py`'s
own docstring already scoped "offline maps, trails, elevation" as
waiting on real GPS/mapping hardware/data this dev sandbox doesn't
have. Maps' zero-hardware slice instead: a schematic plot of whatever
waypoints already exist (`core.waypoint_manager.WaypointManager`), a
click-to-select distance/bearing lookup between any two of them
(finally surfacing `distance_and_bearing()`, which existed since the
Navigation module shipped but had no caller anywhere in the app), and
an optional Trip route overlay (`Trip.waypoint_ids`, the "ordered
planned route"). Maps has no waypoint CRUD of its own — that stays
Navigation's job; Maps is the spatial-visualization companion to it.

New `gui/widgets/waypoint_map_canvas.py` (`WaypointMapCanvas`, a
`QPainter`-based custom widget, same technique
`gui/presence_widget.py` already established) — `project_waypoints()`
is a free function doing a simple equirectangular-style, fit-to-box
projection with one shared scale factor (not stretched per-axis, so
relative shape isn't distorted), pure math tested without Qt. Clicking
a waypoint dot sets "from" then "to" for a distance/bearing readout;
picking a Trip from a combo box overlays its route as a dashed line. No
live refresh from other modules (`gui/main_window.py` caches each
module's widget after first open, and neither
`WaypointManager`/`TripManager` publishes a changed-event) — a plain
"Refresh" button covers it instead, consistent with several other
read-only aggregate-view modules.

10 new tests (`tests/test_waypoint_map_canvas.py`,
`tests/test_maps_module.py`). Verified via a real headless-Qt smoke
test with screenshots: waypoints plot in the correct relative
positions, the route overlay draws correctly, and clicking two
waypoints produces the correct real distance/bearing text
("Base Camp → Summit: 8.7 km — bearing 027°"). 1314 tests passing.

## Maps module, part 2: a real offline basemap + a state park/trail map PDF catalog (2026-07-17)

User follow-up right after Maps shipped: "Can we get the offline Maps
together? Also include state park maps and trail maps" — a genuine
scope jump from part 1's schematic waypoint plot to actual cartographic
imagery. Investigated feasibility directly before writing any code
rather than guessing:

- **This dev sandbox has real internet access** (confirmed via
  `curl`) and ample disk space, so real map data fetching is possible.
- **`PySide6.QtWebEngineWidgets` (the easy path to an embedded
  Leaflet.js slippy map) fails to import** — missing `libnspr4.so`, no
  sudo, the same class of blocked system dependency `libportaudio2`/
  `libpulse` used to be before those got resolved (2026-09-09, see the
  Music module built as v0.20) — `libnspr4.so` itself remains genuinely
  blocked, unrelated to that fix. Ruled out, not worked around.
- **OpenStreetMap's own tile server explicitly prohibits bulk/
  automated downloading for offline caching** — exactly the "download
  this region" feature being built — so it was deliberately not used
  as the tile source.
- **USGS National Map's "USGSTopo" tile service
  (`basemap.nationalmap.gov`) confirmed reachable directly and is a
  public-domain federal service meant for this kind of programmatic
  use** — chosen instead, and it's a real topographic map (shows
  trails), not just roads.
- **State park agency sites (Kentucky, Tennessee) block automated
  scraping** — both `WebFetch` and a browser-UA'd `curl` got 403s/404s
  trying to enumerate real per-park trail map PDF links. Rather than
  hardcode guessed/scraped URLs that might not resolve, the Trail Map
  library was built as a real add-by-URL/add-by-local-file catalog —
  the user (or a future, carefully-scoped scraping pass against a
  confirmed-scrapable site) supplies the actual park/URL/file.
- **`PySide6.QtPdf`/`QtPdfWidgets` ARE importable** (unlike WebEngine)
  — so trail map PDFs open in a real embedded viewer, no external
  viewer or new dependency needed.

Scoped via `AskUserQuestion` before building: user chose **both** a
real pannable basemap and an official PDF trail-map catalog, starting
with **Kentucky and Tennessee**.

**New `core/map_tile_math.py`** — pure Web Mercator "slippy map" tile
math (the same addressing scheme OSM/USGS/every standard XYZ tile
provider uses): `lat_lon_to_tile_xy()`/`tile_xy_to_lat_lon()` (whole-
tile addressing), `lat_lon_to_world_pixel()`/`world_pixel_to_lat_lon()`
(continuous coordinates for smooth pan/zoom), `tiles_covering_bbox()`.

**New `core/map_tile_cache.py`** (`AppContext.map_tiles`) — disk-backed
tile cache using stdlib `urllib.request` (not the `requests` package,
matching `requirements.txt`'s "keep this list minimal" stance).
`fetch_tile()` downloads-and-caches one tile; `ensure_region_cached()`
bulk-prefetches a bounding box across a zoom range, skipping already-
cached tiles, tolerating individual tile failures without aborting the
batch. `DEFAULT_PREFETCH_ZOOM_LEVELS` (6-10) was picked by directly
measuring real tile counts for a Kentucky+Tennessee-sized bounding box
first (~557 tiles, ~19MB) rather than guessing at a "reasonable" range.
**Confirmed the ArcGIS tile endpoint's `{z}/{y}/{x}` path-segment
order directly against the live service** — the reverse of the more
common `{z}/{x}/{y}` XYZ convention this module's own local cache path
and `core.map_tile_math` use.

**New `core/trail_map_library.py`** (`AppContext.trail_maps`) — same
persisted-JSON-metadata-plus-files-on-disk split as
`ReferenceLibraryManager` (`data/trail_maps.json` for metadata,
`trail_maps/` at the repo root for the actual PDFs — configurable via
`maps.trail_map_root_path`, not under `data/` since PDFs are real
files and `data/` is what `core/backup_manager.py` backs up wholesale).
`add_from_url()`/`add_from_local_file()` both validate a real `%PDF`
magic-number header before cataloging anything, so a 404/error page
served with a 200 status doesn't silently become a broken catalog entry.

**New GUI**: `gui/widgets/tile_map_view.py` (`TileMapView`, a
`QPainter`-based pannable/zoomable basemap, mouse-drag pan + scroll-
wheel zoom, missing tiles get a placeholder + a background fetch
request rather than blocking the paint thread — via new
`modules/maps/tile_fetch_worker.py`'s `TileFetchWorker`, a persistent
queue-processing `QThread`, distinct from the one-shot
`modules/maps/tile_prefetch_worker.py`'s `TilePrefetchWorker` used for
the bulk "Download Kentucky"/"Download Tennessee" buttons). New
`gui/add_trail_map_dialog.py` (URL or local-file entry, mutually
exclusive), `gui/trail_map_viewer_dialog.py` (embedded `QPdfView`), and
`modules/maps/trail_map_fetch_worker.py` (the URL-download path off the
GUI thread). `modules/maps/module.py` restructured into a 3-tab
`QTabWidget`: Waypoints (part 1's schematic plot, unchanged), Basemap
(new), Trail Maps (new).

**Verified for real, not just unit-tested**: a real headless-Qt smoke
test fetched an actual tile from the live USGS service, rendered it in
`TileMapView` (screenshot confirms real topographic imagery — rivers,
roads, place names, "Allegheny National Forest" labels — not a
placeholder), downloaded a real small test PDF end-to-end through
`TrailMapFetchWorker` into the catalog, and opened it in the real
embedded `QPdfView` (screenshot confirms actual PDF content rendering).
The Maps module was also confirmed to boot cleanly through the real
`ModuleManager` discovery path (`tests/run_module.py maps`, updated
with the two new services per that file's own maintenance convention).
27 new unit tests (`tests/test_map_tile_math.py`,
`tests/test_map_tile_cache.py`, `tests/test_trail_map_library.py`,
plus 2 more in `tests/test_maps_module.py`) — network calls mocked in
the committed suite (real fetches only happen in the one-off smoke
test), same "mock the external query" pattern as
`test_avatar_manager.py`/`test_power_manager.py`. 1341 tests passing.

## Trail Map catalog seeded with real Kentucky/Tennessee parks, LBL emphasized (2026-07-17)

Immediate follow-up: "Add a few real trail maps from Kentucky and
Tennessee parks... Especially LBL." Every URL was verified reachable
(`curl`, HTTP 200 + `application/pdf` content-type) before being added
— none guessed, consistent with `core/trail_map_library.py`'s own
"never pre-seed with unverified scraped links" design. Added via the
real `TrailMapLibrary.add_from_url()` (the exact same path the in-app
"Add Trail Map" button uses), not hand-edited into `data/trail_maps.json`.

Seeded 7 real trail maps: **Land Between the Lakes NRA** (4 maps —
general visitor/recreation map, North End of the North/South Trail,
Turkey Bay OHV Area, Wranglers Horse & Wagon Trails — cataloged as
state "Kentucky/Tennessee" since LBL genuinely straddles both),
**Cumberland Falls State Resort Park** and **Natural Bridge State
Resort Park** (Kentucky), **Pickett CCC Memorial State Park**
(Tennessee). `tnstateparks.com` itself blocks MIA's own User-Agent
string (confirmed: the exact same URL that returns 200 for a
browser-UA'd `curl` returns 403 through `add_from_url()`'s
`"MIA-Home/0.2"` User-Agent) — Fall Creek Falls was dropped for this
reason and Pickett's map was sourced from a mirror
(`cloudhiking.com`) instead, rather than having MIA spoof a browser
identity to bypass a site's own anti-bot measure.

**Found and fixed a real display bug this surfaced**: the Trail Maps
list only showed "park name (state)", so the 4 distinct LBL entries
were visually indistinguishable from each other. New
`format_trail_map_row()` appends each entry's `notes` when present
("Land Between the Lakes NRA (Kentucky/Tennessee) — Turkey Bay OHV
Area trail map"). 2 new tests, confirmed via a real headless-Qt
screenshot that all 7 entries are now distinguishable. 1343 tests
passing. The 7 real PDFs (~21MB total) live in the gitignored
`trail_maps/` folder, same as Reference Library packs/trip photos —
not committed to git, real user content.

## Fixed a real bug: the trail map PDF viewer silently hid every page past the first (2026-07-18)

User report: "The trail maps you added for LBL are not maps at all."
Investigated by actually rendering every seeded PDF's pages (via
`QPdfDocument`, saved to PNG, visually inspected) rather than trusting
the earlier `%PDF`-header validation — and found the data was fine: 6
of the 7 seeded entries are genuine, detailed trail maps (contour
lines, legends, named trails), the 7th (LBL's general brochure) has a
real park-facilities overview map on page 2. **The actual bug was in
`gui/trail_map_viewer_dialog.py`**: `QPdfView` defaults to
`PageMode.SinglePage` (confirmed directly), and with no page-turn
control anywhere in the dialog, that silently showed only page 1 —
which for every one of these trifold park brochures is just a cover/
title/rules page, with the real map living on page 2. So every single
entry *looked* like it had no map at all, regardless of the real
content. Fixed by switching to `PageMode.MultiPage` (continuous
scroll, like any normal PDF viewer) plus a page-count label so a
multi-page document doesn't look like a dead end. Verified via a real
headless-Qt screenshot: scrolling the North End of North/South Trail
entry now reaches its actual cartographic map on page 2. 1343 tests
passing (no new tests — this is pure Qt widget-configuration behavior,
same "verify via real headless-Qt screenshot, not a mocked pytest
test" treatment as this project's other QPainter/QPdfView-level fixes).

## Replaced brochure-style trail maps with genuine topographic ones (2026-07-18)

Follow-up push-back from the user after the viewer fix above: "No the
issue is that they aren't maps, they are park info guides." Correct,
even accounting for the viewer bug — most of the 7 originally-seeded
PDFs (LBL's general brochure, Cumberland Falls, Natural Bridge,
Wranglers) are illustrated visitor-guide maps (facility icons, mileage
tables, stylized roads), not real cartography, even on their actual
map page. Deleted all 7 (`TrailMapLibrary.delete_trail_map()` via the
real catalog, not a file-system wipe) and searched specifically for
**official government-published topographic maps** this time — real
contour lines/shaded relief, not illustration — verifying each
candidate by actually rendering every page with `QPdfDocument` and
visually inspecting it before cataloging (applying the exact lesson
from the viewer-bug investigation: verify the real artifact, don't
trust metadata/validation alone). Seeded 4 genuine topographic trail
maps: **Mammoth Cave National Park** (Kentucky, official NPS shaded-
relief map), **Red River Gorge / Daniel Boone National Forest**
(Kentucky, official USDA Forest Service numbered-trail map,
1:42,000), **Great Smoky Mountains National Park** (Tennessee,
official NPS map), **Big South Fork National River and Recreation
Area** (Kentucky/Tennessee, official NPS 9-quad-sheet topographic set).
Two rejected candidates during this pass, confirmed non-map content by
rendering before deciding: a Red River Gorge "hiking map" PDF whose
second page was purely a restaurant/shopping business directory (kept
anyway since page 1 was a real official USFS map — same "multi-page
document, judge every page" lesson as the viewer fix), and Kentucky
State Parks' own site had no scrapable topo-map links at all (same
anti-bot blocking already documented for Tennessee's park site).

## Worldwide low-zoom overview + selectable high-detail regions (2026-07-18)

Follow-up ask after the KY/TN basemap shipped: "what do i need to make
the fully offline maps available? I want worldwide offline maps."
Scoped via `AskUserQuestion` first, given the real constraints already
found (USGS is US-only; OSM's tile server prohibits bulk/deep
caching): user picked "worldwide low-zoom + selectable regions at high
detail" — the same model every real offline-map app (OsmAnd, Gaia GPS)
already uses, rather than attempting true worldwide high-detail
coverage (would be many terabytes, measured directly before ruling it
out).

**`core/map_tile_cache.py` now supports multiple named tile sources**
(`TILE_SOURCES`, each `(url_template, file_extension)`, cached under
`data/map_tiles/{source}/...` so they never collide) — every method
(`tile_path`/`fetch_tile`/`ensure_region_cached`) takes an explicit
`source` argument now rather than always assuming USGS. Two sources
registered: `"usgs_topo"` (unchanged, US high-detail) and `"osm"`
(`tile.openstreetmap.org`) — used **only** for
`WORLDWIDE_OVERVIEW_ZOOM_LEVELS` (0-4, ~341 tiles/~5MB for the entire
planet, measured directly before picking this range). This is a
deliberate, narrow exception to "never hit OSM's tile server
programmatically" (established when USGS was first chosen over OSM):
a one-time ~5MB worldwide fetch is the same order of magnitude as a
single normal browsing session, not the kind of bulk/systematic
scraping OSM's usage policy targets — but OSM is never used for
`DEFAULT_PREFETCH_ZOOM_LEVELS`-style deep regional caching, which
*would* cross that line. High-detail coverage outside the US remains
a real, documented gap (no compliant bulk tile source found), not
silently worked around by overusing OSM's server beyond this narrow
case.

**`gui/widgets/tile_map_view.py`** gained `set_source()`/`source()` —
switching sources is an explicit user choice (a dropdown in the Maps
module), not an automatic per-tile blend between two providers with
different visual styles; each source also gets its own correct
attribution text (`"USGS National Map"` vs `"© OpenStreetMap
contributors"`, OSM's own required wording). `modules/maps/module.py`
gained a source dropdown, a "Download Worldwide Overview" button, and
a "Download Current View" button — the latter uses
`TileMapView.visible_bounds()` (already existed) so *any* region can
be cached at high detail by panning/zooming there first, not just the
two original KY/TN preset buttons (which still exist, now just calling
the same shared `_run_prefetch()` helper as the two new buttons).

7 new unit tests (`tests/test_map_tile_cache.py`, network calls
mocked). Verified for real: a headless-Qt smoke test switched the
basemap source live, ran a real worldwide OSM overview fetch (reduced
zoom range for the test's own runtime — the full range is separately
confirmed small via a dedicated unit test) and a real USGS
"current view" fetch over an arbitrary region (central Kentucky
counties, not one of the two presets), confirmed via screenshots
showing real rendered tiles and correct attribution text for both
sources. 1347 tests passing (7 new).

## Objective/mission progress reads "X of Y" instead of "X/Y"; Assistant gets a volume slider (2026-07-18)

Two small, concrete asks alongside the bigger Assistant-coverage audit
below. **"X/Y" → "X of Y"**: every place a Mission/Objective's progress
was rendered with a bare slash — `ObjectiveCard`/`MissionCard`'s
`QProgressBar` text, `modules/dashboard/module.py` and
`gui/home_dashboard.py`'s summary lines, and the Assistant's own
`list_missions`/`log_mission_progress` reply text — now reads "1 of 3"
instead of "1/3".

**Assistant volume slider**: `core/voice_manager.py` gained
`apply_playback_volume()` (pure gain logic — float-space multiply then
clip back to int16 range, since a bare `(audio*volume).astype(int16)`
would wrap a loud sample around to a negative value instead of
clipping cleanly) and `voice.playback_volume` (config, new default
`1.4` — louder than Piper's raw output, the "make it a bit louder"
half of the ask). Applied at playback time in `play()`, not baked into
the synthesized `.wav`, so the new Settings slider
(`modules/settings/module.py`, next to the existing Voice/AI Effect
controls) changes the very next spoken reply's volume immediately —
`valueChanged` only updates a live "N%" label while dragging,
`sliderReleased` is what actually saves + triggers a spoken preview,
so dragging doesn't re-synthesize on every tick.

5 new tests (`tests/test_voice_manager.py`), plus the mission/objective
formatting change updated 7 existing test assertions across
`tests/test_missions_module.py`/`test_dashboard_module.py`/
`test_home_dashboard.py`/`test_assistant_action_handlers.py`. Verified
via a real headless-Qt screenshot: the slider moved to 200%, config
persisted, status label confirmed. 1352 tests passing (5 new).

## Assistant personality: "confident native fluency" + closing real help-doc gaps (2026-07-18)

At the user's explicit request: "I want it to be as if this program is
an extension of the assistant and it should know it like the back of
its hand" — concretely triggered by the Assistant answering "I don't
know" to questions about Maps/Workshop/Missions' newer features. Two
real, separate causes, both fixed:

**A wording gap**: `core/assistant_chat.py` gained `_IDENTITY_APP_FLUENCY`
— info-question-path-only (same regression-safety split
`_IDENTITY_WARMTH` already established; the action-request path's bare
`_IDENTITY_LINE` stays untouched, since that's the fragile, already-
tuned tool-calling surface). Worded as confidence *conditional on* the
grounded material actually covering something ("when the reference
material below covers something, answer with the confident, specific
familiarity of someone describing their own house") rather than a
blanket license to sound sure of everything — `GROUNDING_INSTRUCTION`
right after it in the system message is still the harder "only use
what's below, say you don't know otherwise" rule.

**A real data gap**: `docs/user_help/` had zero coverage of the Maps
and Workshop modules, and `missions.md` predated the whole gamification/
auto-assignment pass — no personality wording fixes that. New
`docs/user_help/maps.md` and `docs/user_help/workshop.md`;
`missions.md` gained sections on MIA-assigned Missions and the
aggregate progress bar. Trimmed the now-stale duplicate "Maps"/
"Workshop & Electronics" subsections in `navigation.md`/`organizing.md`
into one-line pointers, so there's exactly one authoritative chunk per
topic rather than two competing/conflicting ones for retrieval to pick
between (same lesson as the earlier "near-duplicate footer sections"
retrieval-ranking bug).

**Verified for real** — this is an LLM-prompting change, not just unit
tests: ran 5 real questions against the live model. "What does the
Maps module do?"/"What can the Workshop module help me with?"/"Does
MIA ever assign me missions on its own?" all now get confident,
correct, specific answers (previously would have gotten "I don't
know"). Re-verified two existing cases didn't regress: "What does the
Notes module do?" still answers correctly, and an out-of-scope
question ("What can you tell me about the Loch Ness Monster?") still
correctly declines rather than hallucinating — confirming
`GROUNDING_INSTRUCTION`'s anti-hallucination guarantee held even with
the new confidence framing layered on top. 1352 tests passing (no new
tests — this is system-prompt wording + markdown content, verified
live rather than mocked, same treatment as other prompt-wording
changes in this project's history).

## Systematic trigger-phrase gap audit: 11 more real gaps found and fixed (2026-07-18)

Follow-up to fixing "what is my current mission" — asked to "think of
many ways to improve and test the Assistant." Rather than guess, probed
~13 plausible natural alternate phrasings across nearly every existing
domain (not just missions) against the live model, using a scratch
copy of `tests/live_model_check.py`'s own harness. **11 of 13 failed**
— confirming the "current mission" bug was one instance of a systemic
pattern, not a one-off: "when is my next alarm," "am I plugged in,"
"what parts do I have," "what do I have going on this week," "how many
expeditions have I been on," and 6 others all either called nothing or
the wrong tool. Two distinct failure shapes found: most were pure
gating gaps (no trigger phrase matched at all, so the domain's tools
were never attached); one was a genuine tool-*selection* ambiguity
once gating was fixed — "what do I have going on this week" correctly
attached both `calendar` and the always-on `system` domain, but the
model preferred `recall_recent_activity` over `list_calendar_events`
until that tool's description was sharpened to explicitly say
"upcoming... not for past activity."

Fixed all 11 with new trigger phrases (`list_calendar_events`,
`list_components`, `list_tasks`, `list_alarms`, `get_power_status`,
`list_expeditions`, `list_waypoints`, `list_notes`,
`get_system_health`) plus the one description sharpening above.
`list_notes`'s new "wrote down" phrasing deliberately overlaps
`add_note`'s own "write down" trigger rather than avoiding it — same
already-proven "let both domains attach, trust the model to
disambiguate via tool descriptions" pattern this registry already
relies on elsewhere (`set_theme`/`open_module`,
`list_profiles`/`get_device_profile`).

**Verified thoroughly, not just the fixes themselves**: re-ran the full
official 69-case golden set after the trigger additions (no
regressions), then again after the description change (still no
regressions), added 4 new false-positive/collision sanity checks
targeting the specific new broad phrases ("is everything ok" as small
talk, "plugged in" unrelated to power, "working on" unrelated to
tasks, the notes/add_note overlap resolving correctly) — all pass. All
17 new cases folded into the permanent `tests/live_model_check.py`
golden set (69 → 84), which now passes 84/84. 1352 pytest tests
passing (unchanged — this is entirely trigger-phrase/description
tuning, verified live, not unit-testable in the traditional sense).

## Workshop production pipeline gets real Assistant actions (2026-07-18)

The single biggest gap from the earlier module-coverage audit: the
Materials/Jobs/Products/Ledger pipeline had zero executable path for
the Assistant — it could talk about Workshop (per the new help doc
above) but couldn't do anything in it. 10 new actions across 4 small
domains (`materials`, `products`, `jobs`, `ledger` — not one big
"workshop" domain, so a materials-only question doesn't also attach
unrelated ledger/job tools): `add_material`/`list_materials`,
`add_product`/`list_products`, `add_job`/`list_jobs`,
`consume_material`/`produce_product` (both resolve a job name + a
material/product name to real records, same "name-before-noun"
resolution pattern the rest of this registry already uses), and
`record_sale`/`get_ledger_summary`.

**Found and fixed 3 real issues via live-model testing before trusting
any of this**, same "re-verify against the real model, don't assume
scaling stays safe" discipline as every prior registry expansion:
1. `consume_material`/`produce_product`'s own trigger phrases ("my job
   used"/"my job produced") assumed the job's name would never appear
   between "my" and "job" — real phrasing ("My Birdhouse Batch job
   used 4 sheets...") breaks that assumption. Loosened to "job used"/
   "job produced".
2. `add_job`'s bare "new job" trigger falsely gated open on "I love my
   new job at the bakery" — and, worse, once the (wrongly) attached
   jobs-domain tools were in front of the model, it hallucinated a
   completely unrelated `set_birthday` call rather than declining.
   Replaced with "start a new job" (matching the same "Start a new X
   called Y" phrasing `add_mission`/`add_project`/`add_expedition`
   already use), which doesn't collide with the false-positive case.

17 new unit tests (`tests/test_assistant_action_handlers.py`, testing
the actual handler logic — stock deduction/crediting, revenue/expense
totals — not just gating) plus 10 new golden-set cases (84 → 96,
including 2 false-positive sanity checks for the "job"/"material"
words in ordinary conversation). Full official golden set re-verified
clean at 96/96 after every fix. 1369 pytest tests passing (17 new).

## Home dashboard widget sizing fix after Assistant round-trip (2026-07-18)

User report: "I keep having a sizing issue with the dashboard widgets
when going from the Assistant to the Home Screen." Couldn't reproduce
a static geometry discrepancy in a headless round-trip test at a fixed
window size, so diagnosed the more likely mechanism instead:
`HomeDashboard._data_timer` keeps firing on its normal 5-second
schedule even while Home is hidden behind the `QStackedWidget`, and the
existing `_set_widget_body_text()` min-height fix reads `label.width()`
at whatever moment the timer happens to land — stale if that's while
hidden or mid-page-transition, producing wrong/clipped card sizing
that only self-corrects on a later lucky tick.

Fix: `HomeDashboard.showEvent()` now forces an immediate
`_refresh_data()` the moment the page becomes visible again, rather
than waiting on the timer. Verified via a headless spy test that this
fires on both initial show and on becoming visible again after a
hide/show round-trip. Added a secondary defensive measure in
`gui/main_window.py`: all four page-switch methods now call
`updateGeometry()` on both the stack and its wrapping `QScrollArea`
(from the Home/Back crash fix) right after `setCurrentWidget()`, in
case that call alone doesn't generate a real resize event for the
newly-current page. See `docs/KNOWN_ISSUES.md` — unconfirmed on real
hardware, since the original bug was never reproduced here. 1369
pytest tests passing (no new ones — the fix isn't reproducible under
headless Qt, so it was verified with a targeted spy test instead of a
permanent regression test).

## Maps gets real Assistant actions (2026-07-18)

Closed the last module-coverage gap from the earlier audit: the trail
map catalog (`core/trail_map_library.py`) had zero Assistant-callable
actions. New `maps` domain, 3 actions: `list_trail_maps` (optional
park/state keyword filter), `add_trail_map_from_url`, and
`delete_trail_map` (resolves by park name, same case-insensitive
exact-match convention every other delete action uses). Deliberately
did **not** add an action for downloading offline map tiles/basemaps —
that's a real, considered scope decision, not an oversight: prefetching
a region's tiles runs on a background `QThread` worker in
`modules/maps/module.py` because it can take many seconds to minutes,
and this project's Assistant action handlers are synchronous calls
that block the chat reply while they run (no async/background
execution model exists for tool calls yet) — wiring a real tile
download through one would either freeze the chat for a long stretch
or need new plumbing this ask didn't call for. `add_trail_map_from_url`
does do a real (bounded, 15s-timeout) network fetch synchronously,
which is a first for this registry, but it's a single small PDF, not a
multi-tile region download.

8 new unit tests (`tests/test_assistant_action_handlers.py`, mocking
`urllib.request.urlopen` for the add-from-url success/rejection paths
rather than hitting a real network in the committed suite) plus 4 new
golden-set cases (96 → 100, including a false-positive sanity check
for the ordinary use of the word "map"). Full official golden set
verified 100/100 clean on the first live-model run — no trigger-phrase
gaps or false positives found this time, unlike the earlier
Workshop-pipeline pass. Registry now 67 actions across 18 domains.
1377 pytest tests passing (8 new).

## Stop-speaking button, "power percentage" trigger gap, grid spacing fix (2026-07-18)

Three real user reports in one pass. (1) No way to interrupt MIA
mid-sentence once TTS playback started — new "⏹ Stop" button next to
Hold to Talk in `modules/assistant/module.py`, wired to a new
`VoiceManager.stop_playback()` (`sounddevice.stop()`, which aborts the
stream `play()`'s blocking `sd.wait()` is sitting in on
`core/tts_worker.py`'s `QThread`, same as natural playback completion
— a global stop, so it also cuts off the Home dashboard's spoken
startup briefing if that happens to be playing). Enabled only while a
`TTSWorker` is actually running. (2) "What is my power percentage?"
got a hedging "I don't know" reply that only awkwardly related power
to battery — real trigger-phrase gap, `get_power_status` only had
"battery"/"power status" phrasing, nothing matching bare "power" +
"percentage"/"level". Added "power percentage", "power level", "percent
power", "how much power" — same pattern as every other trigger-gap fix
this project has made, re-verified against the live model (102/102,
including a new false-positive sanity check: "This new drill has a lot
more power than my old one" correctly triggers nothing). (3) Apps grid
and Home dashboard widgets reported "spaced very far apart" after
navigating away and back — real regression from the Home/Back crash
fix earlier this session: wrapping the whole `QStackedWidget` in its
own resizable `self._stack_scroll` can hand whatever page is current
more vertical space than its content needs, and neither
`gui/main_window.py`'s Apps grid (`_build_menu()`) nor
`gui/home_dashboard.py`'s widgets grid (`_build_widgets_grid()`) had an
alignment set on their `QGridLayout`, so the extra space grew as gaps
between rows instead of sitting as blank margin below the content —
same underlying issue `gui/home_dashboard.py`'s own top-level
`outer.setAlignment(AlignTop)` already guards against, just missing at
the grid level. Fixed by setting `AlignLeft | AlignTop` on both grids.
**Actually reproduced and confirmed this time** (unlike the two
"unconfirmed" crash-fix entries in `docs/KNOWN_ISSUES.md`): a headless
test forcing a 2400×1600 window measured the Apps grid's extra
inter-row gap at ~122px before the fix, 16px (the configured spacing,
correct) after. 1377 pytest tests passing (no new ones — layout-only
fix, verified via an ad hoc geometry smoke test instead of a permanent
one, same treatment as the earlier dashboard-sizing showEvent fix).

## Voice-command expansion: Navigation, Expeditions, Toolbox (2026-07-18)

First slice of "make the Assistant deeply more interactive for the
most important offline survival tool use cases" (Maps/Missions were
already well covered — Maps last commit, Missions from the earlier
trigger-audit pass; Knowledge already works through the grounded
info-question path, not a tool call, so no action was added there).
7 new actions across 3 domains:

- **Expeditions** (`expeditions` domain, 7 → 11 actions):
  `delete_expedition`, `delete_trip`, `toggle_gear_packed` (mark a gear
  checklist item packed/unpacked by trip + label), `get_trip_summary`
  (logged distance, average speed, planned route distance).
- **Navigation** (`waypoints` domain): `get_sun_moon_info` — sunrise/
  sunset times and moon phase for a saved waypoint, reusing
  `modules/navigation/module.py`'s existing `format_sun_moon_summary()`
  pure function. Genuinely survival-relevant (daylight remaining, moon
  phase for night travel).
- **Toolbox** (new `toolbox` domain): `convert_units` (any of the Unit
  Converter's 13 categories, resolving everyday unit words like
  "miles"/"celsius" against the calculator's exact display strings via
  a new `resolve_unit_key()` in `modules/toolbox/calculators/
  unit_converter.py`) and `calculate_ohms_law` (solves V=IR for
  whichever value is missing).

**Found and fixed 3 real issues via live-model testing**, same
discipline as every prior registry expansion:
1. `calculate_ohms_law`'s original triggers all assumed the user would
   say "Ohm's law" or "solve for X" explicitly — "I have 2 amps through
   a 10 ohm resistor, what's the voltage?" (a natural way to actually
   ask) matched nothing. Added specific electronics vocabulary
   ("amps through", "ohm resistor", "how many volts", ...) — bare
   "current" was deliberately avoided (collides with "current events"/
   "current job").
2. `convert_units`'s original bare "convert" trigger caused a real
   false positive: "I'm trying to convert my garage into a workshop"
   gated the domain open and the model actually called
   `convert_units` for it — same class of hallucination as `add_job`'s
   old bare "new job" trigger. Replaced with specific "to <unit>"/
   "how many <unit>" compounds.
3. `delete_expedition`/`delete_trip` with the name inserted before the
   noun ("Delete my Field Season expedition") gate nothing — same
   accepted name-before-noun trade-off this registry already has for
   delete_project/delete_task, not a new bug; documented in the trigger
   phrase comments and the golden-set cases use the supported "delete
   the X called Y" phrasing instead.

22 new unit tests (`tests/test_assistant_action_handlers.py`) plus 13
new golden-set cases (100 → 113). Full official golden set verified
113/113 clean after the fixes above. Registry now 74 actions across 19
domains. 1399 pytest tests passing (22 new).

## Floating orb + collapsible sidebar, header redesign, sidebar voice/history (2026-07-18)

Large UX pass, several pieces:

- **Floating orb + collapsible Assistant sidebar** (new
  `gui/widgets/floating_orb_widget.py`). Real ask: "so we don't have to
  have a 24/7 open assistant screen." `gui/main_window.py`'s
  `CharacterPanel` is now hidden by default; a small glowing blue orb
  appears and "reaches" toward the mouse (clamped to a max-travel
  radius from its home corner, via a plain 50ms-polled `QCursor.pos()`
  timer — no event-filter fighting this app's deep widget tree, no
  animation easing on top yet, deliberately, since screenshot-only
  review can't judge motion "feel") whenever the cursor nears the
  bottom-right corner; clicking it toggles the sidebar. **Found and
  fixed a real bug via a headless smoke test**: the orb's "stay visible
  while hovering the orb itself" check used its raw `geometry()`,
  which defaults to `(0, 0)` before the orb has ever been shown/moved —
  a mouse position near the window's top-left corner (nowhere near the
  real trigger zone) falsely counted as "hovering the orb." Fixed by
  only trusting that check while the orb is actually visible.
- **Header redesign**: the old bare "Search" button is now a real
  `QLineEdit` styled as a search bar (still click-to-open
  `gui/search_dialog.py`, which already owns the actual live-filtering
  logic — this only changes what it looks like). The notification bell
  is gone, replaced by a circular avatar showing the active profile's
  first initial; clicking it opens a menu with Notifications
  (preserves that access point, count included in the label),
  a quick volume slider (new `gui/widgets/volume_quick_control.py`),
  and Settings.
- **Volume moved out of the Home dashboard grid entirely** — real bug
  report ("spacing and wording of the widgets is off again"), and the
  user's own hunch was right: the old Volume card was the only
  3-element card (header + slider + body) among otherwise-uniform
  2-element cards, and it landed in the grid's first row right next to
  Power/Mission, forcing that row taller than the others. Removed from
  `core/application.py`'s `_register_dashboard_widgets()` and
  `gui/home_dashboard.py` entirely (dead code removed, not just
  disabled) now that it lives in the header's profile menu instead.
- **Sidebar gets full voice parity with the full-screen Assistant
  module**: push-to-talk (on-screen click only — deliberately does NOT
  construct its own `PushToTalkTrigger`, since a second instance would
  bind a second `gpiozero.Button` to the same physical GPIO pin the
  full module's own trigger already claims) and a Stop button.
- **Sidebar starts fresh every launch**: previously loaded and rendered
  whatever conversation was last active, so a long chat history greeted
  the user again on every single boot. Now calls
  `start_new_active_conversation()` on construction instead (same as
  the full module's "+ New Conversation" button); a new "History"
  button opens `gui/conversation_history_dialog.py` (reuses
  `ConversationCard` as-is) to reach an older conversation.

**Caught a real data-pollution incident while smoke-testing the
sidebar changes**: an ad hoc verification script didn't isolate
`ConversationManager`'s data directory (the same mistake class this
project has hit before — see gotcha #11), and briefly wrote several
test conversations into the real `data/conversations.json`. Caught by
inspecting the file's actual content before trusting the test result,
not just the test's own pass/fail — 7 test-generated entries identified
by timestamp/content and removed, the one real conversation preserved.
Updated `docs/user_help/getting_started.md` and `home_and_power.md`,
which both referenced the old header layout/Home volume card.

1399 pytest tests passing (no new committed ones — this is almost
entirely Qt widget/layout/interaction behavior, verified via three ad
hoc headless smoke tests instead: dashboard-grid removal, sidebar
blank-start + history switch, and the orb's show/hide/position/click
behavior). **The orb's motion "feel" specifically still needs real,
live user judgment** — it's the kind of thing this project's own
history has repeatedly found can't be assessed from a screenshot alone.

## "MIA" rename, everywhere + correct pronunciation (2026-07-18)

Real ask, decided via AskUserQuestion: change every display of
"M.I.A." to "MIA" throughout the app, and make it *sound* like the name
"Mia" when spoken rather than being spelled out letter-by-letter.
Literal find-and-replace across 64 files (UI text, docstrings/comments,
`docs/*.md`, `docs/user_help/*.md`, `README.md`, `CLAUDE.md`) —
deliberately **excluded** the `"app": "M.I.A."` manifest-format
constant in `core/backup_manager.py`/`core/update_manager.py`/
`core/expedition_sync.py` and their test fixtures, since that's a
real on-disk data-format identifier checked against existing backup/
update/expedition-export files, not display text; changing it would
have silently broken loading anything already exported before this
rename. Prose/comments/user-facing error strings *inside* those same
three files did still get renamed (e.g. "Not a MIA backup file...").

New `core/voice_manager.py`'s `prepare_text_for_speech()` (pure,
tested) substitutes whole-word "MIA" → "Mia" only in the text actually
sent to Piper synthesis, never in what's displayed — one choke point
(`VoiceManager.synthesize()`) covers every spoken surface (chat replies,
tool confirmations, the startup briefing) regardless of which code
composed the text. Word-boundary-safe, confirmed it doesn't touch
"MIAMI"/similar.

Re-verified the live golden set (113/113 clean) after changing
`core/assistant_chat.py`'s `_IDENTITY_LINE` — used on both the
action-request and info-question paths, the most fragile prompt
surface in this codebase, so any wording change there gets the same
re-verification discipline as every prior identity/prompt change.

**Design note for later**: the incoming Dashboard/Missions design
handoff's own nav uses "M.I.A." as a stylized wordmark/logotype but
"MIA" in body copy ("Say 'Hey MIA' to start a voice session") — worth
keeping in mind if a future visual pass wants a distinct logotype
treatment for the wordmark specifically, separate from this plain-text
rename.

1403 pytest tests passing (4 new — `prepare_text_for_speech()`'s unit
tests).

## Mission Log redesign — second phase of the Dashboard+Missions design handoff (2026-07-18)

Rebuilt `modules/missions/module.py` entirely against `CCH.zip`'s
`Missions.dc.html` reference: a two-panel "Mission Log" (detail panel —
icon/title/region, summary, an objectives checklist, difficulty tag,
a rewards footer — on the left; a mission list — ACTIVE/COMPLETED
grouped, a sticky Level+XP footer — on the right), replacing the old
single-column "Missions list above Objectives list" layout entirely,
not just restyling it. New `gui/widgets/mission_list_row.py` (compact
icon+title row, no inline edit/delete — editing/deleting now happens
from the selected mission's detail panel) and
`gui/widgets/objective_checklist_row.py` (a real checkbox glyph instead
of ObjectiveCard's separate "+1" button); the old `MissionCard`/
`ObjectiveCard` widgets are retired (deleted, not left dead) now that
nothing uses them. `AddEditMissionDialog` gained fields for all the new
Mission data (icon/region/summary/difficulty/mission type/reward XP/
reward credits). The sticky footer reads the *real* active profile's
level/XP (`core.leveling.compute_level_progress()`), not placeholder
numbers — this is live gamification state now.

**Found and fixed a real Qt ghosting bug via an actual screenshot, not
assumed**: the detail panel's header row and difficulty-tag row were
added via `addLayout()` directly rather than wrapped in a `QWidget`,
so `_refresh_detail()`'s `takeAt()`+`hide()`+`setParent(None)`+
`deleteLater()` cleanup loop (this app's established safe-rebuild
pattern) couldn't reach their child widgets — a bare nested layout has
no widget of its own for `takeAt()` to hide/reparent/delete. Selecting
a second mission then a third left the first mission's title/region/
tag labels visibly overlapping the newest one's, confirmed by an actual
rendered screenshot. Fixed by wrapping both in real `QWidget` containers
before adding them, same "always wrap dynamic sub-sections in a real
widget, never a bare sub-layout" lesson this project has hit before
(`gui/character_panel.py`'s `_refresh_suggestions()`).

**Also caught real regressions before they shipped**, all for the same
reason: the design mockup's own placeholder data never exercised these
pre-existing features, so a literal rebuild against just the mockup
would have silently dropped them.
1. The "MIA ASSIGNED" badge (2026-07-16 gamification pass's quest-giver
   indicator) — added back onto the detail panel's header, verified via
   a second screenshot with an auto-assigned mission selected.
2. `MissionCard`'s aggregate objective-progress bar and `ObjectiveCard`'s
   per-objective fractional progress — a checklist row's checkbox alone
   only shows done/not-done, losing "1 of 2 objectives complete" and
   "2 of 3 fish caught" entirely. Added back as plain text: new
   `format_objectives_heading()` ("OBJECTIVES — 1 of 2 complete") and
   `format_checklist_label()` (appends "(1 of 3)" to any incomplete
   objective whose target is more than one step). Verified via a third
   screenshot with partial progress on two different objectives.

`tests/run_module.py` needed `context.missions`/`context.profiles`
wired in for real (profiles was previously deliberately omitted for its
legacy-migration side effect — now genuinely needed since the Level/XP
footer reads it) — its own file comment already documents this
maintenance convention.

10 new pure-function tests (`format_rewards_line`/
`format_level_footer_line`/`format_objectives_heading`/
`format_checklist_label`), verified end-to-end via a headless smoke
test (auto-select first active mission, click-to-select in the list,
click-checkbox-to-increment-tally, real level/XP footer) with three
screenshots. 1430 pytest tests passing (10 new — Qt widget behavior
itself verified via the ad hoc smoke test, not a permanent one, same
treatment as this project's other pure-UI changes).

## Dashboard console redesign + new top nav — final phase of the CCH.zip handoff (2026-07-18)

Closes out the design handoff: `gui/home_dashboard.py` is a full
rewrite (not a restyle) replacing the old customizable-widget-grid Home
screen entirely, and `gui/main_window.py`'s header gained a tab row.

**The console**: a left telemetry panel (Processing Load gauge, Power/
Uptime stats, a tip card), a center console (state label, the big
animated `PresenceWidget` orb — gained a new "speaking" state — the
latest reply as a message bubble), a narrow CPU/NET/SYS gauge rail, a
collapsible right rail (Assistant Profile, Monitoring, Activity Log,
Quick Toggles), and a bottom chat bar. New `gui/widgets/circular_gauge.py`
(plain `QPainter`, matching this app's established technique for
anything circular/animated — no SVG dependency) and
`core/dashboard_telemetry.py` (pure network-rate/uptime-formatting
math, since `core.system_health`'s network counters are cumulative
since-boot totals, not a rate).

**This is the third chat surface** (alongside the full Assistant module
and the sidebar) — reuses the exact same `core.assistant_chat`/
`ChatWorker`/`TTSWorker` logic, so all three can never drift apart. The
startup briefing is now the console's first message bubble instead of
a separate spoken-once banner — same underlying
`build_startup_briefing()` call as before.

**The Assistant Profile card is honest, not a literal mockup port**:
the design's "Mode" selector and "Wake word" row don't correspond to
any real MIA feature (no adaptive-mode concept, no wake-word
detection) — rather than build non-functional UI for either, those
rows show real facts instead (configured TTS voice, the always-on
personality trait, "Push-to-talk" as the honest name for the real
voice-input mechanism). Matches this project's own established stance
against fabricating UI for features that don't exist.

**New top nav**: "MIA" wordmark + tabs (Home/Missions/Monitoring/App
Center, mapped onto the existing Diagnostics module and Apps grid) —
Back, the search bar, and the profile avatar menu (all shipped last
round) stay, since they're real, tested, valuable features the
design's own shallower nav didn't need to account for. The active tab
is derived from `self._stack.currentWidget()` on every navigation call
(`_sync_nav_tabs()`), not tracked separately, so it can't drift out of
sync with `go_back()` landing somewhere unexpected. Per the user's own
call: the small corner-follow orb (from the earlier collapsible-sidebar
pass) now hides itself while Home is the current screen, since the
console's own big orb already serves that role there — everywhere
else, it works exactly as before.

**Found and fixed two real bugs via headless-Qt screenshots**:
1. Reconstructing `gui/home_dashboard.py`'s pure formatting functions
   from memory instead of copying them verbatim from the file being
   replaced broke 21 existing tests (wrong clock format, wrong
   real-estate/kraken/net-worth field names, wrong power-line wording)
   — caught immediately by the test suite, fixed by pulling the exact
   original implementations from git history instead of re-deriving
   them.
2. The Power/Uptime stat tiles reused a 19px bold font sized for a
   different, wider card elsewhere — "59h 18m" clipped to "59h 18n" in
   the tile's ~100px half-column width, and forced the whole fixed-
   width side panel wider than intended, showing an unwanted horizontal
   scrollbar. Fixed with a dedicated smaller font
   (`DashboardStatValue`) plus word-wrap, and a defensive
   `ScrollBarAlwaysOff` policy on both side panels regardless.

**Caught a real data-pollution incident while smoke-testing nav
clicks**: forgot to isolate `ActivityLogManager`'s data directory in an
ad hoc script — clicking the Missions/Monitoring tabs wrote 3 real
`module.opened` entries into the actual `data/activity_log.json`.
Caught by inspecting the file's actual content (not just trusting the
test's pass/fail), identified by timestamp, removed.

Also deleted `gui/dashboard_customize_dialog.py` (zero callers left
once the old widget-grid Home screen was replaced) and updated
`docs/user_help/getting_started.md`/`home_and_power.md` for the new
layout. `core/dashboard_widgets.py`'s registry service itself is left
in place, unused — same "leave it, don't tear out the config-state
migration too" reasoning as the Mission Log phase's own notes.

1439 pytest tests passing (no new committed ones — this phase is
almost entirely Qt widget/layout/interaction behavior, verified via
headless smoke-test screenshots covering the console, both rail-toggle
states, and full nav-tab click-through instead). This closes out the
entire `CCH.zip` Dashboard+Missions design handoff.

## Two real follow-up reports on the CCH.zip redesign (2026-07-18)

1. **"The orb's grey rectangle takes up so much space it makes
   everything around it small and squished."** Real bug in
   `gui/home_dashboard.py`'s `_build_console_panel()`: the orb stage
   frame was added with `stretch=1`, so it filled *all* leftover
   vertical space in the console column — a large, mostly-empty grey
   box around the 150px orb that made the fixed-width side panels read
   as cramped by visual contrast, even though their own pixel
   dimensions never changed. Fixed with a fixed height (260px) sized
   for the orb + toggle button + padding, moving the stretch to below
   the last-message bubble instead so leftover space is plain
   background, not an inflated box.
2. **"[Missions] needs some way of adding to the progression/tracking
   and it also needs to allow you to select the mission to view it."**
   Verified with real simulated mouse clicks (`QTest.mouseClick`, not
   just `.click()`) that selecting a mission and incrementing a tally
   objective both worked mechanically — the real gap was
   *discoverability*, not a broken mechanism: (a) a single-step
   objective's checkbox reads as an ordinary checkbox, but a
   multi-step one ("Catch 3 fish") gave no visible hint that clicking
   the same plain checkbox repeatedly was how you logged partial
   progress; (b) mission list rows had no visual signal that they were
   clickable at all. Fixed: multi-step objectives now get an explicit,
   clearly-labeled "+1" button (`gui/widgets/objective_checklist_row.py`)
   separate from the checkbox, which becomes a pure completion
   indicator for those; mission list rows gained a pointing-hand
   cursor and a trailing "›" chevron (`gui/widgets/mission_list_row.py`)
   — the same "tap to go deeper" convention the design's own Assistant
   Profile rows already use.

1439 pytest tests passing, verified via headless-Qt screenshots of
both fixes.

## Orb stage tuning, round 2 (2026-07-18)

Follow-up on the previous orb-sizing fix: "smaller from top to bottom
but still stretches a bit far across... can be a bit taller but less
wide," plus "remove the word MIA over the orb... make the orb a bit
bigger and pulse a bit more." Console orb stage: 260px → 300px tall,
now capped at 460px max width and centered (was filling the full
console column width). The orb itself: 150px → 190px, and no longer
shows the "Mia" text glyph once past the startup moment — the
console's title/last-message already say who this is, the glyph on the
orb itself was redundant.

`gui/presence_widget.py` gained an optional `pulse_amplitude`
constructor param (default 0.2, the original hardcoded value —
`gui/character_panel.py`'s sidebar and `gui/splash_screen.py`'s boot
moment are both untouched, still their original feel) so the
Dashboard's instance specifically could pulse more noticeably
(`pulse_amplitude=0.4`) without changing the two other callers that
weren't part of this report.

1439 pytest tests passing, verified via a headless-Qt screenshot.

## Console tile restructure + toggleable login screen (2026-07-18)

Three more follow-ups:

1. **"The tile with the assistant should be top to bottom and the text
   underneath, and the same less wide width across so the side menus
   don't look weird."** The orb stage is now a genuinely narrow,
   naturally-tall tile (`setFixedWidth(240)`, no hardcoded height —
   sized to fit whatever's inside, so a long reply can never clip) —
   240px sits between the telemetry panel's 220 and the right rail's
   230, so the console no longer reads as an inconsistently-wide
   centered box next to the side panels. The last-message text moved
   *inside* the tile, underneath the orb, instead of sitting outside
   it as a separate widget.
2. **"Put MIA back somewhere under or above the orb, big bold and
   outlined, the same blue used throughout."** A new `ConsoleOrbLabel`
   — big bold teal text in a bordered box (Qt's QSS has no real text-
   stroke property, so "outlined" here is the same bordered-badge
   language `MissionDifficultyTag`/`MissionActiveCountPill` already
   use) — sits above the orb inside the tile. Distinct from the
   glyph-inside-the-orb text an earlier pass removed as redundant
   clutter; this is a deliberate, more prominent re-addition. Orb
   itself sized down slightly (190 → 160px) to fit the narrower tile
   with real margin.
3. **"If there's only one user profile and no password it should skip
   the login screen, and that should be a setting toggleable in the
   [profile avatar] settings menu."** This behavior already existed
   unconditionally (`gui/lock_screen.py`'s own docstring: "shown at
   boot only... exactly one profile AND it has a password set") — this
   formalizes it into an explicit, opt-out-able setting
   (`profile.always_show_login_screen`, default False, toggled from
   the profile-avatar menu) rather than just an unconditional code
   path with no way back to a confirmation screen. `LockScreen` now
   handles a password-less profile gracefully when the setting is on:
   no password field (there's nothing to verify), a plain "Welcome
   back, continue?" prompt with a `Continue` button instead.

1439 pytest tests passing, verified via a headless-Qt screenshot (tile)
and real-click smoke tests (`LockScreen`'s two modes, the menu toggle's
config round-trip through a fresh reload from disk).

## Dashboard column proportions fixed against the real design reference (2026-07-18)

The user shared the actual design handoff screenshot (`MIAHome.png`) —
confirmed the root cause of "the side menus are still too small, bring
them closer towards the center": the design's own CSS grid uses
proportional flex ratios for *all four* columns
(`minmax(150px,2.3fr) minmax(260px,3.6fr) minmax(110px,1.6fr)
minmax(170px,2.5fr)`), not fixed-pixel side panels sitting next to a
`stretch=1` center that soaks up 100% of whatever's left over. That
mismatch is exactly what made the sides look small on a wide window —
they stayed a fixed size while the center kept growing to fill it.
`gui/home_dashboard.py`'s `body` layout now uses that same 2.3:3.6:
1.6:2.5 ratio (×10 for clean integer stretch factors) across the
telemetry panel/console/gauge rail/right rail, each keeping a minimum
width (`setMinimumWidth()`, not `setFixedWidth()`) matching the
design's own "minmax" — never below a usable size, but free to grow
proportionally with the window instead of staying pinned at a fixed
pixel count.

Also moved the "MIA" label (added last pass) to below the orb instead
of above it, per a direct follow-up correction.

1439 pytest tests passing, verified via a headless-Qt screenshot at
the reference image's own approximate window size (1490×1030) —
resulting column widths now closely match the reference's proportions.

## Console tile reversed back to wide/tall, nav grouping, bigger sidebar widgets (2026-07-18)

Real follow-up report, re-checked directly against `MIAHome.png` rather
than reasoned about from memory: **"the assistant panel in the middle
is too short and not wide enough with too much space around it, it
should be the full length of the window just like the 2 side bars but
should stop a little sooner before reaching the bottom of the window to
display the welcome message underneath."**

This directly reversed the previous pass's `stage.setFixedWidth(240)`
decision. That 240px-narrow read was made *before* the side panels'
own proportional-width bug was fixed — once the side panels actually
grew to their correct width (previous section), a narrow 240px console
tile no longer made sense next to them; the reference clearly shows a
wide box filling nearly the whole console column. `gui/home_dashboard.py`'s
`_build_console_panel()`: the width cap is gone, `stage` gets
`stretch=1` in the outer column layout (tall, like the side bars, but
stopping short of the very bottom because `_last_message_label` is now
a sibling *below* it, not nested inside — this also reverses "text
underneath" being satisfied by nesting it inside the tile). Presence
orb bumped back up 160 → 190px now that there's room again.

**"All the widget looking pieces on the sidebars need to be a bit
bigger"** — the Processing Load gauge (150 → 170px), the CPU/NET/SYS
rail gauges (84 → 104px), and the right rail's Monitoring tiles
(`MonitorTileValue` 15 → 19px, `MonitorTile` given explicit padding and
a 64px minimum height) all sized up. `DashboardStatValue` (POWER/UPTIME)
also bumped 15 → 19px — safe now that the telemetry panel has real
proportional width instead of the old fixed 220px column that caused
the original clipping bug this font size was shrunk to avoid.

**"The menu doesn't have the distinct lines and separation and color
differences the reference picture has"** — `gui/main_window.py`'s
header previously put the wordmark, tabs, and back/search/avatar
cluster directly on the header's own flat background with only spacing
between them. Added a new `_build_nav_separator()` (a thin `QFrame`
VLine) between the wordmark and the tab row, and again before the Back
button; the four nav tabs are now wrapped in their own `NavTabGroup`
frame with a distinct background (`#111722`, matching the same tone
`HeaderButton`/`HeaderSearchBar`/`ProfileAvatarButton` already use) and
a bordered, rounded-pill container, instead of floating loose on the
header bar.

Verified this whole pass with a real headless-Qt boot: rather than a
throwaway widget-only smoke script, this one runs the *actual*
`core.application.MIAApplication` boot sequence (splash → module
discovery → straight to the main window, since the real dev profile is
already single/password-less) against a temporary copy of the whole
repo tree (`core/`, `gui/`, `modules/`, `config/`, and `data/` minus the
72MB `map_tiles/` cache) — real managers, real config, zero
monkeypatching, and zero risk to the actual `data/`/`config/` files
since it only ever touches the copy. 1439 pytest tests still pass.

## Headless MIA Core entry point — first slice (2026-07-19)

Picks up the thread `docs/VISION.md`'s 2026-07-15 "Core drops its GUI
entirely" sharpening flagged as "not built yet, and genuinely
substantial when it is": a new `core_main.py` (parallel to `main.py`,
never imports PySide6/`gui.*` directly or transitively — confirmed by
checking `sys.modules` after import) drives `core/voice_loop.py`'s
push-to-talk -> transcribe -> Assistant -> speak cycle as one blocking,
single-threaded loop — no Qt event loop, no QThread workers, matching
the Receiver's actual shape (a screen-free device with one user talking
to it one turn at a time).

**`core/core_runtime.py`** builds a right-sized `AppContext` (profiles,
notifications, calendar, alarms, journal, inventory, llm, voice,
waypoints, power, expeditions, trips, memories, missions, user_memories,
activity_log, reference_library, device_help, plus an un-discovered
`ModuleManager` so `context.module_manager`-dependent code degrades
gracefully instead of crashing) and a **deliberately curated Assistant
action registry** — alarms, notes, inventory, calendar, waypoints,
missions, recall_recent_activity/system_health/power_status — rather
than the full ~65-action registry `core/application.py`'s
`_register_assistant_actions()` builds for Home. Every one of those
`_action_*` handlers turned out to already be a `@staticmethod` — a
pure function of `(context, arguments)` with zero dependency on
`MIAApplication` itself except `open_module` (now also converted to a
`@staticmethod` reading a new `context.module_manager` field, set by
both entry points) — which is what made it safe to give Core its own
independent copy of the ~20 handlers it curates without touching or
duplicating Home's much larger registry. Left out deliberately, not by
oversight: anything GUI-navigation-only (`open_module`, `set_theme`),
Workshop/Field Kit/Maps/Project Manager/Expedition-detail actions (real
Home-desktop-scoped surfaces, revisitable once this first slice proves
itself on real hardware), and `get_sun_moon_info` specifically (its
handler imports `modules.navigation.module`, which would have dragged a
`modules/`/PySide6 import into this supposedly gui-free process).

**Physical Receiver hardware (push-to-talk button/e-paper display/
recording LED/vibration motor) is stubbed, not built** — `docs/HARDWARE.md`
still lists the exact parts and whether the Receiver gets its own MCU
as open questions, so writing real driver code now would be building
blind, same discipline as 11.3b/11.6. `core/receiver_indicators.py`
defines a `ReceiverIndicators` Protocol (on_idle/on_listening/
on_thinking/on_speaking/on_notify) with a real, fully-functional
`ConsoleReceiverIndicators` default (logs instead of driving GPIO/SPI) —
swap in a real backend once the Receiver's parts are chosen, nothing
else needs to change. `core/push_to_talk_source.py` mirrors this split
for the button itself: `GpioPushToTalkSource` (real `gpiozero.Button`)
falls back to `KeyboardPushToTalkSource` (Enter to start, Enter to stop
— a terminal has no clean "held down" signal the way a real button
does, so this is an honest two-press interaction, not a simulated one).

**Verified for real, not mocked, including a real discovery along the
way**: this dev sandbox turned out to have real `sounddevice`/
`libportaudio2` now (previously documented as blocked) — but `aplay -l`
confirms there's still no real sound card, just a software PulseAudio
device, so live mic capture itself remains unverifiable here. Instead,
verified the same way this project always has for voice work: a real
Piper-synthesized `.wav` fed straight into real Vosk transcription
(bypassing only the mic-capture step), then the full pipeline exercised
against the real running Ollama server end-to-end — "Set an alarm
called Wake Up for 07:00" correctly called the real `add_alarm` handler
and created a real `Alarm`; a two-turn "My name is Alex and I love
hiking in the Cascades" / "What's my name, and where do I like to
hike?" exchange correctly used in-memory conversation history *and*
correctly extracted two real facts via `core/user_memory_manager.py`.
Confirmed `PySide6` never appears in `sys.modules` throughout. All 1439
pytest tests still pass; `open_module` re-verified working for Home
too, both for a real module and a missing one.

**Not built yet, flagged for a future slice, not an oversight**: the
Core→Home hand-off mechanism (still unbuilt per `docs/VISION.md`),
expanding Core's curated action registry toward parity with Home's once
this shape is validated on real Pi hardware, and the real Receiver
hardware backends once `docs/HARDWARE.md`'s open parts questions are
resolved.

## Voice-command readiness for offline wearable use — real STT-noise finding + fix (2026-07-19)

Direct follow-up ask: "deep focus on preparing the assistant for use
offline with the wearable by voice commands." The previous session's
verification of the headless Core entry point only ever fed clean,
hand-typed text into `build_chat_request()`/`chat_with_tools()` — real
enough for proving the pipeline and registry work, but it never
actually exercised real speech recognition noise, which is the one
part of "voice commands on a wearable" that's genuinely different from
typing.

New `tests/core_live_voice_check.py` (sibling of `tests/live_model_check.py`,
scoped to Core's curated registry via `core/core_runtime.py::build_core_context()`
directly rather than a second hand-duplicated context builder) has two
tiers: a 33-case clean-text golden set covering every action Core
registers (all passing, including confirming `open_module`/`set_theme`/
`get_sun_moon_info` correctly never fire — they're not registered), and
a second tier that's new for this project: real Piper-synthesized
`.wav` audio fed through real Vosk transcription, then *that* (possibly
garbled) transcript run through the same pipeline `core/voice_loop.py`
uses — not typed text standing in for speech.

**Found a real, 100%-reproducible bug this way**: Vosk's small STT
model transcribes the word "waypoint(s)" as the two separate words "way
point(s)" — confirmed 6/6 across several phrasings and sentence
positions (`"List my waypoints"` -> `"this to my way points"`, `"What
waypoints do I have"` -> `"what way points do i have"`, etc.). Since
`list_waypoints`' gating relied on the bare substring "waypoint" to
open the whole waypoints domain, this meant the domain would
essentially never gate open from real spoken input, regardless of
phrasing — a much more fundamental gap than a missing trigger phrase
variant. Fixed by adding `"way point"`/`"way points"` to
`list_waypoints`'s `trigger_phrases` in **both**
`core/application.py` (Home) and `core/core_runtime.py` (Core) — this
affects Home's existing push-to-talk voice input identically, since
both go through the same `VoiceManager`/Vosk backend. Domain-scoped
attachment (`AssistantActionRegistry.matching_actions()`) means this
one addition reopens `add_waypoint`/`waypoint_distance` too, not just
`list_waypoints` itself — no need to duplicate the fix into their own
trigger lists. Re-verified: the previously-failing case now passes,
8/8 on the voice tier, 33/33 on the golden set, 1439 pytest tests still
green.

**A second, related pattern observed but deliberately not "fixed" the
same way**: imperative-leading phrasings ("List my alarms", "Show my
waypoints") had their leading verb itself swallowed by Vosk
(`"list"` -> `"this"`/`"this to"`, `"show"` -> `"though"`), reproducibly,
across multiple domains — not a one-off. Query-form phrasings ("What's
my X", "What do I have") survived intact in every test. Unlike the
waypoint fix, this isn't safely patchable via more trigger phrases:
the literal words "list"/"show" are simply absent from the transcript,
and words generic enough to catch "this"/"though" as stand-ins would
collide constantly with unrelated speech. Flagged, not fixed — the real
fix path is evaluating a larger Vosk model (this project has only ever
benchmarked LLM model size for the Assistant's language model, never
STT model size) or a custom vocabulary/grammar bias for command words,
both real investigations of their own, not something to guess at
blind. In the meantime, worth knowing this project's own voice command
guidance (`docs/user_help/`) should favor query-form phrasing over
imperative-form where both exist.

## Nav bar blending, M.I.A. wordmark restored, bigger sidebar widgets, chat bar voice buttons (2026-07-19)

Real follow-up report on the Home dashboard, checked against `MIAHome.png`:

1. **"The Nav bar needs to blend with the bar behind it... one
   continuous color with just the words over top."** `QFrame#NavTabGroup`
   (the distinct background+border box added around Home/Missions/
   Monitoring/App Center in the previous nav-grouping pass) is now
   transparent/borderless — the reference has no box at all, just text
   on the header's own continuous background. The frame itself stays
   (still does layout/margin work), just its QSS fill is gone.
2. **"Change MIA back to M.I.A." — specifically the top-left wordmark
   and the console title, not the rest of the app** (which stays "MIA,"
   pronounced like the name, per the earlier explicit rename). `gui/main_window.py`'s
   `NavWordmark` and `gui/home_dashboard.py`'s console title are the only
   two spots touched.
3. **"Widgets on the sidebars stop halfway down the screen — should be
   big enough to fill."** Compared a real headless-Qt screenshot against
   `MIAHome.png` at its exact 1491×1027 size (not eyeballed at a
   different window size) before touching anything. Every right-rail
   card (Assistant Profile/Monitoring/Activity Log/Quick Toggles) and
   the left telemetry panel's cards got real `setContentsMargins()`/
   `setSpacing()` values instead of Qt's small defaults; the gauge
   rail's own spacing roughly doubled and its CPU/NET/SYS gauges grew
   104px → 116px. Closes most (not literally all) of the gap — the
   reference itself has some empty space in the left/middle columns
   too, confirmed by measuring both at identical dimensions rather than
   assuming "fill 100%" was actually the reference's own intent.
4. **"2 buttons before Send: start recording voice, and stop MIA
   talking."** Brought the full Assistant module's existing Hold to
   Talk / Stop Speaking pair (`modules/assistant/module.py`) to this
   bar too — same `core/push_to_talk_trigger.py` wiring, same
   `TalkButton`/`StopSpeakingButton` QSS (already themed, no new
   styling needed), same handler shape (`_on_talk_pressed`/
   `_on_talk_released`/`_on_stop_speaking`). This dashboard's own
   existing `_set_state()`/console state label doubles as the status
   feedback modules/assistant/module.py gets from a separate status
   label, so no new UI element was needed for that part.

**Verified for real, not just screenshotted**: a real press-and-hold
(with an actual elapsed delay, not a same-tick press+release) correctly
starts/stops recording and degrades to "Speech-to-text unavailable"
gracefully in this mic-less dev sandbox; a real `_speak()` call
correctly enables/disables the Stop button across a full TTS
synthesis+playback cycle. **One real finding along the way**: an
earlier same-tick synthetic press+release (zero elapsed time between
them, not achievable by an actual human clicking a button) left a
`TTSWorker` thread and the whole process stuck for several minutes —
not reproducible with any realistic press-hold duration, so treated as
a synthetic-test artifact rather than a real bug, but worth knowing if
a future automated test ever tries to simulate press/release without a
real delay between them. 1439 pytest tests still pass.

## Partial revert: sidebar Assistant chat + original widget cards restored, new header kept (2026-07-19)

Real user report: "I liked how the dashboard looked before the second
Claude design handoff with the AI assistant in the sidebar and the
original button widgets. The new dashboard isn't looking right."
Investigated via git history rather than guessing which past state was
meant — `git log` showed two distinct design-reference-driven passes:
"ForMIA" (`12cac62`/`dff015f`, 2026-07-15, gave the sidebar chat + the
original Power/Mission/Current Project/Activity Log/Quick Bus/Real
Estate/Kraken Agent/Net Worth widget cards) and the CCH.zip/MIAHome.png
handoff starting at `5c092d6` (2026-07-18, floating-orb collapsible
sidebar + the console/gauges dashboard rebuild + new nav tabs).
Rendered the exact pre-second-handoff commit (`d98f0e0`) in an isolated
git worktree to confirm this by screenshot before touching anything,
then let the user choose the scope via `AskUserQuestion` rather than
assuming "revert everything since 5c092d6" was correct: **a blend, not
a full rollback** — bring back the sidebar chat and the original widget
cards, but keep the current header (M.I.A. wordmark, nav tabs, search,
avatar).

`gui/home_dashboard.py` is now the pre-second-handoff widget-grid
implementation (`core/dashboard_widgets.py`'s registry was untouched
the whole time, confirmed via `git diff --stat` showing zero changes
to it across the entire span — only how `home_dashboard.py` rendered
it had changed), with the chat-bar/voice-button work from the last two
sessions grafted back in on top (same `core.assistant_chat`/
`core.chat_worker`/`core.push_to_talk_trigger` wiring, unchanged).
Restored `gui/dashboard_customize_dialog.py`, deleted in the console
rebuild (`1f553f9`) and never recreated — a real dependency the old
dashboard needs. `gui/main_window.py`: removed the
`self._character_panel.hide()` from the 2026-07-18 "no more 24/7 open
assistant screen" pass (a real explicit ask at the time, now reversed
by a real explicit ask the other way — both preserved here for
context, not a mistake either time) — the floating orb still toggles
it closed for anyone who wants to collapse it, it just no longer
starts collapsed. Also fixed a real staleness bug this surfaced:
`_update_corner_orb()`'s docstring/logic hid the small corner orb
specifically on the Home screen to avoid duplicating the console's own
big presence orb — since Home no longer has that console at all, this
special-case was actively wrong now, not just unnecessary, and was
removed.

**A real regression found via screenshot, not assumed away**: with the
sidebar back to permanently visible, it eats width from the main
content column — the dashboard chat bar's own suggestion-chip row
(redundant with the sidebar's identical chips) pushed the whole screen
past its available width into an unwanted horizontal scrollbar.
Removed that redundant chip row (and the now-dead
`_on_suggestion_clicked()`/`suggested_prompts_for_module` import) —
confirmed clean with a re-rendered screenshot at the same 1491×1027
reference size.

**Verified for real**: all 1439 pytest tests pass against the merged
file; a real headless-Qt boot screenshot at 1491×1027 confirms the
restored layout; a real interactive test confirmed the character panel
starts visible and a full send-through-the-dashboard's-own-chat-bar
round trip against the live Ollama server completes with no crash.

## Plaid Investments product: Fidelity/brokerage holdings + a real net-worth fix (2026-09-09)

Closes the outstanding "Confirm what Fidelity actually exposes" item
tracked above and in `docs/VISION.md`'s Immediate follow-up list.
`core/plaid_manager.py`'s `create_hosted_link_session()` now requests
the Investments product alongside `balance`/`transactions` for every
new connection, plus an update-mode twin
(`create_investments_upgrade_session()`/`finish_investments_upgrade()`,
same shape as the existing Transactions upgrade path) for accounts
connected before this existed. `sync()` fetches each investments-
enabled item's real holdings via `investments_holdings_get`
(`_holdings_snapshot_for_item()`), writing a `plaid_investments_<item_id>`
snapshot into the same watched-folder mechanism balances already use —
no new ingestion code. Confirmed real, easy-to-get-wrong SDK naming:
`InvestmentHoldingsGetRequestOptions` lives under the **singular**
`plaid.model.investment_holdings_get_request_options`, while
`InvestmentsHoldingsGetRequest` itself is **plural** — verified by
direct construction against the installed SDK, not assumed.

**Real, honest limitation, documented in `core/plaid_manager.py`'s own
docstring and the Bank Sync tab's intro text**: Fidelity IS supported
via Plaid, but on Plaid's free/Pay-as-you-go tier, actually seeing
Fidelity holdings requires the user to file a support ticket with
Plaid requesting Investments access first — Plaid's API itself doesn't
error on a non-qualifying item, it returns
`is_investments_fallback_item=True` with no holdings, which
`_holdings_snapshot_for_item()` treats as "nothing to show yet," not a
bug.

**A real, separate, pre-existing gap found while building this, fixed
as part of it**: `sync()`'s balance snapshots never carried a
`summary.total_value` field, meaning Plaid-synced balances contributed
nothing to `gui/home_dashboard.py`'s Net Worth widget — regardless of
Investments. Fixed via a new pure `compute_net_balance_total()`
(assets minus credit/loan liabilities, using each account's
`balances.current`), now written into every balance snapshot.
Deliberately does NOT double-count with the holdings snapshot: a
brokerage account's own `balances.current` already includes its
holdings' value, so the holdings snapshot uses a differently-named
`holdings_total_value` key instead of its own `summary`, read only by
`modules/budget/module.py`'s new Holdings list on the Bank Sync tab
(`format_holding_row()`, an "Add Investments Access…" button, no chart
— a plain list, matching this session's own restraint on not building
visualization nobody asked for).

**Verified for real**: all 1773 pytest tests pass, including a real
(non-mocked) SDK construction test for
`InvestmentsHoldingsGetRequest`/`InvestmentHoldingsGetRequestOptions` —
same discipline that caught two real bugs earlier this session
(`CountryCode` objects vs. plain strings; `TransactionsSyncRequest
.cursor` needing `""` not `None`). No live Plaid credentials exist in
this sandbox, so the real network calls themselves remain unverified
against Plaid's actual API, same honest caveat as every other Plaid
entry above.

## v0.20 — Music module: real local library + playback (2026-09-09)

A "broader project punch list" survey of ROADMAP/KNOWN_ISSUES/VISION
found no other ready-to-build gap this round (the two remaining
ROADMAP checkboxes are genuinely hardware-blocked; the open
KNOWN_ISSUES items all need the user's real machine). User picked
"Revisit the Music module stub" — `modules/music/module.py` was the
last remaining pure-placeholder module, historically documented (as
far back as the v0.10 breakdown above) as blocked on a missing
`libpulse`/PortAudio system dependency with no sudo access.

**That blocker no longer holds — re-verified directly, not assumed**:
`PySide6.QtMultimedia` imports cleanly, `QMediaDevices.audioOutputs()`
returns a real device, `QMediaPlayer`/`QAudioOutput` construct with
zero error on a real bundled FFmpeg 7.1.3 backend; `sounddevice` also
now works. `dpkg -l` confirms `libpulse0`/`pulseaudio-utils`/
`libasound2t64`/`libportaudio2` are all now installed where they
weren't before — see `docs/KNOWN_ISSUES.md`'s matching Closed entry.
User confirmed, given this: full local library + real playback, not a
browsing-only slice.

New `core/music_manager.py` (`AppContext.music`): `Track`/`Playlist`
persisted-JSON records (two sibling files, same "one manager, several
lists" convention as `core/budget_manager.py`), `scan_library()`
walking a configured `music.library_root_path` (same empty-string-
default pattern as `maps.trail_map_root_path`) for `.mp3`/`.flac`/
`.ogg`/`.m4a`/`.opus`/`.wav` files, reading tags via the new `mutagen`
dependency. **Deliberate divergence from `core/trail_map_library.py`**:
files are referenced at their real path, never copied into an app-
owned root — a personal music library already exists elsewhere on
disk, often many GB. `scan_library()` skips re-reading tags for a
file whose `(size, mtime)` hasn't changed since the last scan (the
real cost a large library needs to avoid), and **never auto-creates or
touches the index if `root_path` is missing** — a temporarily-
unmounted drive must never look like "the whole library vanished."

**Playback owns a real, lazily-constructed `QMediaPlayer`/
`QAudioOutput` directly in `core/`**, matching `core.voice_manager
.VoiceManager`'s own precedent of owning real non-widget audio
playback in `core/` (not `core.avatar_manager.AvatarManager`'s
stricter "gui/ owns rendering" split, which is specifically about
widget/video-surface rendering — `QMediaPlayer` has no widget at all).
Construction is lazy so `scan_library()`/CRUD tests stay entirely
Qt-free. **Real, honest limitation, documented in the module's own
docstring**: `core/voice_loop.py` (the headless MIA Core entry point)
runs with no Qt event loop at all — `VoiceManager` uses `sounddevice`
instead of Qt for exactly that reason — so if `context.music` is ever
driven from that headless path, `QMediaPlayer` would silently produce
no audio even though the calls return success. The normal GUI boot
path and the GUI's own Assistant chat path (confirmed: the handler
call happens on the main GUI thread, not inside `ChatWorker`'s
`QThread`) are both safe.

`modules/music/module.py`: Library tab (search + scan + play/add-to-
playlist) and Playlists tab (create/rename/delete + per-playlist track
list), plus a persistent transport bar (survives tab switches and
navigating to a different module entirely, since `gui/main_window.py`
caches module widgets forever) with play/pause/stop/previous/next, a
seek slider and a volume slider both drag-guarded with the exact
`isSliderDown()` pattern `gui/home_dashboard.py`'s Volume card already
established — Music's own volume is deliberately separate from
`context.volume` (system-wide ALSA), a standard per-player concept.
New `gui/add_edit_playlist_dialog.py`, minimal single-field dialog.

9 new Assistant actions, `domain="music"` (`play_track`/`play_playlist`/
`pause_music`/`resume_music`/`stop_music`/`next_track`/`previous_track`/
`set_music_volume`/`get_now_playing`) — confirmed via direct grep, zero
existing trigger-phrase collisions for play/pause/skip/volume/next/
previous anywhere in the registry; the only real risk was an unscoped
bare `"stop"` (already means `"stop tracking"` under `maintenance`),
avoided by keeping every Music trigger specific ("stop the music").
Verified against the real, fully-wired registry (`object.__new__
(MIAApplication)` + `_register_assistant_actions()`, same construction
`tests/live_model_check.py` already uses): all 9 real prompts attach
only the `music` domain, and "stop tracking my truck" attaches only
`maintenance` — zero collision, confirmed not assumed.

**Verified for real, multiple layers**: `tests/test_music_manager.py`
(37 new tests, Qt-free — CRUD/`scan_library()` against real synthesized
WAV files with real mutagen-written ID3 tags, playback logic against a
monkeypatched fake player, matching `tests/test_avatar_manager.py`'s
established convention of keeping Qt out of pytest entirely) +
`tests/test_music_module.py` (pure formatting functions). New
`tests/core_live_music_check.py` (manual, not pytest, mirrors
`tests/core_live_voice_check.py`'s "real hardware, run by hand" shape
but needs no Ollama/LLM at all) drove a full real play → pause →
resume → seek → set_volume → stop round trip against the actual
QtMultimedia/FFmpeg backend — real position genuinely advanced in real
wall-clock time (0.371s → 0.835s across a pause/resume gap), confirming
this isn't just "the objects construct," it's "real audio decode and
timing actually works" in this sandbox. 1810 tests passing.

## Financial deep-dive, part 1: two real bugs fixed (2026-09-09)

A brainstorm on "perfecting" the financial side (grounded in a real
survey of `core/budget_manager.py`/`core/real_estate_manager.py`/
`core/plaid_manager.py`/`core/business_report.py`, not guessed) found
two real bugs worth fixing before any bigger feature work.

**(1) `Bill`/`IncomeSource` never had an `entity_id` field at all** —
`IncomeEntry`/`ExpenseEntry` got one when LLC tagging shipped
(2026-09-08), but `Bill`/`IncomeSource` were a real, deliberate scope
cut at the time (confirmed, not silently redone). That meant the two
*automated* recording paths, `mark_bill_paid()`/`mark_income_received()`
— the ones that actually fire for a recurring bill/paycheck — could
never attribute anything to an LLC, only ad-hoc manual entries could.
Added `entity_id: str = ""` to both dataclasses, wired `add_bill()`/
`add_income_source()`, and both auto-recording methods now pass the
bill's/source's own `entity_id` through to the `ExpenseEntry`/
`IncomeEntry` they create. New Entity combo on `gui/add_edit_bill_dialog
.py`/`gui/add_edit_income_source_dialog.py`, same shape `gui/add_edit_
income_dialog.py`'s combo already established. **Deliberately entity_id
only, not property_id** — mirrors exactly what the generic Income/
Expense dialogs already expose; a property-linked entry only ever gets
`property_id` through `RealEstateManager`'s own rental-income/expense
flow, which has no analog for Bills/IncomeSources.

**(2) The dashboard's Net Worth card silently excluded the native Real
Estate module's own tracked-property equity** — it only ever summed
external `FinancialSnapshot` sources (Kraken/Plaid/Homestead/real-
estate-export). A user who only used the native module and never
imported an external snapshot saw "No financial snapshots imported
yet." even with real tracked properties — flatly wrong, not just
incomplete. `format_net_worth_line()` gained a `property_portfolio_equity`
parameter (`None`, never a fabricated `0.0`, when there are no
properties — same "missing means excluded" convention every other
contribution here already follows); `_refresh_net_worth()` now computes
it from `context.real_estate.all_properties()` via the same
`property_equity()` function `format_property_portfolio_line()` already
uses.

**Verified for real**: `mark_bill_paid()`/`mark_income_received()`
copying a real `BusinessEntity`'s id onto the resulting expense/income
entry, both dialogs' Entity combo round-tripping through a real seeded
entity list, and the Net Worth card showing a real dollar figure for
properties-only data with zero external snapshots — all confirmed via
isolated headless-Qt scripts, not just unit tests. 1902 tests passing.

## Financial deep-dive, part 2: Plaid category coverage (2026-09-09)

Second item in the same brainstorm sequence. Six real Plaid primary
categories — `MEDICAL`, `PERSONAL_CARE`, `GENERAL_MERCHANDISE`,
`BANK_FEES`, `ENTERTAINMENT`, `TRAVEL` — had no matching entry in
`core.budget_manager.EXPENSE_CATEGORIES`, so `map_plaid_category()`
fell every one of them through to `"Other"` (confirmed directly in the
function's own pre-existing fallthrough comment, which already named
all six). For anyone with real Plaid-synced spending, a meaningful
fraction of actual transactions were landing in a single catch-all
bucket, weakening both budget-target comparison and the Business
Report's per-category breakdown.

Added six new `EXPENSE_CATEGORIES` entries (`Medical`, `Personal Care`,
`Shopping`, `Bank Fees`, `Entertainment`, `Travel` — `GENERAL_MERCHANDISE`
maps to `"Shopping"`, the more natural household-budgeting term) and a
matching branch in `map_plaid_category()` for each. No other code
needed updating — every consumer of `EXPENSE_CATEGORIES` (the Bill/
Expense dialogs' category combo, the Budget Targets section's one-row-
per-category loop, the Business Report's category breakdown table)
already iterates the list generically rather than hardcoding its
contents, confirmed by grep before assuming so.

One existing test corrected, not just extended: `test_map_plaid_
category_unrecognized_expense_primary_is_other` had been using real
`"ENTERTAINMENT"` as its example of an unrecognized category — now
genuinely recognized, so it failed once this landed (a real, caught-
by-the-test-suite signal, not silently papered over). Fixed by
switching that test to a clearly-fictional placeholder category
(matching what the function's own docstring already says that test
is really about — "any primary value Plaid adds in the future that
this function doesn't recognize"), and added 6 new tests for the real
categories themselves. 1908 tests passing.

## Financial deep-dive, part 3: per-entity Budget Targets (2026-09-09)

Third item in the sequence. `BudgetTarget` was one global planned-
amount per category — a household and an LLC sharing one Budget
couldn't have separate targets for the same category name (e.g.
"Utilities"). Added `entity_id: str = ""` to `BudgetTarget` (`""` is
the household/unassigned bucket, same convention every other
`entity_id` field here already uses) and re-keyed the upsert from
`category` alone to the `(category, entity_id)` pair —
`set_budget_target()`/`get_budget_target()`/`delete_budget_target()`
all take an optional `entity_id` (default `""`). `all_budget_targets()`
gained the same `entity_id` parameter, with `None` (default) meaning
"no filter, return everything across every entity" — same convention
`total_income()`/`total_expenses()` already use — while every caller
that needs a single, well-defined row-per-category view (the Summary
tab's Budget Targets section, the Business Report) always passes an
explicit value.

**A real design decision, not left implicit**: "All Entities" in the
Summary tab's entity filter has no sensible single planned-amount to
show per category once more than one entity can have its own target
for the same name — so the Budget Targets section (and the Business
Report's Budget-Targets-vs-Actual comparison) deliberately collapses
"All Entities" down to the household/unassigned bucket, same as
explicitly picking "(Unassigned)". Refactored the section to refresh
in place (`_refresh_budget_targets()` — updates spin values, actual-
spend labels, and the group's own title to show which entity it's
scoped to) rather than rebuild, wired to the same entity-combo change
signal the Summary labels already refresh on.

**A real bug caught and fixed before it shipped, not after**: the
Business Report's own "actual" spend for the targets comparison
originally still used the *raw*, unfiltered `entity_id` (`None` under
"All Entities") while `budget_targets` used the newly-collapsed
household-only value — under "All Entities" this would have shown a
household-only target next to an actual figure summed across every
entity, a confusing apples-to-oranges mismatch. Caught by reasoning
through the two numbers' consistency before running anything, not by
a failing test — fixed by resolving both sides through the same
collapsed `entity_id` (the report's other totals/breakdowns
deliberately keep the raw, unfiltered `entity_id` — only this one
comparison needed the collapse).

**Verified for real**: a real isolated headless-Qt script seeded a
household Groceries target ($400, $120 actual) and a separate LLC
Utilities target ($250, $80 actual) sharing the same Budget — switching
the entity filter correctly showed $400/$0 (household) vs. $0/$250
(LLC) with the group title updating to name the selected entity, and
each side's actual-spend figure correctly excluded the other entity's
expenses. 1913 tests passing.

## Financial deep-dive, part 4: real estate depreciation tracking (2026-09-09)

Fourth item in the sequence. `core/real_estate_manager.py` tracked
current value, mortgage balance, and equity but had no depreciation
concept at all — a standard, expected piece of real estate accounting
that was simply never built. Added `land_value`/`placed_in_service_date`
to `Property` and three new pure functions — `depreciable_basis()`,
`annual_depreciation()`, `accumulated_depreciation()` — computing real
straight-line depreciation (the standard MACRS method for residential
rental real property, 27.5 years, IRS Publication 946). **Deliberately
does not implement the mid-month convention** IRS Form 4562 technically
requires for the placed-in-service/disposal years — same "real correct-
shaped number, not fabricated precision" boundary
`core.maintenance_manager`'s Prediction feature already draws. Only
Rental/Investment property types are eligible — a Primary Residence
returns `$0` even with a real depreciable basis, since it's never
depreciated for tax purposes. New Land Value/Placed in Service Date
fields on the Add/Edit Property dialog (the latter auto-syncing to
Purchase Date for a brand-new property, adjustable if it genuinely
differs); two new labels on the property detail view; a new "Annual
Depreciation" column on the Business Report's portfolio table.

**A real, multi-round rendering bug found and fixed through iterative
visual verification, not assumed fixed after one pass**: adding an 8th
column to the portfolio table (already known-fragile — it had one real
bold-glyph wrapping bug fixed earlier this session) broke wrapping
badly enough that even the Property name column wrapped, not just
numeric cells. `nowrap` alone didn't fix it; a smaller font size alone
didn't fix it; `<colgroup>`/`<col width=...>` (both CSS `style` and
plain HTML `width` attribute forms) turned out to be **silently
ignored entirely** by Qt's `QTextDocument` HTML engine — confirmed by
a real, byte-for-byte-identical rendered PDF before and after changing
those values, not assumed. The actual fix: `width="X%"` set directly
on each `<th>` in the header row (which Qt *does* honor), combined
with switching Current Value/Mortgage Balance/Equity/NOI to whole-
dollar formatting — legitimate for Current Value/Mortgage/Equity since
those are already manually-entered estimates (cents there were false
precision, not real data), and a deliberate summary-table display-
rounding choice for NOI (the underlying real transaction data keeps
full cent precision everywhere else in the app). Stress-tested with
7-figure property values ($1.28M) after the realistic-scale case
looked clean, to confirm the fix generalizes rather than just
happening to work for the one dataset tried first.

**Verified for real**: 32 new tests for the three depreciation
functions (Rental/Investment eligibility, Primary Residence/Land
returning $0, the `placed_in_service_date`-falls-back-to-`purchase_date`
rule, clamping at $0 before the start date and at the full basis once
fully depreciated); multiple real rendered-PDF-to-PNG visual passes
(not just unit tests) confirming the portfolio table's final form at
both realistic and stress-test dollar magnitudes; a real headless-Qt
script confirming the Add/Edit Property dialog's new fields round-trip
correctly and the detail view's two new labels show real, correctly-
computed figures. 1929 tests passing.

## Financial deep-dive, part 5: Schedule E prep view (2026-09-09)

Fifth item — "tax support," the vaguest brainstorm item, deliberately
narrowed with the user first: a Schedule E prep view now, 1099/
contractor tracking as an immediate follow-up. Stays inside this
app's own stated boundary ("no tax computation... no brackets, no
liability estimate, no filing support," `core/budget_manager.py`'s own
docstring) — real per-property income/expense data reorganized into
the actual IRS Schedule E (rental real estate) line structure, for the
user/their accountant to transcribe directly. Never a computed tax
liability, never filing-ready, and the rendered report says so
directly in its own caveat paragraph.

New `core.business_report.category_to_schedule_e_line()` maps MIA's
own `EXPENSE_CATEGORIES` onto real Schedule E lines (Insurance→
Insurance, Maintenance→Repairs, Taxes→Taxes, Utilities→Utilities,
Mortgage/Rent→Mortgage Interest) — deliberately conservative, same
"unmapped falls to Other" precedent `core.plaid_manager
.map_plaid_category()` already established, since MIA's household
categories (Groceries/Transportation/Medical/etc.) have no real
Schedule E correspondence. **A real, honest limitation stated directly
in the rendered report**: the Mortgage Interest line is the FULL
Mortgage/Rent category amount, since MIA doesn't track a mortgage
payment's principal/interest split yet (that's the separate, later
mortgage-amortization item) — likely overstates deductible interest,
and says so in plain language rather than silently mislabeling it.
Renamed `core.real_estate_manager._DEPRECIABLE_PROPERTY_TYPES` to
public `SCHEDULE_E_ELIGIBLE_PROPERTY_TYPES` — depreciation eligibility
and Schedule E eligibility are the same real tax-law rule (only
Rental/Investment types), so both now share one constant instead of
the same rule living under two different names in two files.

New per-property Schedule E section on the Business Report, gated to
`range_label == "This Year"` only (Schedule E is inherently an annual
form — showing a partial month or a multi-year range would never map
to one real filing year), mirroring exactly how Budget Targets is
already gated to "This Month" only.

**A real, deliberate accounting-convention fix, caught by actually
looking at a rendered loss, not assumed correct**: a negative Net
Income (Loss) first rendered as "$-881.82" — technically correct but
not how an accountant reads a loss. Fixed to the real "($881.82)"
parenthesized convention, since this document is explicitly framed as
being for the user's/their accountant's reference.

**Verified for real**: new tests for every real category mapping and
the Other fallback, zero-amount line suppression, Total Expenses/Net
Income (Loss) math, the not-tax-advice and mortgage-interest caveat
text, and the accounting-parens loss format; a real rendered PDF
(`QtPdf`-to-PNG) with 2 eligible properties (one showing a real loss,
one a real gain) plus one excluded Primary Residence, confirmed
rendering cleanly with no wrapping on the same page that already
proved fragile earlier this session. 1937 tests passing.

## Financial deep-dive, part 6: 1099/contractor payment tracking (2026-09-09)

Confirmed follow-up to Schedule E: real payments to contractors/
vendors checked against the real, stable IRS 1099-NEC threshold
($600/year) — a factual comparison, never a computed tax liability or
a "you must file" directive. `ExpenseEntry` gained `payee: str = ""`
(distinct from `description` — who was paid, not what the expense was
for) and a new `BudgetManager.payees_over_1099_threshold()` sums
payments per payee (case-insensitive grouping, first-seen casing
preserved for display) and returns only those at/over threshold.
**Real IRS rule applied, not guessed**: only expenses tagged with a
`property_id` or `entity_id` count — 1099-NEC obligations arise from
payments made in the course of a trade or business, so a purely
personal household payment (no property/LLC tag) is correctly
excluded even if the payee name matches a real contractor. New
optional Payee field on the Add/Edit Expense dialog.

New "1099-NEC Threshold Check (This Year)" Business Report section,
gated to "This Year" (annual, same reasoning as Schedule E), listing
payees sorted by amount with a caveat that this is a factual threshold
check, not tax advice, and that the payee's own business structure can
still exempt them.

**A real consistency fix made while designing this, not shipped
twice**: `schedule_e_properties` previously used a bare truthy check
(`if schedule_e_properties:`), meaning "This Year, zero eligible
properties" was indistinguishable from "not This Year at all" — and
`_schedule_e_table()`'s own "No Rental/Investment properties tracked."
empty-state message was unreachable dead code as a result. Both
`schedule_e_properties` and the new `payees_over_threshold` now use an
explicit `None`-vs-real-value sentinel: `None` omits the section
entirely (not this range), a real empty list/dict still renders the
section with its own honest "nothing to show" message (a genuinely
different, meaningful state).

**Verified for real**: new tests for the threshold check (below/at/
over threshold, personal-payment exclusion, case-insensitive grouping,
entity/date filtering, custom thresholds), the corrected `None`-vs-`[]`
semantics for both annual sections (a real gap in the existing test
suite, now covered), a headless-Qt check of the new Payee field
round-tripping through the dialog, and a real rendered PDF showing
both 1099 payees sorted correctly with no wrapping. 1954 tests passing.

## Financial deep-dive, part 7: trend/history views (2026-09-09)

Budget module gained a 7th tab, Trends, charting Income vs. Expenses
for the last 12 calendar months as a grouped bar chart — the Summary
tab only ever showed a single-range snapshot (This Month/Year/All
Time), with no way to see whether spending or income was actually
trending. Reuses the `QtCharts` precedent already established in
`modules/lab/module.py`, extended from a bare index-based line to a
categorical axis with real month labels and two side-by-side series
(`QChart`/`QChartView`/`QBarSeries`/`QBarSet`/`QBarCategoryAxis`/
`QValueAxis`) — confirmed these constructs cleanly in the installed
PySide6 version before building. No new historical-snapshot storage:
each month bucket is computed on demand from the existing
`BudgetManager.total_income()`/`total_expenses()`, since real Income/
Expense entries already carry real dates.

New pure `month_buckets(today, count=12)` helper (module.py) returns
oldest-first `(label, start_date, end_date)` tuples, handling
leap-year February and year-boundary rollover correctly. The Trends
tab reuses the same entity-filter convention as the Summary tab
(`_populate_entity_combo()` was factored out of `_refresh_entity_combo()`
so both combos stay in sync); Income/Expenses get a deliberate, fixed
blue/orange color pair — not Qt's auto-cycled series colors — chosen to
avoid the classic red/green colorblind-ambiguous pairing while staying
intuitive, with a legend so identity never depends on color alone. A
net-cash-flow label sums the displayed window.

**Verified for real**: new `month_buckets()` tests (count, ordering,
exact start/end dates, Dec→Jan rollover, leap and non-leap February).
1960 tests passing. Manual headless-Qt screenshot with real seeded
income/expense data spanning 12 months confirmed the chart renders
correctly — real month labels, both series visible with legend, correct
totals — and that switching the entity filter works without error.

## Financial deep-dive, part 8: Business Report consolidation (2026-09-09)

Last two real gaps from the financial-manager brainstorm for the
Business Report: no Investments/Net Worth section at all (despite this
app tracking Plaid balances, Plaid investment holdings, Kraken crypto,
and native Real Estate equity), and the report always being scoped to
exactly one entity/household bucket per run. New "Net Worth by Source"
section (reuses the existing `_category_table()` as-is) and new
"Investment Holdings" table (institution/security/ticker/quantity/
value, sorted by value, real empty state) — both household-wide, since
`FinancialSnapshot` has no entity concept at all in this codebase, so
they're shown once per document rather than filtered per LLC.

New `build_consolidated_business_report_html()` in
`core/business_report.py` composes one document covering every entity/
household bucket at once: a comparison table (Entity/Income/Expenses/
Net Cash Flow/Property Equity with a bold Total row) followed by each
bucket's own ordinary per-entity report body, page-broken between them
— confirmed via a real rendered PDF that Qt's `page-break-before: always`
actually works (unlike `<colgroup>` width, found earlier this session
to be silently ignored). `include_net_worth_section: bool = True` is a
new, deliberately separate mechanism from the existing `None`-vs-empty
gating `schedule_e_properties`/`payees_over_threshold` use — this one's
a structural "don't repeat this shared section per entity" concern, not
a "this doesn't apply to the selected range" business rule.

`modules/budget/module.py`'s existing per-entity gathering logic
(budget targets, properties, Schedule E, 1099) was extracted into
`_gather_entity_report_kwargs()` — used by both the existing single-
entity export and each bucket of the new "Export Consolidated Report
(All Entities)…" button, so the real logic lives in one place instead
of being duplicated. Every bucket is always included in the
consolidated document, even one with zero activity — same "never
silently drop, show the honest empty state" convention already used
everywhere else in this report.

**Verified for real**: 10 new tests (Net Worth/Investments rendering
and empty states, `include_net_worth_section` suppression, the
consolidated builder's comparison-table totals and per-entity bodies).
1970 tests passing. A real rendered PDF with 3 buckets (household +
2 LLCs, one deliberately left with zero activity), real Plaid balance/
holdings-shaped data, and a tracked property confirmed: the comparison
table's totals are correct, Net Worth/Investments appear exactly once,
each entity gets its own page via a real page break, and the zero-
activity LLC still renders its own honest empty-state report rather
than being silently dropped.

## Financial deep-dive, part 9 (final): mortgage amortization (2026-09-09)

Last item in the financial deep-dive sequence. `Property` gains four
optional loan-term fields (`original_loan_amount`, `interest_rate_pct`,
`loan_term_months`, `loan_start_date` — falls back to `purchase_date`,
same convention `placed_in_service_date` uses) and
`core/real_estate_manager.py` gains real fixed-rate amortization math:
`monthly_payment()` (the standard `M = P·r(1+r)^n / ((1+r)^n − 1)`
formula, hand-verified against a real $300k/6.5%/360mo figure),
`amortization_schedule()` (a full month-by-month principal/interest/
balance breakdown), `interest_paid_in_range()`/`principal_paid_in_range()`,
`remaining_balance_as_of()`, and `payoff_date()`. All treat missing
loan terms (`has_loan_terms()` false) as "no amortization data," never
a guessed default. The projected remaining balance is deliberately kept
separate from `Property.mortgage_balance` (the manually-tracked figure
equity/NOI/the portfolio table already use) — a real mortgage can
diverge from a clean schedule (extra principal, a refinance), so the
two are never conflated; the Real Estate module's detail page labels
the new figures "(per loan terms)" to keep that honest.

`gui/add_edit_property_dialog.py` gained the four matching fields;
`modules/real_estate/module.py`'s detail page now shows Monthly Payment
(P&I), Est. Remaining Loan Balance, and Est. Payoff Date (or "enter
loan terms to calculate" when unset).

**The real Schedule E fix this was all building toward**: the Schedule
E view has carried a caveat since it shipped that its "Mortgage
Interest" line uses the FULL Mortgage/Rent category amount because MIA
didn't track the principal/interest split — real IRS rule: only the
interest portion is ever deductible, principal repayment is a balance-
sheet reduction, never a Schedule E expense line. `modules/budget/module.py`'s
`_gather_entity_report_kwargs()` now substitutes the real interest-only
figure (`interest_paid_in_range()`) whenever a property has loan terms
entered, falling back to the old full-amount behavior otherwise — the
caveat text in `core/business_report.py` was updated to describe both
cases honestly rather than unconditionally warning about a gap that no
longer always exists.

**Verified for real**: 27 new tests in `tests/test_real_estate_manager.py`
(monthly payment against a hand-verified real figure, full schedule
correctness — first-month interest/principal, final balance reaches
zero, total principal equals the loan amount — range-scoped interest/
principal sums, remaining balance before/mid/after the term, payoff
date, backward-compat defaults, negative-value clamping). 1992 tests
passing. A real rendered PDF comparing a property with loan terms
entered (correctly showing $14,839.23 real interest instead of a
$16,780 full payment — a genuine ~$1,940 difference this fix corrects)
against one without (old behavior, unchanged) confirmed the fix changes
the actual rendered number, not just the code path. A headless-Qt
screenshot of the dialog's four new fields confirmed clean layout with
no clipping and a correct round-trip through the dialog's own
`entered_*` properties.

## Settings: profile rename + password change (2026-09-10)

Closes the last real gap behind `modules/settings/module.py`'s own
long-standing "User info and module toggles remain a placeholder for a
future milestone" docstring note — module toggles already existed
elsewhere (the Modules screen), but there was genuinely no way anywhere
in the app to rename a profile or change its password after initial
setup. New `core.profile_manager.rename_profile()` (same CRUD shape as
`set_birthday()`/`add_xp()`), publishing a new `"profile.renamed"`
event. No new password-manager method was needed — the existing
`set_password()` (set-or-remove, no verification of its own — it's
also the raw primitive `create_profile()` uses) plus `verify_password()`
were enough once the module layer does the "confirm the current
password first" step itself, reusing `gui/password_dialog.py`'s
existing `prompt_for_password()` the exact same two-call way
`gui/profile_select.py`'s own profile-switch login flow already does.

Two new small dialogs mirroring `gui/add_profile_dialog.py`'s exact
shape: `gui/rename_profile_dialog.py` (one name field) and
`gui/set_password_dialog.py` (a "protect with a password" checkbox +
field; blank means "keep the current password unchanged" when one
already exists, required when setting one for the first time — this
dialog never sees or checks the *current* password itself, since
that's already verified before it's ever opened). Both wired into
Settings' existing "Account" section as new "Rename Profile"/"Change
Password" buttons right under "⇄ Switch User".

**A small, honest propagation fix included in the same pass**:
`gui/main_window.py`'s header avatar button shows the active profile's
first initial + a tooltip with the full name, built once at window
construction — a plain in-place rename never fires the existing
`"profile.switch_requested"` event (no actual switch happens), so the
header would otherwise show the stale old name until the app restarts.
Subscribed to the new `"profile.renamed"` event instead and update the
button directly when the renamed profile is the active one — scoped
exactly to the staleness this new feature introduces, not a broader
audit of every other place a profile name might be cached.

**Verified for real**: 7 new tests in `tests/test_profile_manager.py`
(rename persists across a fresh load, strips whitespace, rejects a
blank name, returns `False` for an unknown id, publishes
`"profile.renamed"` with the right payload, preserves every other
profile field — password/birthday/XP — across a rename). 1999 tests
passing. A headless-Qt screenshot of the Account section showing both
new buttons; both dialogs screenshotted in isolation (with and without
an existing password) confirming clean layout; and a full manual
walk-through via direct manager calls in an isolated `ConfigManager`
covering every real path: wrong current password rejected, correct
current password + blank new password leaves the old one working,
correct current password + a real new password changes it (old one
stops verifying, new one works), and removing protection entirely
makes `verify_password()` auto-pass again.

## New-user exploration follow-up: 5 fixes (2026-09-10)

Acted as a brand-new user across Music/Real Estate/Budget this session
(isolated data dirs, real interaction, real screenshots) specifically
to find rough edges — five real, reproduced findings, all fixed:

1. **Budget's Summary/Trends tabs went stale.** None of Bills/Income
   Sources/Income/Expenses' add/edit/delete/mark-paid/mark-received
   handlers ever refreshed Summary or Trends — only their own tab's
   list. Confirmed: add a real Expense, switch to Trends, see a
   completely empty chart despite real data existing (the exported PDF
   was always correct — it queries fresh data directly — only these
   two on-screen tabs lied). Fixed with one `tabs.currentChanged`
   connection refreshing Summary/Budget Targets/Trends on every tab
   switch — all three are cheap in-memory recomputations, and none of
   them reset the user's chosen range/entity filter.
2. **Empty lists showed a blank void.** Bills, Real Estate's property
   list and its Rental Income/Expenses sub-lists, and Music's Library/
   Playlists/playlist-tracks all rendered as a totally empty rectangle
   on first use, with zero guidance — unlike the Home Dashboard's own
   widgets, which already say "No X tracked yet." New
   `gui/list_widget_helpers.add_empty_state_item()` (a single,
   disabled, non-selectable placeholder row) applied across all 10
   call sites, each with a tailored message — including a real/honest
   distinction between "genuinely empty" and "filtered to zero
   results" where a search box is involved (Bills, Income Sources,
   Music Library).
3. **Real Estate depreciation could silently mislead.** An unset Land
   Value (`0.0`, the field's own default) means the FULL purchase
   price is treated as depreciable — a real, inflated number shown
   with zero caveat. Fixed by appending "(land value not set — this
   may overstate depreciation)" to the Annual/Accumulated Depreciation
   labels whenever this applies — same honest-caveat convention this
   exact view's Cap Rate figure already uses.
4. **`currentItem()` vs. actual selection mismatch, ~26 call sites.**
   Qt's default `ExtendedSelection` mode keeps `currentItem()` set even
   after a Ctrl+click deselects that row (`clearSelection()` doesn't
   clear it) — every "Edit Selected"/"Play"/"Remove"-style button
   across the app could silently act on a row that no longer looks
   selected. New `gui/list_widget_helpers.selected_item_data()`
   (requires `.isSelected()`, not just "is current") replaces every
   `_selected_*_id()`-style method's own `currentItem()` body across
   Budget/Real Estate/Music — confirmed via a direct repro (select a
   track, `clearSelection()`, click Play — now correctly shows "No
   Track Selected" instead of silently replaying).
5. **Negative amounts silently clamped to $0.00 and still created a
   phantom record.** `add_bill()`/`add_income()`/`add_expense()`/
   `add_income_source()`/`set_budget_target()` all did
   `max(0.0, amount)` rather than rejecting bad input. Confirmed
   unreachable through any real GUI path today (every relevant spin
   box already floors at 0) and confirmed Plaid sync already does
   `amount = abs(txn.amount)` and skips `txn.amount == 0` before ever
   calling these — pure defensive dead code today, fixed anyway so it
   can't quietly bite a future caller (a new Assistant action, a
   future import source). Now `raise ValueError` for a genuinely
   negative amount; exactly `0.0` stays allowed (a real, reachable
   value through the GUI's own spin box floor).

**Verified for real**: 8 new tests in `tests/test_budget_manager.py`
(each of the 5 methods rejects negative, still accepts `0.0` and
positive values). 2007 tests passing. Re-ran the same isolated "new
user" exploration scripts that found these issues in the first place
to directly confirm each fix — adding an Expense now updates
Summary/Trends immediately, every previously-blank list now shows its
message, a property with no Land Value shows the new caveat, the
Ctrl+click-deselect repro now correctly blocks Play, and a negative
`add_expense()` call now raises. This codebase's pytest suite stays
deliberately Qt-widget-free (confirmed by checking existing module
test files before adding new ones) — `add_empty_state_item()`/
`selected_item_data()` are exactly the kind of real-widget-behavior
code this project verifies via manual headless-Qt scripts instead,
not new pytest coverage.

## Kitchen module: recipes, pantry, grocery list, nutrition, meal-frequency, suggestions (2026-09-10)

Closes `docs/VISION.md`'s Kitchen Module bullet — the last remaining
named module from that list — at the user's explicit request to build
the full scope (recipes, pantry inventory, grocery lists, nutrition,
meal-frequency tracking, and suggestions from what's on hand) rather
than a narrower slice.

New `core/kitchen_manager.py` — one manager, several related
dataclasses (`Recipe`/`PantryItem`/`GroceryListItem`/`MealLogEntry`),
same shape as `core/budget_manager.py`. Deliberately its own manager,
not a reuse of `core/inventory_manager.py`'s generic Toolbox Inventory
tool — direct precedent from `docs/ROADMAP.md` milestone 8.3, which
rejected exactly that reuse for Workshop's own component DB ("mixing
kitchen supplies and resistor stock into one list serves neither
well"). Ingredients are plain dicts on `Recipe.ingredients`
(`{"name","quantity","unit","notes"}`), edited one at a time from the
recipe's own detail page via `gui/add_edit_ingredient_dialog.py` — the
real, confirmed codebase convention (`gui/pick_item_quantity_dialog.py`'s
own docstring, and `gui/add_edit_job_dialog.py`'s own docstring
explicitly rejecting an embedded list editor for the directly
analogous Job→materials-consumed relationship) rather than an embedded
multi-row table editor. Units are freeform strings — no conversion
system; nutrition facts are manual entry only — no USDA/nutrition-API
lookup, same "manual now, real integration later" precedent as Energy
tracking and Real Estate's own manually-updated `current_value`.

`recipe_missing_ingredients()` does a case-insensitive name match
against the pantry, and only compares quantities when a matching
pantry item's unit equals the ingredient's unit exactly — otherwise it
falls back to presence-only, a real, honest simplification rather than
fabricating a cross-unit quantity comparison (same boundary
`annual_depreciation()`'s own docstring already draws elsewhere in
this app). `recipes_makeable_from_pantry()` sorts fewest-missing-first,
the engine behind the Suggestions tab.
`add_missing_ingredients_to_grocery_list()` is the real suggestions-
to-action link, skipping ingredients already on the list so repeated
use never piles up duplicates.

`modules/kitchen/module.py`: five tabs (Recipes/Pantry/Grocery List/
Meal Log/Suggestions), `QTabWidget`, same shape as Budget's own
7-tab module. Recipes is itself a `QStackedWidget` list↔detail page,
mirroring `modules/real_estate/module.py`'s exact pattern. Applied the
Summary/Trends staleness fix's own lesson (this same session, Budget
module) proactively from the start here: every tab refreshes on every
`tabs.currentChanged`, since Pantry/Grocery List/Meal Log changes all
affect what Suggestions (and a recipe's own "missing ingredients"
list) shows. Reuses `gui/list_widget_helpers.py`'s
`add_empty_state_item()`/`selected_item_data()` (this same session's
own new-user-exploration fixes) throughout. New dashboard widget
(`format_kitchen_line()` in `gui/home_dashboard.py`) leads with pantry
items expiring within 3 days if any exist, else how many recipes are
ready to make right now, else an honest "no pantry items tracked yet"
— same "critical beats routine status" precedent `format_homestead_line()`
already established.

Five new dialogs (`gui/add_edit_recipe_dialog.py`,
`gui/add_edit_ingredient_dialog.py`, `gui/add_edit_pantry_item_dialog.py`,
`gui/add_edit_grocery_item_dialog.py`, `gui/log_meal_dialog.py`), all
the same `QDialog` + `QDialogButtonBox` + validate-then-expose-via-
`entered_*`-properties shape every dialog in this app already uses.

**Deliberately deferred, not part of this pass**: Assistant actions
(domain="kitchen") — every comparable module this session (Maintenance,
Lab, Music) shipped its module first and got Assistant-wired in a
separate later pass; a Ctrl+K search provider (`on_load()`) — most
recently-built modules (Real Estate, Music) skip this too, it's
explicitly optional per `CLAUDE.md`.

**Verified for real**: 50 new tests (`tests/test_kitchen_manager.py`,
`tests/test_kitchen_module.py`) — CRUD + persistence-across-fresh-load
for all four record types, `days_until_expiration()`'s four real
branches, `recipe_missing_ingredients()`'s exact-unit-match-compares-
quantity vs. mismatched-unit-falls-back-to-presence-only behavior,
`recipes_makeable_from_pantry()`'s sort order, duplicate-skipping in
`add_missing_ingredients_to_grocery_list()`, meal-frequency queries,
and every pure row formatter. 2057 tests passing. A full manual
headless-Qt walkthrough (isolated data dir, same pattern used all
session) confirmed the real end-to-end flow on the first run: two real
recipes with real ingredients, one confirmed fully makeable and one
correctly showing exactly one missing ingredient (a deliberate unit
mismatch on Flour correctly fell back to presence-only rather than
wrongly flagging it missing), "Add Missing Ingredients to Grocery
List" added exactly the one real missing item and correctly no-opped
on a second call, a checked grocery item persisted through the
manager, logging a meal updated `last_made_date`/`times_made`
immediately, and the Dashboard widget correctly led with "1 pantry
item expiring soon" over the routine "recipes ready" count once a
near-expiration item existed.
