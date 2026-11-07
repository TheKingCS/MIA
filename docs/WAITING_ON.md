# Waiting On

*The running list of what Zac and the other agents need to do (Zac, 2026-11-06: "keep a running track of what other
agents or I need to do and I will address those later"). Claude adds to it as work needs someone, and strikes an
item when it's done. Newest first within each person. Read with `docs/NEXT_SESSION.md`.*

*Last updated: 2026-11-07*

## Zac

### Decisions
- [ ] **The phone's old security packages (T-0051)**: keep them with the exposure written down, build newer ones,
      or move the phone's encryption to Android Keystore over time (Claude: keep now, Keystore over time). Details
      under Claude below.
- [ ] **The education ladder** (H-0080 / H-0084): approve, amend or reject **DEC-0102**; pick MIA's **second
      language**; pick the **first two tracks** (Claude suggests Applied Money, then Psychology).
- [ ] **The savings hound**, now **DEC-0103 (PROPOSED)** (H-0086: Muse took the receipts-first correction): approve,
      amend or reject it; groceries and household only
      to start (Claude: yes); household needs inside the grocery list (Claude: yes); **are you fine scanning
      receipts into the Inbox** as the price source?
- [ ] **The rest of the Interconnection Architecture doc** (it arrived cut off after "## 3. Five Layers"): paste it,
      so build plan step 7, the module contract, follows your layers.
- [ ] **Glasses:** the five questions in `docs/GLASSES_NAVIGATION_PLAN.md`; whether the glasses' question buttons
      should be read-only (an email question brings stranger-written text into a turn that can change things).

- [ ] **The Chronicles:** 124 candidate events wait for your yes or no (the dev window's Chronicles panel); the
      weekly issue can only tell approved ones. And how the Creator looks in the comic (DEC-0087: "waiting for
      Zac" in `docs/chronicles/characters/creator.md`). Then approve each issue: `python -m tools.chronicle_issue
      show I-0001`, `... approve I-0001`. The panels are drawn by SDXL-Turbo now (samples in
      `C:\Users\zacrh\DevTools\imagegen\out\sdxl_*.png`): to give the series one look, save the picture you like as
      `C:\Users\zacrh\DevTools\imagegen\series_reference.png`.

### At the PC
- [ ] **Cut your area's vector map** (built 2026-11-06 with your OK): `.venv\Scripts\python -m tools.offline_map
      cut home --around-waypoints 10` (every waypoint, 10 km around; or `--bbox west,south,east,north`). It
      tells Protomaps' map server which area, nothing else; a few MB per town. Then Maps on the web opens on it.
- [ ] **Night School's start time:** it's set for 01:30, but you work nights and sleep in the morning. Set
      `"start"` in `work/night_school.json` to when you're usually asleep (say `"09:30"`); it runs four hours
      from then. (On 2026-11-07 Claude started one by hand at 08:55, while you slept.)
- [ ] **Restart MIA** so she loads `cryptography` 50.0.2 (47 had three HIGH advisories, T-0048) and everything
      built 2026-11-06: Night School's second try, promises and notes (Kept), photo search, the new web pages
      (Diagnostics, Knowledge, Classroom, Household, Navigation, Observations, Memories, Maps with vector
      areas and tap-to-add waypoints), near-duplicate photos offered like bursts, and the new loops; and
      (2026-11-07) her own router running in the shadow on each turn, and her answers about herself coming from
      her code and the Knowledge Vault too.
- [ ] **Start the standing mission** when you want the council working the loops' tasks:
      `python -m tools.work mission start M-0001`.
- [ ] **Sign the reviewers in:** `codex login` (the second reviewer), `gh auth login`, Copilot's `/login`.
- [ ] **Approve or reject** what's waiting: Night School keeps real exercises she passes in `python -m tools.lab
      list` (`python -m tools.lab approve <id>`). One is there now: the night of 2026-11-06's
      phone_link lesson, `20261106-e2a5be` (a bad record no longer breaks the phone link).
- [ ] **Her specialists' notes (DEC-0109):** read and confirm (or withdraw) what they write, so MIA can say a person checked it.
      `.venv\Scripts\python -m tools.specialists show radio` lists the notes with their ids; then `... confirm radio <id>`
      or `... withdraw radio <id> "why"`. The radio specialist has three now. Want another specialist (finance, health,
      cooking...)? Say so.
- [ ] **Her own models (DEC-0106):** nothing to do now. When you're curious: `.venv\Scripts\python -m tools.model_forge
      list` shows each model she has made and how it scored; `... router` retrains the tool router (about half a
      minute). A model only goes into use with your yes, and Claude will ask when one has earned it.
- [ ] **Later, for fine-tuning (DEC-0106 stage 3):** training a local model on the 7900 XTX needs ROCm and PyTorch,
      which work best on Linux (`docs/HARDWARE.md` recommends Ubuntu). When we get there: whether to dual-boot
      Ubuntu on the PC, or try ROCm on Windows (more limited). Not needed until her corpus is big enough.
- [ ] **Plaid:** finish the work in progress in `core/budget_manager.py` and `core/plaid_manager.py` (its test,
      `test_import_transaction_transfer_is_skipped`, fails until then), and link every card and bank. Before
      committing it, run `.venv\Scripts\python -m tools.docs stale` (DEC-0110): `add_expense` and `add_income`
      gained a `kind` parameter, and their docstrings (and a dozen others there) haven't said so yet.
- [ ] **The phone:** install build 143 or newer (`adb install -r`), then reopen MIA on the glasses. The CI build
      from 2026-11-06's push or later also lets Look take or choose a photo on the phone (and the Inbox choose a
      file): try both.
- [ ] Pick the council's voices; try Make Something; try Council Mode on the glasses.

- [ ] **Maps and comms** (`docs/MAPS_AND_COMMS.md` section 4): for mesh messaging without cell service, buy two
      or more Meshtastic LoRa radios (US 915 MHz; one stays on the PC); say whether to install ATAK-CIV on
      the phone; name the first places to map (the property's corners, the well, trailheads).

### Using MIA (whenever)
- [ ] **Try the new web pages** (after the restart, in the sidebar): Kept, Classroom, Household, Navigation, Maps,
      Observations, Memories, Knowledge (copy Kiwix `.zim` packs into `reference_library\` first: her specialists also cite them
      when they study, DEC-0109), and
      Diagnostics (yours only). Each is working but plain: Muse does the look. Tell Claude what's wrong or missing.
- [ ] **Maps:** once your area is cut (above), open Maps, tap where something is (the well, a gate, a trailhead)
      and name it; it's a waypoint everywhere (Navigation, the glasses, the TAK export).
- [ ] **Promises and decisions** (DEC-0054, built 2026-11-06): tell her "I promised Sam I'd fix his gate by
      Saturday" and say "keep it" when she offers; she mentions it the day before. "What did I promise?", the Kept
      page in the sidebar, "I kept my promise to Sam".
- [ ] **Find a photo by what's in it**: once the vault has photos on the PC, she describes them at night; then
      "find my photos of the creek".
- [ ] **The council from your phone**: after MIA restarts on the PC, "The Council" is in your sidebar (yours only).
      Write to them there; @claude or @codex asks one member.
- [ ] **Write your first Operating Journal lines** by talking to her ("add to my operating journal: work out 4 times
      a week"), then ask "am I living how I said I want to?".
- [ ] **Try Good News Radio:** "what's the good news?", "good news, the late night one", or play "Good News Radio,
      Sunny, Nov 6". Say "that story was misleading" when one is.
- [ ] Log a game: "played pickleball for an hour, it was hard".
- [ ] A vision model is installed for sight (`ollama pull qwen2.5vl:7b`, about 6 GB; `ollama rm qwen2.5vl:7b` takes
      it back off). Nothing to do unless you'd rather not keep it.
- [ ] Add a place by grid ("add a waypoint called Spring at 18S UJ 23478 06483") and open
      `python -m tools.tak_export`'s `MIA_places.zip` in ATAK-CIV.
- [ ] **Later:** when the dev window's Night School panel says the evidence supports it, let her choose her own
      lessons (`"mode": "self"` in `work/night_school.json`).

## Muse

- [ ] **Handoff numbers:** H-0080 and H-0081 were each used twice (`H-0080_chatgpt-...`, `H-0081_chatgpt-...`). The
      next free number is **H-0087** (H-0086 is Muse's savings-hound reply).
- [ ] **Screens waiting on your look**: working screens are built on the shared frame (2026-11-07), formatting
      only: `web/operating.html` (the Operating Journal), `web/play.html` (games and training load), `web/news.html`
      (Good News Radio), `web/council.html` (owner only), and 2026-11-06 `web/kept.html` (promises, decisions,
      ideas and goals set aside, DEC-0054; its demo shows sample notes). Still engine-only: the Night School panel's
      look, and the education transcript (if DEC-0102 is approved).

## ChatGPT (Chat)

- [ ] **Vision checks** muse asked for: the education ladder (H-0080: which measures matter, which are vanity), and
      the savings hound (where's the noise line for deal findings).

## Claude (for a later session)

- [ ] **Sight on the glasses and the phone**: a Look button (camera, then the question by voice) that sends the
      photo to `POST /api/sight` (built, `core/sight.py`); then a phone build for Zac to install. 2026-11-06: the
      phone's web view now answers a page's file input with Android's picker (`MainActivity.onShowFileChooser`; it
      builds, not yet tried on the phone), so Look's "choose a photo" works there, and "take a photo" opens the
      camera, which writes into MIA's own cache (never the gallery; cleared at the next look). The glasses' own
      camera and asking the question by voice are still to do.
- [ ] **T-0051, security (phone):** the audit covers the phone's own packages now (`phone.vulnerable`, weekly):
      `cryptography` 42.0.8 (11 advisories), `starlette` 0.27.0 (14), `fastapi` 0.99.1 (1). They're pinned by
      the phone's `pydantic<2`; its server listens on 127.0.0.1 only. Chaquopy has no newer `cryptography` for
      Android and no `pydantic-core`, so there's no simple upgrade. **Zac: choose** (a) keep them, the exposure
      written down (only apps on the phone can reach its server), (b) build `cryptography` for Android ourselves,
      or (c) move the phone's encryption to Android Keystore (Kotlin) and its server off fastapi over time.
      Claude: (a) now, (c) over time. Details in `work/tasks/T-0051.md`.
- [ ] Flaky: `tests/test_reference_library_manager.py`: two causes found and fixed (an open libzim handle on delete;
      and, 2026-11-06, a freshly written file's timestamp reading a few ms ahead of `time.time()` on Windows, 1 file
      in 10, so a pack looked "still copying"); and the native crash mid-suite (no summary printed), which has a
      **likely trigger** (2026-11-06; it crashed 5 runs in a row, then passed 3 with the same trigger): one more test in `tests/test_server_app.py` that creates a second profile
      and logs it in (any route after) makes the full suite die later with "Fatal Python error: Aborted" / an
      access violation inside anyio's event loop, at `tests/test_user_sync.py::test_through_the_server`; never in
      a subset. Signing in alone didn't trigger it; a request as that person afterwards (`/api/diagnostics` or
      `/api/council`, both a 403) did, so look at what building a person's view on a worker thread leaves behind
      (not a Qt object: no store is one; not the reference library: it isn't per person).
      Worked around by checking the 403 inside the council test, which already signs a second person in.
      Later the same day: 8 clean runs with the trigger, uncaptured and with RAM nearly full (the 14B and the
      vision model both loaded), so it's neither the trigger alone nor memory; it couldn't be reproduced. The
      lab now reruns a suite that ended without pytest's summary, once, and says so, so a lesson, a merge or
      dev.suite is never judged on a crash;
      `tests/test_inbox.py::test_what_she_read_and_the_person_corrected_is_noted` failed once in a full run (2026-11-06),
      never alone.
- [ ] `vault.coverage` is built from the vault's own list (photos over a week old still only on the phone,
      2026-11-06); photo-transfer failures, which only the phone sees, could sharpen it in a phone build.
- [ ] Loop coverage (230 of 258): 3 to do, all after Zac's Plaid work (Plaid's two stores, business-use shares).
- [ ] Step 4's last leftover: Plaid re-categorizations (after Zac's Plaid work). Done: OCR field corrections
      (`inbox.reading`), the Loop's predictions (`loop.prediction`), and 2026-11-06 the desktop's Qt edits of recipes,
      meals, upkeep tasks and people (`corrections.screen_edit`); other Qt screens can join it the same way.
- [ ] Step 8: the routing audit answers 90 of 112 benchmark questions by a plan (2026-11-06); the 10 left to the
      model are research, how-to and one reframing question. Next: calibration against more outcomes than dates.
- [ ] The Chronicles' panels: characters that stay the same across panels (T-0036). The bigger model is in
      (2026-11-06): SDXL-Turbo, 0.7 s a panel; samples in `C:\Users\zacrh\DevTools\imagegen\out\sdxl_*.png`.
      **Zac:** to give a series one look, save the picture you like as
      `C:\Users\zacrh\DevTools\imagegen\series_reference.png`: every panel starts from it (palette and line
      work; see `out\consistency_sheet_90.png`).
