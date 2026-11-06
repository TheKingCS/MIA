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

### Using MIA (whenever)
- [ ] **Write your first Operating Journal lines** by talking to her ("add to my operating journal: work out 4 times
      a week"), then ask "am I living how I said I want to?".
- [ ] **Try Good News Radio:** "what's the good news?", "good news, the late night one", or play "Good News Radio,
      Sunny, Nov 6". Say "that story was misleading" when one is.
- [ ] Log a game: "played pickleball for an hour, it was hard".
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

- [ ] The phone build bundles Chaquopy's `cryptography` 42.0.8, which the dependency audit doesn't cover yet.
- [ ] Flaky, seen once each: `tests/test_reference_library_manager.py::test_search_all_packs_returns_snippet_from_matching_pack`,
      and one native Qt crash mid-suite.
- [ ] Records some loops wait on: when the phone last reached the PC (`phone.link`), turns traced by surface
      (`glasses.voice`), photo-transfer failures (`vault.coverage`), the screen maker's retries (`creations.maker`).
- [ ] Step 4 leftovers: edits on the desktop's Qt screens, Plaid re-categorizations (after Zac's Plaid work), OCR
      field corrections, the Loop's predictions.
- [ ] Step 8: more cross-domain plans (the benchmark's G questions); calibration against outcomes.
- [ ] The Chronicle's yearly edition, from the kept seasons (step 17).
