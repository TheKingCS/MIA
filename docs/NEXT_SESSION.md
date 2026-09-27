# Next Session: Where We Left Off

The running to-do list between Claude sessions. Claude's cloud sessions
start from a fresh copy of this repo with no memory of past chats, so
**anything not written here is forgotten.** Start a session with "read
docs/NEXT_SESSION.md". Update it at the end of each session.

*Last updated: 2026-09-27*

---

## 1. Your hands-on steps (need your computer, not Claude)

- [ ] **Plaid sandbox test.** Follow `docs/PLAID_SETUP.md` Parts 1–5
      and report back. Then Part 6: Reset → Production → connect real
      accounts.
- [ ] **Phone voice first run.** Follow `docs/PHONE_VOICE_SETUP.md`
      (Tailscale, `server.enabled`, add to Home Screen) and try it on
      the drive home. Report: did it hear you over road noise, how long
      answers took, anything confusing.
- [ ] **Claude Design pass.** Upload `docs/design_handoff/` (or the zip
      Claude sent) plus your inspiration pictures to Claude Design and
      paste the prompt at the top of its README. Bring the 3 directions
      back here; Claude builds the one you pick as a new MIA theme.

## 2. Build queue (Claude), in order

1. **Fix whatever the Plaid and phone-voice tests turn up.** Both were
   built without being able to reach Plaid or a real phone.
2. **Phone voice, phase 2: a real phone app** so MIA keeps listening
   with the **screen locked** and in the background (web apps can't).
   Needs one decision first: **iPhone or Android?** iPhone apps need
   a Mac + Xcode, or a paid Apple developer account for anything beyond
   short test installs; Android can be built and installed directly.
   Also in this phase:
   - headphone-button push-to-talk
   - phone conversations saved to the desktop's History
   - desktop screens refreshing after phone-made changes
   - faster replies (stream the answer instead of waiting for the
     whole thing)
3. **Claude Design direction → new theme** (after you bring designs back).
4. **Finance, #2: homestead build and tool costs.** Wire your real
   tools and builds into the existing Workshop Materials/Jobs/Ledger
   pipeline.
5. **Finance, #3: mower business-use write-off.** A business-use-
   percentage engine for personal equipment used partly for contract
   lawn care.
6. **Finance, #4: money on your phone.** A read view of Budget, Debts
   and Net Worth in the phone app (it already has login and a secure
   connection).

## 3. Ideas parked for later (need their own planning pass)

- **MIA email inbox**: forward receipts, manuals and business
  documents; MIA classifies them and files them to the right place
  (e.g. the mower's manual and maintenance schedule onto the mower's
  page) and updates records from them. Open question: how an offline-
  first app receives email (IMAP polling vs. a forwarding address).
- **Textbook tutor**: add textbooks and course material and have MIA
  teach from them. Builds on the existing Reference Library, Classroom
  and the Assistant's retrieval.
- **Auto-tagging business transactions** (lawn care, rentals,
  homestead) to the right business entity after bank sync.

## 4. Known loose ends

- Cloud sessions have no auto-push git hook: Claude pushes manually
  after each commit (working as intended).
- `tests/run_module.py` can't open **Household** (it doesn't wire
  `recurring_missions`), so the design package has no Household
  screenshot.
- One test fails in Claude's cloud sandbox (UTC clock) and looks
  timezone-dependent:
  `tests/test_navigation_module.py::test_sun_moon_summary_for_real_coordinates_has_sensible_shape`.
  It predates this session and probably passes on your computer.
- Plaid: newer `loan`/`line_of_credit` liability types (personal/auto
  loans) aren't mapped to Debts yet. Card payments may show both as an
  expense and on the card; watch for double counting once real
  accounts sync.
- The Bank Sync tab's intro text about Fidelity needing a support
  ticket may be outdated under Plaid's Trial plan.
- Phone server: there's no Settings toggle yet; you turn it on by
  editing `config/config.json`.
