# Waiting On

*The running list of what Zac and the other agents need to do (Zac, 2026-11-06: "keep a running track of what other
agents or I need to do and I will address those later"). Claude adds to it as work needs someone, and strikes an
item when it's done. Newest first within each person. Read with `docs/NEXT_SESSION.md`.*

*Last updated: 2026-11-06*

## Zac

### Decisions
- [ ] **The education ladder** (H-0080 / H-0084): approve, amend or reject **DEC-0102**; pick MIA's **second
      language**; pick the **first two tracks** (Claude suggests Applied Money, then Psychology).
- [ ] **The savings hound** (muse's couponing proposal / H-0085): approve it or not; groceries and household only
      to start (Claude: yes); household needs inside the grocery list (Claude: yes); **are you fine scanning
      receipts into the Inbox** as the price source?
- [ ] **The rest of the Interconnection Architecture doc** (it arrived cut off after "## 3. Five Layers"): paste it,
      so build plan step 7, the module contract, follows your layers.
- [ ] **Glasses:** the five questions in `docs/GLASSES_NAVIGATION_PLAN.md`; whether the glasses' question buttons
      should be read-only (an email question brings stranger-written text into a turn that can change things).

- [ ] **The Chronicles:** 124 candidate events wait for your yes or no (the dev window's Chronicles panel); the
      weekly issue can only tell approved ones. And how the Creator looks in the comic (DEC-0087: "waiting for
      Zac" in `docs/chronicles/characters/creator.md`). Then approve each issue: `python -m tools.chronicle_issue
      show I-0001`, `... approve I-0001`.

### At the PC
- [ ] **Restart MIA** so she loads `cryptography` 50.0.2 (47 had three HIGH advisories, T-0048).
- [ ] **Start the standing mission** when you want the council working the loops' tasks:
      `python -m tools.work mission start M-0001`.
- [ ] **Sign the reviewers in:** `codex login` (the second reviewer), `gh auth login`, Copilot's `/login`.
- [ ] **Approve or reject** what's waiting: Night School keeps real exercises she passes in `python -m tools.lab
      list` (`python -m tools.lab approve <id>`).
- [ ] **Plaid:** finish the work in progress in `core/budget_manager.py` and `core/plaid_manager.py` (its test,
      `test_import_transaction_transfer_is_skipped`, fails until then), and link every card and bank.
- [ ] **The phone:** install build 143 or newer (`adb install -r`), then reopen MIA on the glasses.
- [ ] Pick the council's voices; try Make Something; try Council Mode on the glasses.

- [ ] **Maps and comms** (`docs/MAPS_AND_COMMS.md` section 4): for mesh messaging without cell service, buy two
      or more Meshtastic LoRa radios (US 915 MHz; one stays on the PC); say whether to install ATAK-CIV on
      the phone; name the first places to map (the property's corners, the well, trailheads).

### Using MIA (whenever)
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
      next free number is **H-0086**.
- [ ] **Screens waiting on your look** (the engine and actions are built; Claude can build working screens on the
      shared frame once you've set the look): the Operating Journal, Recreation (games played and training load),
      Good News Radio, the Night School panel and the education transcript (if DEC-0102 is approved).

## ChatGPT (Chat)

- [ ] **Vision checks** muse asked for: the education ladder (H-0080: which measures matter, which are vanity), and
      the savings hound (where's the noise line for deal findings).

## Claude (for a later session)

- [ ] **Sight on the glasses and the phone**: a Look button (camera, then the question by voice) that sends the
      photo to `POST /api/sight` (built, `core/sight.py`); then a phone build for Zac to install.
- [ ] The phone build bundles Chaquopy's `cryptography` 42.0.8, which the dependency audit doesn't cover yet.
- [ ] Flaky, seen once each: `tests/test_reference_library_manager.py::test_search_all_packs_returns_snippet_from_matching_pack`,
      and one native Qt crash mid-suite.
- [ ] Records some loops wait on: when the phone last reached the PC (`phone.link`), turns traced by surface
      (`glasses.voice`), photo-transfer failures (`vault.coverage`), the screen maker's retries (`creations.maker`).
- [ ] Step 4 leftovers: edits on the desktop's Qt screens, Plaid re-categorizations (after Zac's Plaid work), OCR
      field corrections, the Loop's predictions.
- [ ] Step 8: more cross-domain plans (the benchmark's G questions); calibration against outcomes.
- [ ] The Chronicle's yearly edition, from the kept seasons (step 17).
- [ ] The Chronicles' panels: a bigger image model and characters that stay the same across panels (T-0036).
