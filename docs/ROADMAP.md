# M.I.A. Roadmap

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
| **v1.0+** | Fleet (Robots/Drones/Vehicle), Communications, Navigation, Agriculture, Medical, Smart Home, Media, Project Manager, Memories AI-query — added incrementally as real hardware for each is acquired |

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


## v0.2 breakdown (current phase — in progress)

Splitting the System layer into small, independently testable milestones:

- [x] **2.1 Kiosk boot infrastructure** — systemd service, autologin,
      fullscreen launch, crash-restart behavior
- [ ] **2.2 User profiles** — multi-user support, per-user config/data
      separation, profile switcher on the setup/login flow
- [ ] **2.3 Notification Center** — core service + UI (toast/banner +
      a persistent notification list), any module can raise one
- [ ] **2.4 Global Search** — index across config, notes, files,
      module metadata; search bar accessible from anywhere
- [ ] **2.5 Module Manager UI upgrade** — enable/disable modules,
      reload without full restart
- [ ] **2.6 System Logs viewer** — read `logs/mia.log` in-app
      (Diagnostics module's first real feature)
- [ ] **2.7 Backup/Restore** — export/import config + data directory
- [ ] **2.8 Update Manager (local)** — apply an update package from a
      USB drive/local file, no internet required

Each will land as its own milestone with a short manual test checklist.
