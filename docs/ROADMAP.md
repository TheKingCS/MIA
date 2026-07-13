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
| **Connected Device Framework** (discover/identify/pair/telemetry/control) | Robots, Drones, Smart Home, Vehicle OBD, Power monitoring, Field Kit's Connected Device Manager. Starts with physically-attached USB/serial devices (v0.11); wifi/Bluetooth discovery is a planned later extension of the same framework, not a separate one — added when that transport is actually built rather than speculatively now |
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
17. **Field Kit** — connected device detection/identification (USB/serial now, wifi/BT planned), per-device actions (browse files, eject, flash OS + auto-install MIA), useful scripts library, security/network recon + active toolkit, MCU firmware flashing (ties into Workshop & Electronics' own planned "MCU flashing" bullet rather than duplicating it)

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
| **v0.11** | Field Kit — Connected Device Framework (core service, USB/serial detection+identification) + Device Manager UI, OS/MIA flashing+provisioning, useful scripts library, security/network toolkit, MCU firmware flashing tie-in — the third v1.0+-bucket slice buildable with zero real hardware beyond a spare USB drive/SD card, at the user's explicit request to turn M.I.A. into a field engineering/programming tool |
| **v0.12** | Expedition Mode — Expedition + Trip core/CRUD with a Trip activity type (hiking, camping, fishing, kayaking, biking, etc.), campsite/waypoint categories, gear checklist (Inventory-linked or freeform), trip journal with an explicit weather/conditions field, speed & distance from logged checkpoints, a schematic (non-tiled) route map, and trip photos — the fourth v1.0+-bucket slice buildable with zero real hardware, at the user's explicit request for field-ready outing tracking across activity types (live GPS, elevation, automated weather, and real map tiles all explicitly deferred — see the v0.12 breakdown) |
| **v0.13** | Device Profile + Theme System — one codebase, config-driven Core (Pi 5 + AI HAT+ 2) vs. Home (desktop) editions, plus a selectable theme system (Dark Field, Low Energy, Colored, Anime Monochrome) applied at the QApplication level so it can differ in weight between editions |
| **v0.14** | Pi 5 + AI HAT+ 2 deployment readiness — documentation/code-audit pass only (no physical hardware yet): deploy script review, flagged the open AI-HAT-inference-path question and polling-interval power budget as real unknowns to revisit once real hardware exists |
| **v0.15** | Expedition data sync — Pi ("Core") exports Expedition Mode data (expeditions/trips/waypoints/journal/inventory/photos) to a docked USB drive via the Field Kit's existing device detection; Home merges it in by record id (no duplication on re-import) |
| **v1.0+** | Fleet (Robots/Drones/Vehicle), Communications, Agriculture, Medical, Smart Home, Media, Project Manager — added incrementally as real hardware for each is acquired (Media/Music specifically also needs `libpulse`, a system package not installable without sudo in this dev sandbox — confirmed blocked, not just deferred) |

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
- [x] **5.6 Assistant + Reference Library grounding** — the Assistant's
      grounding (5.4) previously only ever searched `docs/*.md`
      (M.I.A.'s own self-documentation), completely separate from the
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
      convinced the model the conversation was about M.I.A.'s own
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
      real command/code execution, not CRUD on M.I.A.'s own data — and
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
Music was considered first but is blocked here: `PySide6.QtMultimedia`
fails to import in this dev sandbox at all (missing `libpulse.so.0`, a
system package, same "no sudo" wall as `sounddevice`/PortAudio in
milestone 5.3) — confirmed blocked, not just deferred, so nothing in
that section can be verified here right now.

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

**Field Kit** — requested directly by the user to turn M.I.A. into "the
most useful offline engineering and field programming tool": detect and
identify devices physically plugged into the Pi, act on them (browse
files, flash an OS + auto-install M.I.A., flash MCU firmware), plus a
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
      first-boot script that auto-installs M.I.A. to a selected storage
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
      config) or elevated privileges, and M.I.A. runs as a systemd
      **user** service, not root — whether the target Pi OS deployment
      has the right permissions out of the box is genuinely unknown
      until tested on real hardware; (b) Raspberry Pi OS images ship
      `.img.xz` compressed, raising a streaming-decompress-while-writing
      vs. decompress-then-write design choice; (c) the actual first-boot
      M.I.A. auto-install mechanism (what gets written into the image's
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
- [ ] **11.5 Security/Network Toolkit** — recon tools (port scanner,
      wifi/network analyzer, hash identifier, subnet calculator) plus
      active tooling (hash cracking, packet crafting, exploit-framework
      launching) wrapping already-installed system tools (nmap, John/
      Hashcat, etc.) rather than reimplementing them — M.I.A. provides
      the offline-friendly UI/launcher, not the underlying capability.
      Network-facing recon (packet sniffer, wifi/BT scanning) is
      reconciled with, not duplicated from, the still-unbuilt
      Communications section (`docs/ROADMAP.md`'s v1.0+ bucket) when
      that section is eventually built.
- [ ] **11.6 MCU firmware flashing** — ties Workshop & Electronics'
      already-planned (but unbuilt) "MCU flashing" bullet to 11.1's
      serial-device detection: flash firmware via `esptool`/`avrdude`
      wrappers to an identified, currently-attached board, rather than
      inventing a second, separate device-detection mechanism for it.

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
prepare M.I.A. for its real target hardware (a Pi 5 + AI HAT+ 2, which
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
