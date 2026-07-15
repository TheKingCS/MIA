# Full App Walkthrough — current-state acceptance checklist

Created 2026-07-15. The per-milestone guides in this folder
(`2.1_kiosk_boot.md` through `4.4_install_content_pack.md`) stop at an
early point in this project's history — everything since (the entire
Assistant/LLM era, Expedition Mode, Missions, Project Manager, Field
Kit, the four themes, the whole companion-philosophy pass, voice) has
never had a walkthrough at all. This is that: one connected pass over
the **current** app, not a per-milestone archive. Re-run this after any
change that could plausibly touch the Assistant, a module's core CRUD,
or a cross-cutting service (themes, voice, notifications) — and update
this file itself when a section goes stale, the same discipline
`docs/ROADMAP.md`/`docs/VISION.md` already hold themselves to.

**Automated coverage this checklist does NOT re-litigate**: `pytest -q`
(1085+ pure-logic/unit tests) and `python tests/live_model_check.py`
(68-case tool-calling golden set against the live model) already run
fast and repeatably — run those first, and only walk through this
checklist for what they can't cover: real Qt rendering, real audio,
real multi-screen navigation, and subjective "does this feel right"
judgment calls.

**Mark each hardware-dependent item explicitly** — this dev sandbox has
confirmed-blocked system audio (no `libportaudio2`/no real audio
device — see `docs/KNOWN_ISSUES.md`) and no GPS/camera/AI HAT+2. Items
marked **[Pi/HAT only]** below can only be truly verified on real
target hardware; don't treat "couldn't test it here" as "broken."

## 0. Prerequisites

- [ ] `systemctl --user status ollama` — active, or the Assistant's
      tool-calling/chat/memory-extraction/auto-titling all silently
      degrade.
- [ ] `ls voice_models/*.onnx` — at least the default voice present, or
      TTS/STT silently unavailable (logged warning, not a crash).
- [ ] `config/config.json` exists and `system.setup_complete` is `true`
      — otherwise every boot re-triggers the setup wizard.

## 1. Boot & Profiles

- [ ] `~/MIA` launches straight to the Home dashboard (single profile,
      no password) — no setup wizard, no profile selector.
- [ ] If `system.kiosk_mode` is `true`: launches fullscreen;
      `Ctrl+Shift+Q` exits with a confirmation prompt.
- [ ] Switch User (header button) → profile selector → back in.
- [ ] Add a second profile, with and without a password; delete one
      (refuses to delete the last remaining profile).

## 2. Home Dashboard

- [ ] Clock/date update live.
- [ ] **Briefing banner** shows a greeting matching the time of day,
      correctly summarizing active missions / today's calendar events /
      unread notifications / active projects / most recent Memory —
      and omits any category that's genuinely zero (no "0 missions"
      padding).
- [ ] **Briefing is spoken once** on launch (needs real audio — **[Pi
      only]** in this sandbox specifically; synthesis itself is
      verifiable everywhere).
- [ ] Power card shows real battery status, or "No battery or UPS
      detected" gracefully.
- [ ] Volume card: **[Pi only]** for a real `amixer` round-trip; here it
      should show disabled + "Not available on this device."
- [ ] "Open Apps" reaches the full module grid.

## 3. Assistant — text

- [ ] Full-screen Assistant module: ask one info question ("What can
      you help me with?") — gets a warm, in-character reply, not a
      cold refusal.
- [ ] Ask "Can you speak?" / "Do you remember things I tell you?" —
      should correctly say yes to both (this exact pair was a real,
      fixed bug — see `docs/ASSISTANT_CAPABILITIES.md`'s "self-knowledge
      problem" section; worth spot-checking after any prompt change).
- [ ] Tell it a fact ("My name is ___ and I like ___"), start a **new**
      conversation, ask it back — memory should persist across
      conversations via the "🧠 Memories" store, not just within one
      chat.
- [ ] One action-request per domain from `docs/ASSISTANT_CAPABILITIES.md`
      — at minimum: add + list + delete for one CRUD domain (e.g.
      Notes), plus `get_power_status`, `get_system_health`,
      `open_module`. Confirm the on-screen module actually reflects the
      change (not just the chat reply).
- [ ] A destructive action bundled hypothetically shouldn't be
      reachable via a single ordinary message — this is defense-in-depth
      (`split_safe_tool_calls()`), not something to hand-craft a test
      for here; covered by the golden set instead.
- [ ] Sidebar (character panel) chat: text-only by design — confirm it
      does **not** attempt to speak.
- [ ] Suggested-prompt chips in the sidebar change per screen/module.

## 4. Assistant — voice

- [ ] Push-to-talk: hold, speak a short phrase, release — transcribes
      and sends. **[Pi only]** for a real mic; here `start_recording()`
      should fail gracefully (no PortAudio/no device).
- [ ] Settings → Voice: dropdown lists every voice with a model file
      present; selecting one speaks a preview line immediately and
      persists across restart (`voice.tts_voice_id` in config.json).

## 5. Modules — quick CRUD pass

For each: open it, add one item, confirm it appears, edit it, delete
it, confirm search (Ctrl+K) finds it if the module registers a search
provider.

- [ ] **Missions** — add a mission, add an objective (tally and
      trip-duration types), log progress, complete it (confirm a
      celebratory notification fires).
- [ ] **Expeditions** — add an Expedition, add a Trip under it, add
      gear/a journal entry, view the route map (schematic, not a real
      basemap).
- [ ] **Memories** — auto-generated recap for the Expedition above
      appears with correct distance/duration/photo count.
- [ ] **Notes**, **Calendar**, **Alarm** (Toolbox tools) — CRUD; set an
      alarm a minute out and confirm it actually fires a notification.
- [ ] **Inventory** — add an item, +1/−1 quantity buttons, delete.
- [ ] **Project Manager** (Toolbox) — add a project, add a task, mark
      done, delete both.
- [ ] **Field Kit** — Devices tab lists real connected USB/serial
      devices; Scripts tab runs a trivial script and Stop actually
      kills it (process-group kill, not just the shell); Security tab's
      4 pure-Python tools (hash ID, password strength, subnet calc,
      port scan) all return real results.
- [ ] **Workshop & Electronics** — component CRUD.
- [ ] **Navigation** — add a waypoint, compute distance/bearing between
      two, sun/moon data for today.
- [ ] **Knowledge** (Reference Library) — install a `.zim` pack (if one
      exists), search within it, confirm it's indexed by Ctrl+K.
- [ ] **Files** — browse, create/rename/delete (typed-confirmation
      dialog, no trash).
- [ ] **Diagnostics** — System Health panel updates live; log viewer
      shows real recent log lines with working level/text filters.
- [ ] **Dashboard** (the module, not Home) — recent activity/missions/
      memories/events/projects/tasks all populated correctly.
- [ ] **Music** — confirmed placeholder, `QtMultimedia` import blocked
      in this sandbox; **[verify on Pi]** only.

## 6. Settings & cross-cutting

- [ ] All 4 themes (Dark Field / Low Energy / Colored / Anime
      Monochrome) apply live with no restart; open a fresh dialog after
      switching and confirm it reflects the new theme (a prior real bug
      class — stale per-widget stylesheets).
- [ ] Device Profile toggle (Core/Home) changes and persists.
- [ ] Backup Now → produces a file; Restore from Backup → round-trips
      correctly (test on a throwaway copy of `data/`, restore is
      destructive).
- [ ] Voice dropdown (see section 4).

## 7. Companion/proactive behaviors

These fire at most once per real calendar day — testing them same-day
twice won't re-trigger; check `config.json`'s
`system.last_*_date`/`last_checkin_date` keys if you need to force a
re-check.

- [ ] Set the active profile's birthday to today (`set_birthday` via
      chat) → triggers a birthday notification on the next daily-check
      tick (every 5 min while the app runs).
- [ ] Add a Calendar event for today → same-day digest notification.
- [ ] No conversation activity + past 6pm local time → check-in
      notification; confirm it does **not** fire before 6pm or on a day
      with real chat activity already.

## 8. Explicitly hardware-gated — do not expect these to work here

Confirmed blocked in this dev sandbox specifically (see
`docs/KNOWN_ISSUES.md` for the full list and root causes) — re-test
once real Pi 5 + AI HAT+2 hardware exists, not before:

- Real speaker output (Piper synthesis itself is verified; the last
  "sound from a speaker" step is not)
- Real mic input (STT round-trip is verified against pre-recorded WAV,
  not a live mic)
- `amixer`-based volume control
- AI HAT+2 NPU inference path (Ollama currently targets generic CPU/GPU
  HTTP only — genuinely unresolved whether it can drive the Hailo NPU
  at all)
- Wi-Fi analyzer / active security tooling (`nmap`/`hashcat`/`scapy`/
  `aircrack-ng` all absent, need root)
- GPS, camera/species-ID, any Modular Backpack hardware — not yet
  chosen/acquired at all
