# Next Session: Where We Left Off

The running to-do list between Claude sessions. Claude's cloud sessions
start from a fresh copy of this repo with no memory of past chats, so
**anything not written here is forgotten.** Start a session with "read
docs/NEXT_SESSION.md". Update it at the end of each session.

*Last updated: 2026-09-27 (night)*

**Cognitive Extension:** you approved slices A → B → C → D → E
(`docs/COGNITIVE_EXTENSION_PROPOSAL.md`, "Decisions"). **Slice A
("Talk it out") is built:** conversation modes, journaling into an
encrypted Private Journal, off the record, and the safety floor. **Slices B ("Remember Why") and C
("Know when to speak") are built too.** D waits on your first real use
of the Android app.

---

## 1. Your hands-on steps (need your computer, not Claude)

**New computer? Start with `docs/SETUP_GUIDE.md`.** It walks through
every step below in order, from a blank machine, with Windows notes.

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
- [ ] **Live check of MIA's conversation skills** (see
      `docs/ASSISTANT_AUDIT.md`). With Ollama running:
      `python tests/live_model_check.py`. It uses fake data and never
      runs the tools it's testing. Send Claude the FAIL lines.
- [ ] **Try "Talk it out".** In MIA: Notes → 🔒 Private Journal →
      Set Up… and pick a passphrase (you can reuse your Plaid vault
      passphrase; if you forget it, the journal can't be read). Then
      in chat or on the phone: "I want to journal", talk, "I'm done
      journaling"; check the entry in the Private Journal tab. Also try
      "just listen", "no bullshit", "hype me up", "off the record".
      Optional: Settings → Support & Safety → a trusted person.
- [ ] **Install the Android app.** On your phone: GitHub → the MIA
      repo → Releases → "MIA Companion (Android)" → tap
      MIA-Companion.apk (full steps: `android/README.md`). Needs the
      phone voice setup at home done first. Tell Claude what works and
      what doesn't: locked-screen listening, the headset button, the
      Bluetooth mic option, signing back in after MIA restarts.
- [ ] **Claude Design pass.** Upload `docs/design_handoff/` (or the zip
      Claude sent) plus your inspiration pictures to Claude Design and
      paste the prompt at the top of its README. Bring the 3 directions
      back here; Claude builds the one you pick as a new MIA theme.

## 2. Build queue (Claude), in order

1. **Fix whatever the Plaid and phone-voice tests turn up.** Both were
   built without being able to reach Plaid or a real phone.
2. **Phone voice, phase 2, the rest** (the Android app itself is built,
   see `android/README.md`): phone conversations saved to the
   desktop's History, desktop screens refreshing after phone-made
   changes, and streaming replies so MIA starts talking sooner. Plus
   whatever your first real use of the app turns up.
3. ~~Cognitive Extension, slice B: "Remember Why"~~ **built**
   (2026-09-27). Try it: Part 6 of `docs/SETUP_GUIDE.md`. Follow-ups:
   MIA asking which kind of support you want when it's unclear, and
   Perspective on the headless Core voice loop.
4. ~~Cognitive Extension, slice C: "Know when to speak"~~ **built**
   (2026-09-27): one gate for every unprompted message, 5/day, no quiet
   hours. Follow-ups: the opt-in weekly journal reflection (delivered
   through the gate), and "learning from being ignored" (needs the
   notification bell to record dismissals).
5. **Fix what the live conversation check turns up** (now 215 cases,
   including Workout, People & Pets, Household, Classroom, and 7
   personal-mode cases). Then
   "propose, you confirm" record updates from things mentioned in
   passing (e.g. "the mower got a new battery" → offer to note it on
   the mower).
6. **Cognitive Extension, slice D: Contextual Presence** (after the
   Android app): Places, geofenced transitions sent from the phone,
   Welcome Home, "you're at Lowe's, want the materials list?". Then
   slice E, Life Runway.
7. **Claude Design direction → new theme** (after you bring designs back).
8. ~~Finance, #2: homestead build and tool costs~~ **built**
   (2026-09-28): expenses tagged to builds and tools, build budgets,
   tool cost of ownership and cost per hour, Budget → Builds & Tools,
   five Assistant tools. Try it: Part 7 of `docs/SETUP_GUIDE.md`.
9. ~~Finance, #3: mower business-use write-off~~ **built**
   (2026-09-28): business-use log, hour-meter totals, worksheet with PDF
   (Budget → Builds & Tools). Follow-up idea: an "Equipment business
   use" section in the Business Report, and the standard mileage rate
   option for vehicles.
10. **Finance, #4: money on your phone.** A read view of Budget, Debts
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
