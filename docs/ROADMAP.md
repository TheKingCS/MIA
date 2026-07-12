# M.I.A. Roadmap

**See also: `docs/VISION.md`** — the long-term, four-project mission
behind M.I.A. (this device is "Project 1: The Brain" of that larger
picture). This document is the near-term execution plan; VISION.md is
the North Star. Keep them separate — see VISION.md's "why this is a
separate document" section for why that distinction matters.

This is the living plan for M.I.A. beyond v0.1. It exists so scope
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
| **Connected Device Framework** (discover/pair/telemetry/control) | Robots, Drones, Smart Home, Vehicle OBD, Power monitoring |
| **Notes/Journal Engine** (dated, searchable, taggable rich text + voice memo transcription) | Daily journal, Project Manager notes, Lab notes, vehicle notes |
| **Activity/Memory Log** (system-wide event history via the event bus) | Memories section, "what did I do on Project X" queries, Diagnostics history |
| **Global Search** | One search bar over docs, notes, files, inventory, settings, everything |
| **Notification Center** | Any module can raise an alert (low battery, weather warning, medication reminder, backup complete) |
| **Voice Interface (STT/TTS, push-to-talk)** | Assistant, hands-free control of any module |

## Top-level module sections (post-consolidation)

Character, Memories, and Global Search are system-wide / ambient, not
sections themselves — everything below is a menu section:

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
| **v1.0+** | Fleet (Robots/Drones/Vehicle), Communications, Navigation, Agriculture, Medical, Smart Home, Media, Project Manager — added incrementally as real hardware for each is acquired |

## Self-Modification / Dev Mode (staged, deliberately separate from the Assistant phase)

A specific, explicit goal for M.I.A.: an assistant that can eventually
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
      glow core (`gui/boot_core_widget.py`) with "M.I.A." rendered in
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
      M.I.A.'s own docs (`docs/*.md`) and module metadata via
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
      editing M.I.A.'s own source code, gated behind a cautious
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
