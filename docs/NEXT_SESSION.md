# Next Session: Where We Left Off

The running to-do list between Claude sessions. Claude's cloud sessions
start from a fresh copy of this repo with no memory of past chats, so
**anything not written here is forgotten.** Start a session with "read
docs/NEXT_SESSION.md". Update it at the end of each session.

*Last updated: 2026-09-27 (evening)*

---

## 1. Your hands-on steps (need your computer, not Claude)

- [ ] **Plaid sandbox test** (full checklist: `docs/PLAID_SETUP.md`).
      1. On your main computer: `git pull`, activate `.venv`,
         `pip install -r requirements.txt`, `python main.py`.
      2. Plaid dashboard → Developers → Keys: copy your client_id and
         **Sandbox** secret. Never paste them into a chat.
      3. MIA → Budget → Bank Sync → Set Up Plaid: paste the keys, pick
         `sandbox`, and choose a vault passphrase (store it in a
         password manager; it can't be recovered).
      4. Connect a Bank → any bank → log in with `user_good` /
         `pass_good` (code `1234` if asked) → Sync Now.
      5. Check the Income, Expenses and Debts tabs, sync again, and
         confirm nothing is duplicated.
      6. Report back to Claude (the error text plus the last lines of
         `logs/`, never keys).
      7. Then Part 6: **Reset Plaid Setup** (clears the test data) → Set
         Up Plaid with your **Production** secret → connect your real
         banks (10 free connections; one bank login = one connection).
- [ ] **Phone voice first run** (full guide: `docs/PHONE_VOICE_SETUP.md`).
      1. Install Tailscale on the computer (`sudo tailscale up`) and on
         your Android phone, both on the same account.
      2. login.tailscale.com → DNS: turn on MagicDNS and **Enable
         HTTPS**.
      3. Give your MIA profile a password (Settings).
      4. In `config/config.json` set `"server": {"enabled": true,
         "host": "127.0.0.1", "port": 8765}`, then restart MIA.
      5. `sudo tailscale serve --bg http://127.0.0.1:8765`, then
         `tailscale serve status` to get your `https://…ts.net`
         address.
      6. On the phone: open that address in Chrome → log in → ⋮ → Add to
         Home screen → allow the microphone.
      7. Try it on the drive home (screen stays on, phone mounted).
         Report whether it heard you over road noise, how long answers
         took, and anything confusing.
- [ ] **Claude Design pass.** Upload `docs/design_handoff/` (or the zip
      Claude sent) plus your inspiration pictures to Claude Design and
      paste the prompt at the top of its README. Bring the 3 directions
      back here; Claude builds the one you pick as a new MIA theme.

## 2. Build queue (Claude), in order

1. **Fix whatever the Plaid and phone-voice tests turn up.** Both were
   built without being able to reach Plaid or a real phone.
2. **Phone voice, phase 2: a native Android app** (you have Android)
   so MIA keeps listening with the **screen locked** and in the
   background, which web apps can't do. Plan: a small Kotlin app with an
   Android foreground service (the kind that's allowed to keep the mic
   on, with a persistent notification), talking to the same
   `/api/voice/*` endpoints the web app already uses.
   - Build the installable APK with GitHub Actions, so you download it
     straight to your phone with no Android Studio needed; you'll allow
     "install unknown apps" once.
   - Headphone and Bluetooth button to start/stop talking.
   - Phone conversations saved to the desktop's History.
   - Desktop screens refresh after phone-made changes.
   - Faster replies (stream the answer instead of waiting for all of it).
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

- **Offline awareness follow-ups** (the base is built, 2026-09-27):
  a notification when MIA goes offline or comes back, and actually
  queuing "remind me when I'm back online" requests.

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
