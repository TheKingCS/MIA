# Next Session: Where We Left Off

The running to-do list between Claude sessions. Claude's cloud sessions
start from a fresh copy of this repo with no memory of past chats, so
**anything not written here is forgotten.** Start a session with "read
docs/NEXT_SESSION.md". Update it at the end of each session.

*Last updated: 2026-10-07*

**Collaboration hub (2026-10-05):** the team shares memory through
`docs/COLLABORATION.md`, `CURRENT_STATE.md`, `DECISIONS.md`,
`QUESTIONS.md` and `HANDOFFS/`. Start there too.

**Engine Phase 1 (2026-10-05): approved and built.** Life events
(history), links (how things relate), Life State v2 and the read model
(`/api/state`, `python -m tools.export_state`, the published schema).
Details, acceptance results and the 10-question guardrail for new
proposals: `docs/ENGINE_PHASE1_PLAN.md` sections 8 and 9. For Muse (design): `docs/HANDOFFS/H-0003_claude-to-muse_where-mia-is.md`, with a placeholder sample state in `docs/schema/life_state.example.json`. Never put
real personal data (seed data) in the repo.

**Cognitive Extension:** you approved slices A → B → C → D → E
(`docs/COGNITIVE_EXTENSION_PROPOSAL.md`, "Decisions"). **Slice A
("Talk it out") is built:** conversation modes, journaling into an
encrypted Private Journal, off the record, and the safety floor. **Slices B ("Remember Why") and C
("Know when to speak") are built too.** D waits on your first real use
of the Android app.

---

## 1. Your hands-on steps

### From your phone, now (you're phone-only for the moment)

Everything here works from a phone: the GitHub app (or github.com) for
the hub, and the Meta AI app.

- [ ] **Read `docs/CURRENT_STATE.md`** in the GitHub app: where the
      whole team is.
- [x] Q-0015 answered and DEC-0019 approved (2026-10-07): MIA on the
      phone, the spike now, Android first, iPhone soon after.
- [ ] **Try MIA on your phone, no computer:** open
      `https://github.com/TheKingCS/MIA/releases/tag/phone-spike` on your
      Android, install **MIA-Phone-Test.apk** (it sits beside the companion
      app), open it, and tell Claude how long it took to start and how it
      feels. Done: under 8 seconds (2026-10-07).
- [ ] **Test MIA's own AI model on your phone (2026-10-07):** install the
      newest MIA-Phone-Test.apk, then gear → Settings → **Model test**.
      Download **Qwen 2.5 · 1.5B** on Wi-Fi, tap **Start**, then **Quick
      test**, keep MIA open, and send Claude a screenshot of the results.
      If you have time, do the same with **Qwen 2.5 · 3B**.
      (`docs/PHONE_MODEL_TEST.md`)
- [ ] **Make your account on the phone (2026-10-07):** install the newest
      **MIA-Phone-Test.apk** from the same page over the old one. It asks
      for your name, email, password, country and what MIA should help
      with, then shows a **recovery code once: write it down**. Your "You"
      becomes you, and you stay signed in until you log out. The gear
      (top right on Home) now opens your real **Profile** and **Settings**.
- [x] DEC-0014 and DEC-0016 approved; Q-0011 answered (Android, no
      glasses yet, MIA not on the PC yet); Q-0012 parked (2026-10-05).
- [ ] **The screens' photos (DEC-0018):** ask ChatGPT for the images in
      `docs/design/IMAGE_REQUESTS.md` (paste that file), then on github.com
      → TheKingCS/MIA → `web/img` → Add file → Upload files, with exactly
      the filenames listed. They can come one at a time.
- [ ] **Switch on the public preview (one setting):** on github.com
      (in the phone browser, "Desktop site" if the menu is missing) →
      TheKingCS/MIA → Settings → Pages → "Build and deployment" →
      Source: **GitHub Actions**. Then Actions → "Pages preview" → Run
      workflow (or wait for the next push). The preview is at
      https://thekingcs.github.io/MIA/ (placeholder data only).
- [ ] *(When the glasses arrive)* **In the Meta Wearables Developer Center:** check that Web Apps
      (and the Device Access Toolkit) are enabled for your account.
- [ ] **In the Meta AI app:** turn on Developer Mode (Settings › App
      Info › tap the version number 5 times). It's needed to load
      MIA's glasses app later.
- [ ] **See MIA install and pass on Windows without your PC:** github.com
      → TheKingCS/MIA → Actions → "Windows". Green means GitHub's Windows
      machines installed MIA and passed its tests.

### At the PC, when you're back (your Windows PC, DEC-0015)

### New on 2026-10-01: try these first (about 30 minutes)

Start with `git pull` in your MIA folder. Tell Claude anything that
looks wrong (the text on screen, never passwords or keys).

- [ ] **Run the installer.** Ubuntu: `bash install.sh` in the MIA folder.
      It skips what you already have, adds a "MIA" shortcut to the app
      menu and ends with a setup check. Check that the shortcut opens
      MIA. On a Windows PC, if you have one: double-click `install.bat`
      (it has never run on Windows: send Claude what it prints).
- [ ] **Your account.** Settings → Email, Recovery Code & Household →
      add your email and Save. If you have a password: "Make a new
      recovery code" and **write the code down** (it's shown once). No
      password yet: Settings → Change Password gives you one and the
      code. Your existing profiles are now one household: check that the
      calendar, budget and kitchen still show everything.
- [ ] **Sign in by email.** Switch User → "Sign in with email". On the
      phone and in the Android app, sign in with your email too.
- [ ] **A test account.** Switch User → New Profile, choose "Nobody"
      for sharing: check it sees an empty calendar and budget. Then
      Settings → Email, Recovery Code & Household → Delete my account
      (tick "erase") while signed in as the test account.
- [ ] **MIA's setup questions.** Settings → My Apps → "Ask Me the Setup
      Questions Again". Pick a focus, or "Show me everything".
- [ ] **Country.** Settings → Support & Safety → Your country (United
      States keeps everything as before).
- [ ] **Email drafts.** In People & Pets, give someone an email (use your
      own address for the test), or say "Pat's email is ...". Then say
      "write an email to Pat saying hi": a draft opens; try Copy and "Open in my mail app".
      Optional: Settings → Sending Email with a Gmail **app password**
      (never paste it into a chat), then press Send. On the phone, the
      Android app's "Email drafts".
- [ ] **Imports.** Settings → Import from Another App: a calendar export
      (Google Calendar → Settings → Import & export → Export, unzip the
      .ics), your phone's contacts (.vcf), or a bank's "download
      transactions" .csv. Check the categories the bank import guessed
      in Budget. Say "undo that" if an import isn't what you wanted.
- [ ] **Undo and why.** Ask MIA to add something ("add milk to the
      grocery list"), then "undo that". When MIA messages you on her own,
      ask "why did you tell me that?".
- [ ] **Check My Setup.** Settings → Check My Setup (or ask "is
      everything set up?"); fix or report anything marked ❌.
- [ ] **Today.** Look at the new Today card on Home (under the
      greeting); tap a row to jump to its app. On the phone, the Today
      tab. Ask "what's on today?". Tell Claude if something you'd expect
      is missing.
- [ ] **Quick capture.** Click the "✚" in the header (or Ctrl+Shift+Space)
      and try a few: "milk and eggs", "changed the truck's oil today",
      "dentist Tuesday at 2", "idea: rain barrel by the shed". Each says
      where it went (Undo is right there); anything MIA can't place
      becomes a note tagged "capture". Tell Claude what landed wrong.
- [ ] **Private budget (optional).** Budget shows whose budget it is.
      Only if you want your own money separate from the household's:
      "Keep my money private...". Switching back keeps it for later.
- [ ] **Whose is it.** In Maintenance, edit the truck (or anything) →
      "Belongs to". Or tell MIA "the truck is mine". Things marked as
      someone else's drop off your Today list.
- [ ] **Accessibility.** Settings → Accessibility: try a bigger text
      size and high contrast (switch back after). Press Ctrl+Shift+R on
      any screen to hear it (needs MIA's voice installed). Tell Claude
      anything that's still hard to read.
- [ ] **Child accounts (only if a child will use MIA).** Add User →
      tick "This is a child's account", pick your household and type
      your password to approve. Sign in as them: only kid-friendly apps
      show, money and admin apps say "ask a parent", Settings has just
      text size and contrast. Your Account window (Settings → Email,
      Recovery Code & Household) can reset their password or make it a
      regular account later.
- [ ] **Starter sets.** Settings → My Apps → "Add a Starter Set...":
      look through the six sets and add any that fit (untick the parts
      that don't). Or tell MIA "set me up with the homestead starter
      set". Tell Claude what's missing or doesn't belong.
- [ ] **Your real life, entered through MIA (Engine Phase 1).** Put in
      your properties, loans, bills, income, vehicles and people the way
      any user would (or tell MIA). Tell MIA how things connect: "the
      land loan funds the lot", "the greenhouse depends on selling the
      lot". Then run `python -m tools.export_state --out me.state.json`
      in the MIA folder and look it over (it stays on your computer;
      never paste it anywhere public). Ask MIA "what did I get done this
      week?" and "what depends on selling the lot?".
- [ ] **Check the new front end on your new computer and phone (Phase 2).**
      On the new computer, in the MIA folder: `git pull`, then
      `python -m tools.web_check`. It opens MIA's new web Home in the
      built-in browser and prints one line (load time, memory,
      smoothness) and PASS or CHECK. Paste that line into the hub
      (`docs/CURRENT_STATE.md` under Recent changes) or send it to
      Claude. Then open MIA → Apps → "Home (preview)" and try "Done" on
      something that's due. On the phone (with phone access on), open
      the phone address plus `/web/` to see the same Home. Also answer
      Q-0010: what OS and hardware the new computer has.
- [ ] **Export your data** once, to see what's in it (Settings → Email,
      Recovery Code & Household → Export my data).

### Still waiting from before

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
      4. Settings → **Phone Access** → tick **Let my phone reach MIA**
         (its checklist shows what's left).
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
- [ ] **Try the textbook tutor and the document inbox**
      (`docs/SETUP_GUIDE.md`, Part 10): add a textbook and study from
      it; send the mower's manual and a receipt to the inbox and file
      them. Install `tesseract-ocr` (Part 1a) and try a photo of a
      paper receipt, and Share → **MIA inbox** from the Android app.
      Tell Claude how well real receipts read (which digits it gets
      wrong, if any). Email intake is optional (a separate Gmail address with an
      app password; never paste the app password into a chat).
- [ ] **Claude Design pass.** Upload `docs/design_handoff/` (or the zip
      Claude sent) plus your inspiration pictures to Claude Design and
      paste the prompt at the top of its README. Bring the 3 directions
      back here; Claude builds the one you pick as a new MIA theme.

## 2. Build queue (Claude), in order

**The phone spike passed (2026-10-07, `docs/PHONE_SPIKE.md`)**, and Zac
has it on his phone (first start under 8 s). His feedback is fixed:
account menu, no Apps tile, every card the phone's width, Garage spacing.

**Next, in order (`docs/design/CONCEPT_AUDIT.md`'s build list):**
1. Onboarding (create your account on first start), Profile and Settings
   pages. This is Phase 2's first step.
2. Photos of things (assets, recipes, properties).
3. Skills and Missions like the concept.
4. The Real Estate detail panel.
5. Strip icons.
6. Weather (needs Zac's OK).
7. The net-worth trend.

Then the rest of Phase 2 (`docs/PHONE_FIRST_PLAN.md`): Android notifications, speech and battery, background checks, backup, an on-phone model for Talk, faster starts. Keep the iPhone path open.

**Now (2026-10-06, DEC-0017, approved): the web becomes all of MIA.**
Track it in `docs/WEB_PARITY.md`. Done: the shared frame (`web/shell.js`)
the Dashboard (`core/web_surfaces.py`, `/api/shell`,
`/api/dashboard`), the Apps page (`/api/apps`), Home as MIA herself
(Muse's orb + chat) and the ⋯ menu. Next, each one a full engine API (every read and every
add/edit/delete/complete as an action kind in `core/actions.py`) plus a
working screen on the frame, for Muse to restyle:
1. ~~Money~~ **done 2026-10-06** (`web/money.html`; bank connect/sync
   stays on the PC: it needs the vault passphrase).
2. ~~Garage + Maintenance~~ **done 2026-10-06** (plus Property,
   Greenhouse and the asset page; still to do: sensor graphs, parts per asset).
3. ~~Missions, Skills, Character~~ **done 2026-10-06** (closes H-0013;
   still to do: drawn prerequisite lines in the skill tree, character art).
4. ~~Kitchen, Workout, Real Estate~~ **done 2026-10-06** (Zac asked for
   them next; still to do: recipe ratings and photos, rest timer and
   guided sessions, depreciation and selling a property).
5. Photo fields for assets, recipes and properties (Q-0014, Muse said yes),
   stored in each person's data folder, never `web/img/` (that's the public repo).
6. Calendar, Notes, Inbox, full Assistant chat; then the rest of the 59 rows.
Ctrl+K search on the web is also still missing (Shell row).

**Direction (2026-10-01):** keep perfecting MIA for personal use, but
built for any person or household, not just you. The youth/school
initiative is parked (`docs/future/MIA_YOUTH_INITIATIVE.md`). Then
(2026-10-01) you asked to approach MIA as if hundreds of people may use
it, and went with Claude's recommendations. The plan, in order:

- **Stage 1, accounts and households: built** (ROADMAP "People and
  ownership", steps 1 and 2). Email sign-in with a recovery code,
  each account its own household, joining with a member's password,
  per-person settings, notifications, workouts and Classroom.
- **Stage 2, MIA asks and each person's Apps screen: built** (ROADMAP
  step 3). New accounts get MIA's setup questions; focuses (Personal,
  Home & Family, Homestead, Business, Student) order and tuck away apps
  per person without blocking any. Settings → My Apps; Modules → Hide
  from my Apps; or ask MIA ("switch me to student mode").
- **Stage 3, email drafts: built** (ROADMAP step 4). "Write an email to
  pat@example.com about the faucet": a draft window with Send (only when
  you press it), Copy, or your mail app; a card on the phone's web app.
  Sending is optional and per person (Settings → Sending Email; your own
  address, not the inbox mailbox). Follow-ups **built** (2026-10-01): the
  Android app's "Email drafts" (Send, Copy, Mail app, Discard), and
  addressing by name (People & Pets has an email field; household members
  by their sign-in email; "Pat's email is ..." remembers it).
- **Stage 4, country-aware crisis lines and currency: built** (ROADMAP
  step 5). US, Canada, UK, Ireland, Australia, New Zealand; elsewhere
  general advice and findahelpline.com. Settings → Support & Safety.
- **Stage 5, your data and undo: built** (ROADMAP step 6). Export and
  delete your account, "undo that", "why did you tell me that?", "stop
  telling me about ...", and Settings → Check My Setup. The accounts plan
  is complete.
- **MIA's installer: built** (ROADMAP step 7): `bash install.sh` on
  Linux/Pi (`--kiosk` for a Pi), double-click `install.bat` on Windows.
- **Imports: built** (2026-10-01): Settings → Import from Another App
  (.ics calendars, .vcf contacts, bank .csv statements).
- **Today: built** (2026-10-01): a Today card on Home, a Today tab on
  the phone, "what's on today?".
- **Quick capture: built** (2026-10-01): the "✚" in the header or
  Ctrl+Shift+Space.
- **Private budget: built** (2026-10-01): Budget → "Keep my money
  private...".
- **Ownership marks: built** (2026-10-01): "Belongs to" on vehicles,
  tools and appliances; "the truck is mine", "whose mower is it?".
- **Accessibility: built** (2026-10-01): Settings → Accessibility (text
  size, high contrast), Ctrl+Shift+R reads the screen aloud.
- **Child accounts: built** (2026-10-01): Add User → "This is a
  child's account"; kid-friendly apps only, no money or admin tools,
  the Assistant speaks simply, the safety reply also asks them to tell
  an adult. A child's journal stays private to them.
- **Open question for the owner:** should MIA also tell a child's
  parent when the safety floor triggers for the child? Today it does
  not (it tells the child to talk to an adult right away). Decide and
  tell Claude.
- **Starter sets: built** (2026-10-01): Home & Family, Homestead,
  Student, Personal, Business, Fitness; offered at the end of the setup
  questions, in Settings → My Apps, and by asking MIA.
- **Next in this line:** a real Habits module.


1. **Fix whatever the Plaid and phone-voice tests turn up.** Both were
   built without being able to reach Plaid or a real phone.
2. **Phone voice, phase 2, the rest.** Built (2026-09-28): phone
   conversations in the desktop's History, desktop screens refreshing
   after phone-made changes, and per-turn timings ("heard 1.2s ·
   thought 3.4s · spoke 0.8s"). **Left: faster replies**, waiting on your
   timings from a real drive: the slow stage decides the fix (streaming
   the model's words, speaking the first sentence early, or a faster
   speech-to-text model). Plus whatever your first real use turns up.
   Also built today: **sorting bank charges to your businesses** (Budget →
   Bank Sync → Review Business Tags; set up your businesses under Summary
   → Manage Entities first).
3. ~~Cognitive Extension, slice B: "Remember Why"~~ **built**
   (2026-09-27). Try it: Part 6 of `docs/SETUP_GUIDE.md`. Both follow-ups
   are **built** (2026-09-28): MIA asks which kind of support you want
   when you sound worn down (and learns your usual answer), and "remind
   me why" works on the headless Core voice loop too.
4. ~~Cognitive Extension, slice C: "Know when to speak"~~ **built**
   (2026-09-27): one gate for every unprompted message, 5/day, no quiet
   hours. The opt-in weekly journal reflection is **built** (Settings →
   When MIA Speaks Up), and so are offline/back-online notices with "remind
   me when we're back online" (2026-09-28). "Learning from being ignored"
   is **built** too: 3 of the last 4 of a kind dismissed → a 2-week break
   from that kind (Settings or "you can tell me about ... again" ends it).
   Slice C is complete.
5. **Fix what the live conversation check turns up** (now 215 cases,
   including Workout, People & Pets, Household, Classroom, and 7
   personal-mode cases). ("Propose, you confirm" updates from things
   mentioned in passing are **built**, 2026-09-28: try "the mower got a
   new battery today, $120" and answer "yes".)
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
   (Budget → Builds & Tools). Follow-ups **built** (2026-09-28): the
   Business Report's "Equipment business use" section, and vehicles in
   miles with the standard mileage figure (enter each year's IRS rate
   in the worksheet).
10. ~~Finance, #4: money on your phone~~ **built** (2026-09-28):
   `/api/finance/summary`, a Money tab in the web app, Show money in the
   Android app. Read-only by design. Your finance sequence (debts →
   builds and tools → business use → phone) is complete.
11. ~~Textbook tutor and document inbox~~ **built** (2026-09-28). Try
   them: Part 10 of `docs/SETUP_GUIDE.md`. Follow-ups, roughly in order:
   - ~~reading photos and scans~~ and ~~"Share to MIA" on Android~~
     **built** (2026-09-28): Tesseract OCR in the background (install
     `tesseract-ocr`, Part 1a), Share → MIA inbox in the Android app;
   - the model's help on messy manuals (propose extra schedule steps,
     still confirmed by you), and updating an item's details (model,
     serial, warranty end) from its documents;
   - meaning-based search for textbooks (embeddings), so "why do
     breakers trip" finds a passage that never uses those words;
   - ~~a receipt's line items~~ **built** (2026-09-28): kept on the
     expense; "what did I buy for the greenhouse?". Later: splitting one
     receipt across two builds.

## 3. Ideas parked for later (need their own planning pass)


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
- Accounts: the inbox's email mailbox, the field kit's expedition sync,
  backups and reports still read the device's first household (the main
  `data/` folder). Deleting a profile doesn't tidy an emptied household.
- Plaid: auto/personal loans and lines of credit now become Debts too
  (2026-09-28), but the bank doesn't report their rate or minimum: fill
  those in on the Debts tab. Card payments may show both as an expense
  and on the card; watch for double counting once real accounts sync.
- The Bank Sync tab's intro text about Fidelity needing a support
  ticket may be outdated under Plaid's Trial plan.
