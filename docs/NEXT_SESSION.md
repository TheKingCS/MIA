# Next Session: Where We Left Off

The running to-do list between Claude sessions. Claude's cloud sessions
start from a fresh copy of this repo with no memory of past chats, so
**anything not written here is forgotten.** Start a session with "read
docs/NEXT_SESSION.md". Update it at the end of each session.

*Last updated: 2026-11-07 (afternoon)*

**New 2026-11-07 (latest): Start Here, a grouped sidebar, the live browser, and the audit.** Start Here
(web/start.html, core/web_guide.py: a test keeps its phrases routed to tools); the sidebar grouped by life area;
her browser lives inside MIA (hidden Edge, live frames on the Browser page, the person clicks and types on the picture,
teaching records it; `browser.own_window` for the old window). The audit (Claude Doc
https://claude.ai/artifact/56xyaTxEQThT1vrYh484Ay) proposes seven areas, eight hubs and four screen tiers, waiting on
Zac; its step 1 (the areas in the sidebar, Today with a Waiting for you queue) is next once approved. Real use so far
is light (33 messages, most apps never opened): the organization is the priority.

**New 2026-11-07 (late night): the desktop opens on the web (DEC-0124); only Zac's words go out of the browser
(DEC-0122); taught procedures proposed (DEC-0123).** The window's web mode (`gui/main_window.py` set_web_mode,
`gui.web_first`): web front end edge to edge, classic Qt screens by Ctrl+Shift+C or for PC-only apps (the web Apps
page's "Open on this PC", a `/desktop-open/<id>` link the web view catches). Checked off-screen with the real
modules; not yet seen on Zac's screen. Phone app 145 installed on his phone by adb (built locally with
GITHUB_RUN_NUMBER=145, one above CI's 144).

**New 2026-11-07 (night): the Browser page and HTML e-receipts.** `web/browser.html` (core/web_browser.py): what her
browser is on, held steps with screenshots (Go ahead / Cancel on the step's own proposal), taught tasks with Do it /
Forget (`browser.run_task`, `browser.forget_task`). Emailed HTML receipts now keep each item on its own line
(core/document_text.py), so their pantry and materials effects work.

**New 2026-11-07 (night): the phone keeps your place.** The app is "MIA" with no title bar (theme NoActionBar); it
reopens the last page (MainActivity.remember / lastPlace, SharedPreferences, never the token), and every page keeps
its scroll, an open Talk and its draft for 12 hours (web/shell.js keepPlace / backToPlace, localStorage). Checked in
Edge with Playwright; not yet on the real phone.

**New 2026-11-07 (night): receipts that do things (DEC-0120), filed on their own with exact Undo (DEC-0121).** The inbox's email intake reads Zac's everyday
mailbox read-only, taking only receipts and orders (`core/inbox_mail.fetch_receipts`); a receipt proposes what it
means (`core/receipt_effects.py`: pantry and grocery list, a service done on the vehicle, workshop materials), done on
filing. Next: Zac's first real receipts (store formats will need tuning), the web Inbox's email setup (desktop only
today), and order emails from online stores (Amazon lines rarely parse as receipt lines).

**New 2026-11-07 (late): more projects, the design brief, MIA for Zac alone (DEC-0119).** Calculators for a chicken
coop and run, garage shelving, a bookshelf, a lean-to, a compost bin, a cold frame, a picnic table, a firewood rack
and deck stairs, each a built-in plan with steps, and `cut_list` for any project of his own parts (boards and 4x8
sheets). The Claude Design brief, "MIA: Screens and Flows for Claude Design", is a Claude Doc
(https://claude.ai/artifact/3R3ZjAWg4JzV1yE6dXK515): every screen, the frame, flows, states, round-one order.
DEC-0119: MIA is for Zac alone, never children; whether to remove the old child-account code is his call (WAITING_ON).

**New 2026-11-07 (evening): humor and plans (DEC-0118).** Humor: `core.personality.humor_for` (light turns, by
chance, a random flavor) and each person's level by chat (`set_humor`). Plans: the Library's plans shelf
(`core/plan_library.py`, tools in `core/assistant_plan_actions.py`, the Knowledge page's Plans section), material and
cut lists worked out in `core/build_calcs.py`. Next for it: more calculators as Zac names them (chicken coop, lean-to,
shelving, stairs), reading the text of dropped-in plan PDFs (OCR is in `core/ocr.py`), and a size form on the web.

**New 2026-11-07: MIA's browser (DEC-0117, `docs/BROWSER.md`).** Edge through Playwright in her own profile per
person; every step is sorted in code (`core/browser_safety.py`); commits wait as `browser.commit` for the person's
OK (screen or a coded yes); secrets never typed; tasks taught by showing (`core/browser_routines.py`), learned after
two clean runs (`browser.runs` loop). Tests: `tests/test_browser.py` (a pretend Edge); smoke-tested on real Edge.
Next for it: Zac's first real try (WAITING_ON), a web screen listing taught tasks and their runs, and a routing
corpus check that "open the website" reaches `browse`.

**Canvas build (DEC-0113 approved 2026-11-07; the design canvas "MIA Core Screens" is the reference, H-0092).**
Build order and where it stands (tick as each lands; screenshots in demo mode: serve a folder with `web/` and
`schema/` -> `docs/schema/` and open `/web/<page>?demo`):
- [x] Shared pieces: `web/ui.css` (orb states, finding, kind tags, status strip, focus surface, big action, states,
      What I used), app accents in `web/tokens.css` (`--atmo` from `<body data-app>`: Workout, Kitchen, Workshop).
- [x] Home: date, greeting, status strip, MIA Noticed (core/findings.py), focus rows with their kind, Upcoming beside
      it, MIA's column on wide screens. Engine: `dashboard()` gained `strip`, `finding`, each row's `kind`/`tone`.
- [x] Talk: her orb and state in the header (Ready, Listening, Thinking, Speaking, Can't Reach), What I used.
- [x] Sidebar: Home, Apps, Pinned (favorites), life areas folded (`shell()` gained `favorites`, `groups`, each app's
      `group`).
- [x] Workout: Today leads with one big Start; a live session takes the whole screen as Active (count large, how
      it was counted), Rest (draining ring) and Done (planned → done); tuck it away and a bar brings it back. Engine:
      `training_session.view()` gained each count's `how`, `last_counted`, `weight`, `rest_total`. Left for Workout:
      "+30 s" on rest needs a `training.rest_more` action; Progress charts (volume, frequency) per the canvas.
- [x] Kitchen: Today leads with the next meal's Start Cooking; the recipe page has Start Cooking; cook mode
      (`web/cook.js`) takes the screen: one step large, what it uses, the step's own timer offered, named timers that
      keep running, Back / Next Step / I Made This. Engine: `core/cooking_session.py` (a personal store, `cooking`),
      `core/cooking_actions.py` (`cooking.start/next/back/go_to/timer/timer_cancel/made/stop`; made = `meal.cook`),
      `cooking` on the Kitchen and recipe reads. Left: voice quick commands for cooking ("next step", "set a timer"),
      the glasses' cooking panel, servings scaling on the recipe page.
- [~] Every other app: the shared frame now matches the canvas on every page (`web/ui.css`, "every app's frame"):
      status strips with the label above, a white value and an index bar; "needs you" amber instead of red fills
      (attention panels, overdue chips and rows; red stays for real errors); tabs as a rail lit from below. Checked
      in demo mode on 60 pages (no new script errors; presence.html's old error is the page to retire).
      Done per app: Missions (ready-to-complete focus card, next objective, XP, source), Freedom (each figure tagged
      Fact/Calculation/Missing by `core.freedom.figure_kind`), Skills (capability status and next honest step first),
      Money (net worth with "+$X this month" and its six-month line: `core/net_worth_history.py` keeps one point a
      day, noted when Money is read, so the line starts the day it ships and grows with use), Garage and the asset
      page (machine cards with meter and plain due words; Spent this year, condition, one Needs You card with a big
      Done, what it cost lately: `core/web_equipment.due_words`, `meter_reading`, `_upkeep_this_year`), the Dungeon
      (today's run card with gold projected loot and a big Run Cleared, the overtime boss card, the week's runs meter), Compliance (one panel per group, each obligation
      a row with the one step `core/web_compliance.next_step` says comes next), Insurance (You Have, then
      quotes side by side each with `core/insurance.verdict`'s sentence, and a big Draft A Quote Request), Real Estate (the property card: its word from `core/web_screens.property_badge`,
      Rent Due amber; Rent / Cash Flow / Equity in one row), Workshop (Builds first: the bench card with Budget / Spent /
      Hours and the next step, Sell First, Best Earner per hour, a big Start A Build), Orders (the stage rail New / Building / Ready / Delivered
      with the step `core/web_business.order_stage` says moves it on; owed amber, paid green), Inbox (each waiting item's "Goes to" line from `core/web_inbox.goes_to`),
      Calendar (one page: Due Today, Past Due, Due Soon as short lines, the month beside them on PC), Journal (Write Entry first, the privacy line, one column of entries with
      date and tags above the title), People (Birthdays first: a card each with gift ideas, then the one person
      `core/web_more.catch_up` says to catch up with), Classroom (the course to continue from
      `core/classroom_manager.continue_course`, lessons to tick with their XP, subjects as rows that open), Guitar and any learning path (`core/paths.path_card`: stage rail, the week, Work On Next
      with homework, every check of the stage with who verifies it), Memory Vault ("N of M safe at home" per month from
      `core/memory_vault.vault_page`, a green or amber dot on each photo), Operating Journal (a card per line with its meter from
      `core/operating_journal.line_score`), Play (six weeks of play minutes as bars, the latest games with
      `core/recreation.effort_word`, a big Log a Game), Observations (a card each: Needs You or Noticed, the
      apps it drew on, Open in <app>, from `core/observations_web.card`), Expeditions (the next one as one card:
      heads-up from `core/web_more._trip_heads_up`, packing to tick, Start Trip; the rest as rows),
      Maps (the route card under the map: from the first
      waypoint to the one picked, distance, bearing, sunrise and sunset; no climb until MIA has elevation; the
      canvas's full-screen map with floating controls is still to do).
      Navigation (a compass with the needle on the bearing, waypoints with their grid, sun and moon tiles).
      World Map (km² cleared as the headline, the next achievement from `core/world_map.next_rank`, a big I'm Here).
      Knowledge (Search / Packs / Plans Shelf tabs; result cards with a snippet from
      `ReferenceLibraryManager.search_titles`; its test needs libzim, so run it on the PC).
      Music (song rows you tap to play, the one playing in cyan; a Now Playing bar held at the bottom).
      Files (the path, Upload, one list with line icons and a meta line, ⋯ for Rename and Delete).
      Passwords (one line per login; Show opens one card at the top with a countdown, Copy and Hide; ⋯ for the rest).
      News ("Three stories today", a card per story tagged by how it's known: `core/good_news.KNOWN_TAGS`).
      Look (the photo shown but not kept, the questions as chips, the answer with how she knows it, Take a Photo).
      Settings (a label over one card per group; each setting a row with its note and a switch; the demo now has
      `docs/schema/settings.example.json`).
      Profile (initial, name and email; About You rows that open their editors; Security; Sign Out; no household per
      DEC-0119; the demo now has `docs/schema/profile.example.json`).
      Fix-It (a big Report a Problem, Open · Worst First cards with ×N and the latest thing said, learned phrasings).
      Diagnostics (Passed / Look At / Unread tiles, a dotted row per check-up, Run Again).
      Still to do: Power, Toolbox, Lab and Field Kit need web pages first (WEB_PARITY).
- [ ] Glasses: the shared orb on `web/glasses.html`.
- Note: DEC-0119 (MIA for Zac alone) came after the canvas: drop household members from Party's leaderboard and
  Profile's household card when those screens are built.

**What Zac and the other agents need to do is in `docs/WAITING_ON.md`** (kept current every session).

**Where the build plan stands (`docs/BUILD_PLAN.md`, 2026-11-07).** Phases A and C are done; most of D is built.

- **Phase A, the loops (done):** 60-odd loops in `core/loops.py` (daily; heavy ones weekly from Night School);
  the dev suite, reverts and dependency audit (`core/dev_checks.py`); corrections in every area
  (`core/corrections.py`); weekly benchmarks graded by code (`core/benchmarks.py`, `python -m tools.weekly_bench`);
  the standing mission M-0001 (paused until Zac starts it) and MIA's Sunday self-report. Loop coverage
  (`core/loop_coverage.py`): 229 of 257 processes covered (2026-11-06), 25 declined with a reason, 3 to do (Plaid),
  with its why; a test fails on a new process nobody decided how to watch. Every loop as built: `docs/LOOPS.md`
  (generated: after adding a loop, run `python -m core.loop_catalog`; a test checks it).
- **Night School (DEC-0100, `docs/NIGHT_SCHOOL.md`):** starts at 01:30 from MIA's daily check once MIA restarts
  with the new code (Zac sleeps in the morning: see WAITING_ON). First real full night run by hand 2026-11-07
  08:55: one lesson passed (phone_link, kept in the lab for Zac), two failed.
- **Phase B:** step 7 (the module contract) waits on the rest of Zac's Interconnection Architecture doc. Step 8
  (cross-domain) built: composed plans, `afford`, `slipped`, `projects`, `habits`, `priorities`, `resources`
  and, 2026-11-06, `recall`, `person`, `patterns`, `discussed`, `returns`, `time`, `held back` and `running costs` (the routing
  audit: 90 of 112 benchmark questions answered by a plan, 11 by tools, 10 by the model alone: research, how-to
  and open-ended coaching, where the model belongs; the benchmark with the model: 85 of 112 clean, from 60),
  sureness in every plan answer, calibration by ratings and by projected dates checked when they come.
- **Phase C (done):** capability gaps (`core/capability_gaps.py`), seasons of memory (`core/seasons.py`), the
  Operating Journal (`core/operating_journal.py`), recreation (`core/recreation.py`).
- **Phase D:** Good News Radio (on for Zac; `core/good_news.py`); maps and comms (MGRS, TAK package and
  local-network sharing, GPX tracks; `docs/MAPS_AND_COMMS.md`; mesh and vector maps next); sight on the PC
  (`core/sight.py`; the glasses' and phone's Look button is Kotlin work next); the council from the phone
  (`web/council.html`); the Chronicles' weekly issue (`core/chronicle_issue.py`; waits on Zac approving archive
  events; consistent characters need T-0036's bigger image model).
- **Phase E (done):** T-0040, T-0042, T-0044, T-0045. T-0041's rest waits on real use of MIA's creations.
- **DEC-0054 built (T-0018, 2026-11-06):** `core/life_notes.py` (promises, decisions, ideas, goals set aside,
  kept on "keep it", a dated promise mentioned the day before and on it, done or forgotten by voice) and the
  goods-before-market-day finding. Left: the "still using it?" mark on subscriptions (it touches
  `core/budget_manager.py`, which holds Zac's Plaid work in progress: after it lands) and a screen for the notes.
- **T-0010:** a rating said out loud works everywhere, the glasses included; a 👍/👎 on the glasses screen is
  Muse's, if Zac wants one.
- **Working web screens** (formatting only, the look is muse's): `web/operating.html`, `web/play.html`,
  `web/news.html`, `web/council.html`, and 2026-11-06 `web/kept.html`, `web/diagnostics.html` (owner only),
  `web/knowledge.html`, `web/classroom.html`, `web/household.html`, `web/navigation.html`,
  `web/observations.html`, `web/memories.html`, `web/maps.html` (the offline topo tiles, no map library; vector
  tiles later). Still desktop-only: the Pi-era Power, Toolbox, Lab and Field Kit (DEC-0015: the Pi is a later step). Check a new page's script with
  `C:\Users\zacrh\Android\node\node.exe --check web/<page>.js` (a syntax error leaves the page blank). To see a page render on this PC, use
  headless Edge (no Playwright here): `msedge --headless=new --window-size=600,900 --screenshot=x.png
  "file:///C:/Users/zacrh/MIA/web/<page>.html?demo=1"`.
- **Found by the loops, 2026-11-06:** T-0050 (fixed: git output read as UTF-8), T-0049 (fixed: `dev.lab` counted
  practice), T-0051 (the phone's old `cryptography`/`starlette`/`fastapi`: Zac chooses; Claude recommends keeping
  them for now with the exposure written down, then Android Keystore over time). `phone.vulnerable` audits the
  phone's packages weekly from its build.
- **Known flaky:** the reference library's (one cause fixed 2026-11-06: an open libzim handle on delete), a native
  Qt crash mid-suite (seen twice), and `test_inbox.py`'s reading-corrections test (once in a full run).
  The one failing test is Zac's uncommitted Plaid work (`test_import_transaction_transfer_is_skipped`).

**Next for Claude:** the glasses' own camera and the question by voice for Look (the phone's web view takes and
chooses photos now, 2026-11-06, built but untried on the phone), Meshtastic once radios exist, vector offline
maps, the same character across panels (T-0036: SDXL-Turbo is in, 2026-11-06; an IP-Adapter next), the module
contract once the doc arrives, and
DEC-0054's last piece (a "still using it?" mark on subscriptions, after Zac's Plaid work lands).

**Glasses navigation: `docs/GLASSES_NAVIGATION_PLAN.md` is a draft waiting on
Zac's five questions.** Recipes open by shelf; Music plays on the phone
(`Music.kt`) from the glasses and reads the phone's Music and Download folders
(`music.extra_folders`); neither tried on real hardware.

**First boot and User Sync (2026-11-02): slices 0-5 of
`docs/GLASSES_FIRST_BOOT_PLAN.md` are in.** User Sync has all seven topics,
the phone permission step and a phone screen (`web/sync.html`, linked from
Home). After it come the Know Your System mission, Home's tour, the app
menu and four app tours (`core/welcome.py`, `core/app_intro.py`). Next is
slice 6 (idle tips). Still to do: a weekly repeat for the meal-prep mission;
a birthday without a year gets no reminder. Glasses' Home, app menu and
Missions are in the boards' look, and everyday actions go through the relay
(DEC-0064): compiled, not yet tried on the real pair; `mia-art` needs
publishing with them. Zac, on the
phone: Home, Getting To Know You, try the Allow buttons and a topic or two.

**The development platform's MVP is built (DEC-0070, 2026-11-03):**
`python -m tools.work` (list, claim, run --as, review --as, approve, history),
and `web/dev.html` for the device's owner. Details and what's not yet proven:
`docs/DEV_ECOSYSTEM_AUDIT.md` section 13.

**Tasks now live in `work/tasks/` (DEC-0068, 2026-11-03):** `python -m
tools.work list --ready` shows what can start. The build queue below is
history; anything still open from it is a task.

**Parked, to come back to (Zac, 2026-11-03), in this order:**
1. Personality plan (DEC-0067), `docs/PERSONALITY_AND_ECOSYSTEM_AUDIT.md`
   sections E to G. Done: phase 1, tuning round 1, 👍/👎 ratings, turn traces.
   Next: **phase 3, the self-knowledge map** (needs Zac's go), and **GitHub
   Issues** (blocked: no GitHub login on this PC; sign `gh` in, or a cloud
   session sets it up). Later: rating on the glasses (relay + Claude Design's
   screen), a fine-tune from the ratings, shopping for models.
2. Glasses: install phone build 143 or newer (DEC-0066 screens, fixes from the
   fifth relay review); Zac's call on making the glasses' question buttons
   read-only (an email question puts stranger-written text into a Talk turn).
3. Restart MIA on the PC to hear the new voice.

**Personality phase 1 is in (DEC-0067, 2026-11-03):** results in
`docs/PERSONALITY_AND_ECOSYSTEM_AUDIT.md` section E. The glasses' answers come from
`core/response_composer.py`; restart MIA on the PC, and the phone needs a new build,
to hear it. Next: her manner (jokes, stiffness, closing offers), measured with
`python -m tools.conversation_check`.

**Pending on the glasses (2026-11-03):** phone build 142 (DEC-0066: every
designed screen, money included, offered question buttons) is built in
`android-phone/app/build/outputs/apk/debug/` but not installed: Zac's phone
wasn't plugged in. Plug in, `adb install -r` it, reopen MIA on the glasses.
The glasses page is already live. A security review of everything added since
the fourth one (DEC-0064 to 0066: actions, missions, music, questions, money)
found no High issue (2026-11-03). Fixed: a reference could be approved after it expired, and I Made This couldn't work. Build 143 has both; install it, not 142. Still open, Zac's call: the glasses' question buttons run full Talk turns that can change things, and 'Any emails I should answer?' brings stranger-written email into such a turn (make glasses Talk read-only?). Recipe photos and her
awakening voice need a way round the relay's size limit (H-0079).

**The glasses are here (2026-11-01).** Meta's DAT plugin is installed in
Claude Code on the PC (`mwdat-android`, DAT 1.0.1). It corrects MIA's
docs: through the phone app the toolkit offers Display (a native UI on
the glasses), a live camera stream and photos, Inputs, and experimental
Speech, Motion and audio, plus "Hey Meta, start MIA" (Voice Invocations);
MockDeviceKit tests without glasses. **DEC-0059 (Zac, 2026-11-01): the
glasses go through the phone app's toolkit; no Web App, no Funnel.** The
first-boot work in `web/glasses.*` is Claude Design's, still in progress:
leave it to that session.

**Toolkit in the phone app (2026-11-01):** `MetaGlasses.kt` connects from
Settings (Glasses, phone app only), opens a session on display-capable
glasses and draws `/api/glasses`: pinned apps, each app's panels, their
readouts, Back. **It runs on Zac's real glasses (2026-11-02).**
Read-only so far: actions, Inputs, voice and the orb come next. The
toolkit needs Android 10, so minSdk went 26 to 29; build tools are AGP
8.11.1, Kotlin 2.2.21, Chaquopy 17, compileSdk 36. The app's id and token
live in `android-phone/local.properties` (gitignored), never in the repo;
CI builds get "0" unless the workflow is given them as secrets. Developer Mode
with 0/0 stopped at DAT_APP_ON_THE_GLASSES_UPDATE_REQUIRED. What fixed it
(Meta's docs don't say): real id and token in the build, then in the
Developer Center the package and signature under Configuration, a version
built to Ready, that version on the Beta channel, and Zac invited to it.
A later signing key or package change needs a new version. Keep
versionCode above the phone's when installing a local build (set
GITHUB_RUN_NUMBER; last used 141, installed over USB on 2026-11-02). Her art is public in `TheKingCS/mia-art`
(DEC-0061, artwork only; `python -m tools.glasses_art <folder>` draws the orb).

**Superseded in part by DEC-0062/0063 (2026-11-02):** her face becomes a Web
App (test page live at thekingcs.github.io/mia-art, installed by QR; look,
icon, key through the install link, crypto and speech all passed on the real
glasses) joined to the phone by a sealed relay, not built yet. Her icon opens
her; a tap makes her listen. The relay is live and passes `relay/test.mjs`
(`docs/GLASSES_RELAY_PLAN.md`; deploy from `relay/` with Node in
`C:\Users\zacrh\Android\node`). Next: the page's and phone's encryption and
pairing, with fake data; nothing personal crosses until the plan's gate passes. The phone can't open a Web App. Still unknown:
camera while the Web App shows. The tap works through the glasses (she heard
Zac and answered there); her spoken answers there run long and should be short.

**Getting MIA on the glasses (2026-11-02):** opening the phone app connects
her; a drop retries four times; Close MIA on her Home stays closed. **A tap
on the glasses brings her back** (works, Zac tested): the glasses send
KEYCODE_MEDIA_PLAY over Bluetooth, and ListenService plays a moment of
silence to hold Android's media button. With her showing, the tap is Select.
While the listener runs, a tap can't start paused music (Zac is fine with
it; MIA will be his music app). Not yet tried with the phone in a pocket.
**"Hey Meta, start MIA" doesn't work:** Meta says "no device called MIA",
and on the phone the voice stream reaches STARTED then "Channel error
occurred" within 100 ms, every time. Next step is Meta support checking the
Voice Invocation permission, optional now: DEC-0060 makes the tap the way
in (Zac doesn't want to ask one AI to open his AI); the code stays.
Next: her look on the glasses, then approving actions. Local
build: `C:\Users\zacrh\Android\phone_build.ps1 assembleDebug`.

**Zac's call: qwen3:14b or stay on qwen2.5:14b** (both measured
2026-10-30: same speed, tool choice 212 vs 213 of 213, qwen3 reasons
more on open questions; `docs/INTELLIGENCE_BENCHMARK.md` section 2,
the answers in `pc-check/intelligence-*.md` on the PC).

**Inspection and self-knowledge (2026-10-30, DEC-0056/0057 approved):**
`core/inspection.py` built (the core, this computer, MIA herself; "inspect
this computer", "inspect yourself", "run a self-check"); assistant port
scans limited to the own network. **The development lab is built
(DEC-0058, approved):** `python -m tools.lab list / propose / approve /
reject` (`core/dev_lab.py`), "what proposals are waiting?". Plan and next
phases: `docs/INSPECTION_AND_SELF_PLAN.md`.

**Usage audit and the design brief (2026-10-30):** `docs/UI_AUDIT.md`
(web pages weren't counted anywhere; now every web screen counts its
opens in `data/page_usage.json`; re-run the audit in a few weeks) and
`docs/design/CLAUDE_DESIGN_PROMPT.md` (Zac pastes it into Claude Design).
Retire-after-checking: `finances.html`, `grow.html`, `presence.html`.

**Active Training (DEC-0055, approved): phases 1 and 2 built** (the live
workout session, voice controls, Count With Me on the Workout screen,
the glasses' Active Training card). Next for it: the phone app's native
count voice and workout-listening mode (an Android build), retiring the
Qt Workout module's old in-memory session; status in
`docs/ACTIVE_TRAINING_PLAN.md` section 9. Zac, at the PC: say "start my
workout" and try a set with Count With Me.

**Waiting on Zac: DEC-0053 (looking things up online, when asked) and
DEC-0054 (remembering commitments, decisions, ideas and dropped goals),
both PROPOSED in `docs/DECISIONS.md` with their open choices.** Built
since the last note: the desktop panels get the instant code answers
(`core.assistant_turn.instant_answer`), long conversations keep their
start (`earlier_topics`), what "it" means (`what_it_means`), and a second
try before a loop answer is thrown out for an unchecked number.

**2026-10-30 (later): built.** Step 1 (one owner per fact:
`core/fact_owners.py`), the question plans (`core/question_plans.py`, 15
plans, by meaning with `core/meaning.py` and nomic-embed-text, in every
chat surface), the debt payoff math (`core/debt_math.py`), `llm.num_ctx`.
Live on the PC: plan answers in 3 to 7 seconds. Zac: ask MIA the
benchmark questions in your own words and say which answers are off.
Then built the same day: the tool loop (`core/tool_loop.py`), findings
(`core/findings.py`: on Home, in a "noticed" plan, and the four kinds
Zac allowed unprompted through the gate) and conversation state's first
slice (`core/conversation_state.py`, follow-ups). Next: the rest of
conversation state (what "it" is on any turn, open questions, a running
summary), then propose outside research (benchmark F4-F6) and the data
MIA doesn't record yet (commitments, decisions, ideas, best-by dates,
subscription use) as their own decisions. Also try qwen3:14b on the
bench (`tools/pc_model_check.py`, research R7) before any switch. Note: the desktop's chat panels don't use
`run_assistant_turn` (no quick commands or direct lookups there); unify
them when conversation state is built.

**2026-10-30: DEC-0052 approved** (`docs/REASONING_PLAN.md`): one owner
per fact (step 1, next to build), answers that combine several lookups
(question plans from Zac's own list, then a tool loop with up to 60 s),
findings across apps, conversation state. Zac's Intelligence Benchmark
(112 questions) is `docs/INTELLIGENCE_BENCHMARK.md`: today 77 reach the
model with no tools at all (`python -m tools.bench_audit`). Build order:
step 1 (pay owned by the Dungeon), then the 15 question plans in its
section 4, then the tool loop. Outside research (F4-F6) and the data MIA
doesn't record yet (commitments, decisions, ideas) need their own
decisions (section 5).

**2026-10-29 (Claude on the PC): her voice, and how she describes herself.**
- Zac: restart MIA, listen to Kokoro's Heart (now your saved voice), and
  try the others in Settings → Voice (Emma, Bella, Nicole, Michael,
  George...). `voice.kokoro_speed` (default 1.0) sets her pace. Then
  check Home and Missions look right (the stretched-cards fix was tested
  offscreen only).
- A fresh install gets Kokoro from `deploy/finish_install.py` (about
  350 MB in `voice_models/kokoro/`) and `kokoro-onnx` from requirements.
- Next for the voice: the phone still speaks with Android's own voice
  (`android-phone/.../Voice.kt`); it could fetch Kokoro audio from the
  PC when linked. A custom voice just for MIA is a later step (DEC-0051).
- Loose ends seen on this PC: 15 tests fail on master here (not checked
  against CI): the inbox and textbook PDF tests when the full suite runs, OCR
  because Tesseract is installed, and presence's out-of-date "Due in 2
  days" expectation.

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

**Claude on Zac's PC (2026-10-20).** Claude Code now runs on Zac's PC
(`claude remote-control` in `C:\Users\zacrh\MIA`, started at sign-in in
auto mode by `pc_remote_control.bat`; the PC signs in by itself after a
restart, 2026-10-20), next to the real MIA,
Ollama (qwen2.5:14b on the RX 7900 XTX) and the linked phone. On the PC:
`git pull` before starting, and commit and push after each piece (the
cloud sessions and Muse work from GitHub). Real data lives in `data\` and
`config\config.json`: gitignored, never committed, never pasted (DEC-0002).
**Top priority for the next PC session: Plaid, all cards linked (see the ⭐ section below).** First jobs, in order: (1) ~~the 14b's misses caught by MIA's own code~~
**done 2026-10-19: 213/213** (`settle_on_named_tool`, `core/assistant_chat.py`);
(2) a real
test of glasses voice, location quests while closed, the memory vault
and sync with the linked phone; (3) the voices (install.bat again);
(4) finishing modules without a web screen (`docs/WEB_PARITY.md`).

---

## ⭐ NEXT PC SESSION'S PRIORITY (Zac, 2026-10-21): every card and bank linked with Plaid

Zac wants MIA managing his finances: before anything else at the PC,
get all his cards and accounts connected through Plaid. Guide:
`docs/PLAID_SETUP.md`. State on 2026-10-21: Plaid isn't set up on the PC
yet (no `data\plaid_vault.enc`), and MIA's bank code has never talked
to Plaid for real.

**Zac, before you sit down:**
- [ ] A list of every bank and card company to link. The Trial plan
      allows **10 logins** (one login covering checking + savings + a
      card at the same bank counts once). Over 10? Pick the 10 that
      matter most, or ask Plaid about the next plan.
- [ ] Your phone nearby: banks send a verification code.
- [ ] Your Plaid dashboard login (Developers → Keys: client_id, the
      **Sandbox** secret and the **Production** secret). Never paste
      them into a chat.
- [ ] A vault passphrase saved in your password manager (MIA's
      Passwords app works) before you type it into MIA: it can't be
      recovered.

**The session, in order (Claude watches the logs and fixes as you go):**
1. `git pull`; open MIA → Budget → **Bank Sync**.
2. **A 10-minute sandbox test first** (Parts 3-4: Plaid's fake bank,
   `user_good` / `pass_good`). It costs no connections and catches any
   bug before a real login counts against the 10.
3. **Reset Plaid Setup** (clears the fake data), then **Set Up Plaid**
   with the **Production** secret (Part 6).
4. **Connect a Bank** for each login on the list; **Sync Now**.
5. Check with Claude: Expenses and Income categories, the Debts tab
   (APRs, minimums; add promo APR end dates by hand), nothing doubled
   on a second sync, the Summary's totals.
6. Then open **Freedom** (DEC-0038): with the bank synced it fills in by
   itself (spending, saved, the pace). Tag build spending to its build in
   Money so the builds count down. Then: bills, the budget, which debt
   to pay first, business tags for the homestead goods.

**Claude, at that session:** start here. Tail `logs\mia.log` while Zac
links; fix any failure before the next login (a failed login can still
use up a connection). Never read or print the vault, keys or access
tokens.

---

## 1. Your hands-on steps

- [ ] **Back at the PC (2026-11-04), in this order.** Restart MIA first so it loads everything new.
  1. **Approve T-0019**: `.venv\Scripts\python -m tools.work approve T-0019`, type T-0019 (about 4 minutes, two test runs; your settlement still counts).
  2. **Sign the reviewers in**: `codex login`, `gh auth login`, then `copilot` and `/login`. Until Codex is in, every task needs you to settle it (approve wants two providers).
  3. **The MIA Development window** (desktop shortcut): the board, the **Council** chat (`@mia` is free; `@claude`, `@codex`, `@qwen` use that one's allowance; `debate`, `discuss`, `budget 4`, `stop`), **Missions** (give one a goal and a scope; its tasks are `tools.work new "..." --source M-0001`; starting one spends your usage), **Voices** (play each member, keep one), **What the team learned** (confirm or withdraw MIA's notes), **The Chronicles** (106 candidates: keep, private or drop).
  4. **Make Something** in MIA's sidebar: describe something you track ("the seeds I save") for a screen, or something recurring ("every Sunday, tell me what I spent") for a workflow. Drafts change nothing until you publish.
  5. **Council Mode on the glasses**: "MIA, bring the council together", then a name ("Claude, start us off"), "everyone", "debate it", "sum up", "hold on", "that's all". The engine side is built; the speaker card and each member's voice on the glasses still need building and testing with you (T-0035).
  6. **Decide**: how the Creator looks on the page (DEC-0087).
  - Samples from the local image model: `C:\Users\zacrh\DevTools\imagegen\out\` (draft quality, under a second each).
  - Also new in the window: **Independence** (what each member has shown it can do; MIA's coder is 0 of 2 so far, from two real attempts on T-0019), **MIA's architecture** (read from the code; it found one real break, T-0042), and Made by MIA takes a **CSV file**.
  - Next build: T-0042 (a good first mission task), T-0035 (glasses side, with you), T-0036 (a bigger image model and consistent characters), the rest of T-0040 and T-0041.

- [ ] **Later, together (Zac, 2026-10-21): fill in all of Zac's own information** once the systems are built: the real addresses (homestead, each rental), how each activity is owned, filing jointly or not, the Freedom plan's numbers and builds, the flock, the recipes, the label info, the Compliance list verified one by one. Entered in MIA on the PC (data\, never the repo), with Claude walking through it.

- **PC day: done (2026-10-19).** The readiness check passed (Python, Tesseract, Plaid, account, password, Ollama with qwen2.5:14b, Phone Access, Tailscale serving, ffmpeg, starts with Windows); the speech and voice models didn't download yet (run install.bat again). Model picked: qwen2.5:14b (DEC-0022 note). Left: link the phone, and run install.bat again for the voices. Was: follow `docs/HOME_COMPUTER_SETUP.md` top to bottom: Windows Update + AMD driver + Git, `git clone` MIA, **install.bat**, set your password, **setup_home_pc.bat** (Ollama + qwen2.5:14b, Phone Access, ffmpeg, Tailscale, starts with Windows, no sleep, the model comparison, the readiness check), then on the phone Tailscale + Settings → Home Computer → Link. Then tell Claude "the PC is up" (and paste `pc-check\models.md`).

- [ ] **New in the next phone build (2026-10-19):** (1) **Talk to MIA through your glasses:** pull down Quick Settings → edit (✎) → drag **Talk to MIA** in, or long-press MIA's icon → Talk to MIA. With the glasses connected over Bluetooth, say "open Kitchen", "I weigh 182", or ask anything; she answers in your ear, and the glasses' screen switches to the app (once the glasses app is set up, ~Nov 16). Works with the phone alone too. (2) **Location quests while MIA is closed:** Settings → My Places → Allow All The Time (Android opens its settings: choose "Allow all the time"), then Allow Notifications. Arriving at a place then shows a notification; tap it.
- [ ] **Your insurance (DEC-0034):** Apps → **Insurance** → Add → **Read A Policy** (your car insurance's declarations page PDF, or a photo of it), check what MIA read, save. Then Shop It → **Draft A Quote Request**, send it to two or three insurers, and put their answers in with **Add A Quote**. MIA lines them up against what you have.
- [ ] **After PC day, the Memory Vault (DEC-0030 E):** on the phone, Apps → **Memory Vault** → Turn On The Vault, allow all photos. Leave MIA open on Wi-Fi a while; the strip counts what's safe on the PC. Then Free Up Space (Android asks you each time; its Trash keeps them 30 days). `docs/MEMORY_VAULT.md`.
- [ ] **Cameras (DEC-0033):** when you pick cameras, get local-stream ones (Reolink is easiest; `docs/SECURITY_CAMERAS.md`) and put them on the PC's Wi-Fi. With the phone linked to the PC (Settings → Home Computer) and Tailscale on both, add them from the phone: Security → Add A Camera → "On the home computer's Wi-Fi". They then work from anywhere. Next for Claude after that: smoother live video, motion alerts, cameras on the glasses, then lights/locks via a local Home Assistant.
- [ ] **Try the new game layer on the phone (DEC-0032):** Missions → **Quests** (start Ready For Winter; finish chapter 1 and watch chapter 2 open), the **Party** link there (start a raid; Join the leaderboard), Expeditions → **World Map** (press I'm Here; the phone asks for location once), Settings → **My Places** (Add Where I Am at the gym or store, Turn On, and next time you arrive MIA asks), a recipe → **I Made This** (the pantry goes down), and listen for the chime when you finish an objective (Settings → Sound to turn MIA's spoken lines on).

- [ ] **Homestead goods (DEC-0036, 2026-10-21):** in MIA (PC or phone) → Workshop → Recipes → Add Recipe: one real thing you make in batches (materials in your own units, "One batch makes", the price each, how many days it keeps). Add its materials under Materials, Begin Crafting, Finish, then the **Goods** tab: Label Info (your business name, address and Kentucky's statement), print a label, and try a market day. Zac's line stays within Kentucky's home-based processor rules (banana bread, cookies, breads, honey; `docs/HOMESTEAD_GOODS.md`). Tell Claude what's clumsy.

- [ ] **Chickens, greenhouse goods and starters (DEC-0037, 2026-10-21):** Workshop → Recipes → **From A Starter** → Eggs (set your price and how many days they keep). Apps → **Chickens** → Add A Flock (pick Eggs for the cartons), tap the eggs in each day, log feed when you buy it, and put a dozen Into Cartons. In the Grow Lab, harvest a batch "Also into stock". Tell Claude what's clumsy.

- [ ] **Freedom (DEC-0038, 2026-10-21), from the phone now:** Apps → **Freedom** → **Your Plan**: what a month of living takes, saved so far, about what you save a month, your take-home an hour and your shift length. Then **Add A Build** for each: greenhouse, chicken coop, solar, root cellar (about what each costs). Tell MIA your reasons ("remind me why") so they show at the bottom. Once Plaid is linked, the numbers fill in by themselves.

- [ ] **Zac's two specs (2026-10-21): approve the next steps.** Read `docs/BUSINESS_OS_AUDIT.md` and `docs/INTELLIGENCE_AUDIT.md` (sections 7-8 / 7 say what Claude needs). Approve DEC-0040 (the obligations calendar; and give MIA your addresses, how each activity is owned and whether you file jointly, in MIA, not in a chat that gets committed) and DEC-0041 (capability registry, then docs retrieval). Then ask your phone "What AI model are you using?" again.

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
- [ ] **Fitness and meals (2026-10-14, DEC-0020/0021): the screens are
      in the phone build.** Workout → Today → **🎯 My plan**: set your
      goals, training days, what each training day is ("Dips 3x8", one a
      line), handstand practice, prep day, allergies. Kitchen → **Week
      Plan**: tap "+ add" on a day (or "Fill empty meals"), open a meal to
      see its recipe, try **Schedule meal** and **Add to grocery list**.
      Then log a weigh-in (Workout → Progress) and say "step one of
      today's workout complete", "today's lunch complete", "I weigh 182".
- [x] Your PC's specs (DEC-0022, via Muse H-0037/H-0038): Ryzen 7
      9800X3D, Radeon RX 7900 XTX 24 GB; on once the Ethernet cable
      arrives. (RAM still unknown; it doesn't change the plan.)
- [ ] **When the PC is set up:** install MIA on it (the Windows
      installer from the Windows CI run), Ollama for Windows (it runs on
      the 7900 XTX; Claude will say which model to pull), and
      **Tailscale** on the PC and your phone, signed in with the same
      account (free; this is what lets the phone reach the PC from work).
      Leave the PC on (sleep off) for MIA to reach it.
- [ ] **Look at MIA's new look (DEC-0023)** in the newest phone build and
      say what to change.
- [ ] **Your plan from Muse (H-0030):** ask Muse for your plan "in MIA's
      paste format" (she has `docs/PLAN_TEXT_FORMAT.md`), copy it, then
      Workout → 🎯 My plan → **Paste a plan** → paste → **Read it** → check
      what it says → Yes. Undo takes it all back.
- [ ] **Run the 1.5B Quick test again on build 21 or newer** (Model test,
      tap Start first) and send the screenshot: some questions are now
      answered by MIA's code instantly.
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
- [ ] **Try the new round (2026-10-16, H-0048)** in the phone app once it
      updates (or https://thekingcs.github.io/MIA/web/calendar.html and
      .../glasses.html with placeholder data): the **Calendar** (Home →
      Calendar), a **photo** on a recipe (open it → Add Photo), and on the
      glasses Missions → Select Mission → Sort, Kitchen → Recipes, Garage
      → Past Due. Star the apps you want pinned on the glasses (Calendar
      too, if you want it in your pins).
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

*History since 2026-11-03: open work is in `work/tasks/`.*

**First: talk to MIA on the PC again (DEC-0125).** Web mode (DEC-0124) hides the character panel, where
hold-to-talk lives, and the web Talk has no mic, so the PC can't be talked to. Then humor on the Settings screen
(it's voice-only). Both from `docs/design/CORE_SCREENS_REVIEW.md`, which also lists what Claude Design's screens
show that MIA doesn't do.

**Parity (DEC-0125): close the gaps in `docs/PARITY.md`.** Voice is done but Look (a voice "look at this" that
takes the photo itself) and Passwords (screen-only by Zac's decision). Next the phone pages (Power, Toolbox, The
Lab, Field Kit), then glasses cards and asks. Each closed gap: delete its line in `work/parity.json` and run
`python -m core.parity`. New tools go in both `core/application.py` and `core/core_runtime.py` (K-0069).

**Every session, ongoing (DEC-0104): document what you touch, and work the backlog.**
`.venv\Scripts\python -m tools.docs next 15` lists the files with the most undocumented definitions (engine
first); `show <file>` prints each with its code; write the docstrings by reading the code (what it is, what it
does, how when that isn't plain; check any claim you aren't sure of), put them in a JSON
`{"core/x.py": {"func": "...", "Cls.meth": "..."}}` and `apply` it (inserts them, lowers the ratchet,
regenerates `docs/ATLAS.md`). Skip `core/budget_manager.py` and `core/plaid_manager.py` while Zac's Plaid work is
uncommitted. 6,863 of 13,808 documented on 2026-11-07: every core/, server/ and tools/ file is done (but those two); every modules/ and gui/ file is done too. In tests/ a test named as a sentence counts as documented (DEC-0116); 13,146 of 13,816 are documented, and what's left is test helpers and short-named tests (`tools.docs next` lists them). A docstring may now end in a quote (`apply` adds a space).

**Her own models (DEC-0106, build plan step 19):** the model forge (`core/model_forge.py`, `python -m tools.model_forge router` / `list`) made her first model 2026-11-07, a tool router trained on her tools' own words and the person's record names: 80% first pick, 95% top five on requests it never saw (card in `data/models/router/`, not in use). Each model is assigned to an issue (a slipping loop) or a project and judged by it; the playbook of five kinds and `python -m tools.model_forge needs` say where one could help. The router now runs in the shadow on every traced turn (its top five in the trace, the `models.router_shadow` loop); once it has 20 turns with a tool called, read how it did before deciding anything. Next: build plan step 19 (d) onward. `self_docs` (get_mia_docs, the council) now answers from her code's docstrings and the Knowledge Vault too.

**Her specialists (DEC-0109, `docs/specialists/`):** nine workers (construction, homesteading, radio, strategy, maker, outdoors, research, testing, engineering) with sourced workbooks; study hall gives one a night new notes (`python -m tools.specialists study <id>` by hand); notes stay derived until Zac confirms. Add a specialist by adding it to `SPECIALISTS`.

**Her weekly self-audit (DEC-0108):** `python -m tools.audit` (report), `code`, `connections`, `run`. Night School runs it weekly and opens one task each for the top code and interconnection finding (first: T-0052, T-0053). Her best practices are `docs/practices/` (written by `core/practices.py`: edit principles there, lessons come from the vault). Life events, links and the life state's new `areas` section (`core/life_areas.py`) were done 2026-11-07: 49% to 76% connected. What's left (boss book, dungeon, recreation, fitness, quests...) comes up one a week as an audit task.

**Her curriculum (DEC-0107, `docs/CURRICULUM.md`):** ten computing tracks, one Night School lesson a night for the next objective (`python -m tools.night_school curriculum`). Nothing run yet: the first real night with it is the next one. Grow it in `core/curriculum.py` when her teacher's lessons point at a gap.

**The Highest Self (H-0089 → H-0090, DEC-0114 PROPOSED):** the doctrine is `docs/design/MIA_HIGHEST_SELF.md`; its core is in `core/personality.py` (two CHARACTER clauses, a tone example, the faith-and-meaning line, the integrity rules, the values pinned by `tests/test_personality_values.py`). Measured on the corpus (`pc-check/conversation-highest-self-*`): routing fixed, doubt and grand plans better, "is God real" still deflected, dependency uneven, answers six words longer. Next, after Zac's ratings and decision: the three modes (Intellectual, Counselor, Creative), then tune on his ratings.

**Experience Maturity (DEC-0113 APPROVED 2026-11-07, amended):** the design canvas "MIA Core Screens" (H-0092, `docs/design/MIA_DESIGN_STANDARDS.md` §13) is the reference; the build runs in order: shared pieces (`web/ui.css`, the orb), Home and Talk, Workout, Kitchen, then every other app. Progress is tracked in the "Canvas build" list below.

**Learning paths (DEC-0112):** any desire runs through `core/paths.py` (guitar is its first program; anything else is drafted and started on the person's say-so). Don't build a parallel learn-a-skill feature: add a `Program`. MIA's own curriculum is ten Programs on her own PathBook (`core/curriculum.mia_book()`, `data/dev/mia_paths`); `python -m tools.night_school curriculum` shows it. **Guitar (DEC-0111):** when Zac has tried it, read his heard-check attempts (his folder's `paths.json`, path `guitar`): if real chords fail that should pass, adjust `CHORD_TONE`/`STRAY` in `core/guitar_ear.py` from those numbers (they were set on synthesized strings).

**Every commit, ongoing (DEC-0110): docs change with the code.** Run `.venv\Scripts\python -m tools.docs stale` before committing: it lists every definition whose code changed while its docstring didn't (changed parameters first). Read each and fix the words that no longer hold; lab reviewers get the same list.

**Every session, ongoing (DEC-0105): write MIA knowledge entries for what you build** (`work/knowledge/`, via `core.dev_knowledge.add`, by claude, citing the commit, task or decision): what you did, how, why that way, and what went wrong. K-0038 to K-0042 are the first (the documentation method and its lessons).

**The mission system is locked in (DEC-0047, `docs/MISSION_SYSTEM.md`).**
Build order (Zac said begin, 2026-10-27): 1) the Loop ✅ built
(`core/the_loop.py`), 2) the Sunday check-in ✅ built
(`core/weekly_checkin.py`). 3) the **Fix-It Log** ✅ built (DEC-0049, `docs/FAILURE_LOG.md`).
**Claude on the PC, every session: read `data/profiles/<id>/fix_report.md`
(or Apps → Fix-It Log) first, turn the worst open issues into failing
tests and bench cases, fix, mark fixed.** **2026-10-27, Zac + Chat's direction:
the Brain, the Body, the Relationship.** The audit and the order are in
`docs/BODY_AND_RELATIONSHIP_PLAN.md` (section 8), with four questions
for Zac (section 9), answered (DEC-0050). **At the PC first: run
`python tests/live_model_check.py` (its new PERSON_CASES check MIA never
dead-ends with "I don't know") on the 14b; fix any FAIL before going on.**
Then plan step 1, the About Me page. Was: the Sunday morning
check-in, 3) adventures from the day's project with real-gain rewards
(the craft, the recipe unlock) and guild ranks, 4) pattern noticing,
titles, the emergent class, 5) the Codex, seasons as quarters,
cutscenes. **Zac, at the PC:** The Dungeon → Loop → Change on your
work: Sun–Thu (or your days), 9:30 pm to 6 am, and in Setup the
30-minute unpaid break; Chores: 2:30 pm. Or just
tell MIA. Reminders come from the PC app (it has to be running).

**Zac, at the PC (2026-10-27, DEC-0046):** Apps → The Dungeon → Set Up
Your Dungeon: the job, pay an hour, when overtime starts, the day the pay
week starts, and the words the paycheck shows in the bank (look at one
deposit under Money). Then clear today's run and try "GM this" in Talk
after a rough shift. Live-model check of Game Master mode on the 14b is
owed (tone, no invented numbers).

**Zac, 2026-10-24 (DEC-0045): the apps stay the layout; make MIA smarter
at using them.** The five-places frame is undone. Next AI work: MIA
working the apps for you in Talk and by voice (understand what you mean,
do it across apps, say what she did), not new navigation. Then Muse's
H-0070 Freedom look pass.

**Game layer (DEC-0028, `docs/GAME_LAYER.md`), 2026-10-17:** all built
except the watch HUD (waits for the watch): Reward Shop, gear bars,
bosses, stats, buffs, the Chronicle, and (DEC-0032) questlines, kitchen
blueprints, world map, party, sound, location quests. Possible next
steps there: more seasonal starters, a basemap under the world map
(offline tiles). Location quests in the background are built
(2026-10-19, `Places.kt`). **ALICE picks built (DEC-0029):** What I Used, MIA Remembers,
one conversation everywhere, the voice guide. **Expansion audit**
(`docs/EXPANSION_AUDIT.md`, DEC-0030 approved): phase B crafting is
built (Workshop → Recipes / Builds). DEC-0030 approved (2026-10-17). Built since: the phone side of DEC-0022 (`docs/HOME_COMPUTER_SETUP.md`), phase C Orders & Quotes, phase D Grow Lab, and show-off mode (DEC-0031). Next:
DEC-0022 on the real PC (model comparison; two-way sync with photos, files, conversations and the journal, heavy jobs and the **memory vault (phase E)** are built, 2026-10-18; vault next: copying while MIA is closed via an Android foreground service; near-duplicates (offered like bursts) and search and captions on the PC are built, 2026-11-06: `core/vault_captions.py`), then phase C (quotes from a recipe, customers and orders, a portfolio page),
D (grow lab), E (memory vault, after DEC-0022's phone↔PC link). Receiving
from a scanned receipt into a recipe's materials is a small follow-up.

**The phone spike passed (2026-10-07, `docs/PHONE_SPIKE.md`)**, and Zac
has it on his phone (first start under 8 s). His feedback is fixed:
account menu, no Apps tile, every card the phone's width, Garage spacing.

**Next build (DEC-0022, approved 2026-10-15): supercharged online.**
When the phone can reach Zac's PC (same Wi-Fi, or Tailscale), Talk uses
the PC's bigger model and falls back to the phone's 1.5B mid-
conversation; MIA shows which level she's on. Then heavy jobs on the PC
(voice, OCR, textbooks, email, bank sync), then two-way sync. Cloud AI
stays off unless switched on. **Zac's PC: Radeon RX 7900 XTX, 24 GB
(AMD: Ollama's ROCm support on Windows, or llama.cpp's Vulkan build).**
Plan: measure Qwen 2.5 14B (~9 GB, fast) and 32B (~19 GB, fits the card)
on the golden set in CI (accuracy only; CI has no GPU), pick one, then
build: the phone finds the PC at home (same Wi-Fi) **and from anywhere through Tailscale from the start** (Zac, 2026-10-15: from work Wi-Fi too),
Talk uses it with the phone's 1.5B as fallback, and the shell shows the
level (PHONE / HOME PC / ONLINE, Muse's H-0035 §5). Then presence-page
frame and the dashboard saying card as a readout (H-0035 §3).

**Glasses Heads-Up screen (2026-10-18):** swipe down on the orb; clear until a win or notification, then a card for 6 s. **Glasses quick action menus (2026-10-16, H-0042)** work in the preview
for every app (`core/glasses.py`); pins are the person's favorites
(DEC-0024); Household, People and Inbox panels and line icons are in
(H-0045). Phase 3 voice is built (2026-10-19, `core/glasses_voice.py`, `Voice.kt`: the phone listens through the glasses as a Bluetooth headset). Then: Phase 4 on-device
test when the Display arrives (~Nov 16: Funnel URL, revocable
glasses-only link limited to `/api/glasses` and `GLASSES_KINDS`).

**The Stark interface (DEC-0023, 2026-10-15)** is built; Muse reviews
(H-0034). Follow-ups: workshop-style header images, more line icons,
the presence page and character art in the new language.

**Fitness screens built (2026-10-14, DEC-0021, H-0029).** Next for
them: Muse's look review; recipe photos; a reps field on the practice
timer if Muse wants it; the 1.5B's remaining misses (questions with no
unique trigger: "What bills do I have?" reaches inventory through "do I
have"; debts, chores, the budget summary; completion phrasing).

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



- **The ideas list: `docs/future/IDEAS.md`** (Zac, 2026-10-18): future
  features that automate life and save money, each written up the same
  way. First one: an insurance check-up (compare and save). Zac adds to
  it over time; nothing there is approved until he picks it.


## 4. Known loose ends

- **On Zac's PC (2026-10-20):** `pytest` used to save into the real
  `config\config.json`: one run left 49 test profiles (Alex, Faith) and
  made a Faith the active one. Fixed in `tests/conftest.py` (a temp
  config, and the end-of-run guard now covers config.json too); the
  leftover profiles are removed. Windows Update restarted the PC
  overnight (12:22 to 3:01 AM) and MIA only starts at sign-in, so it
  stayed down until Zac signed in. Fix (Zac chose both):
  `pc_stay_up.ps1` (also setup step 6): no restart while signed in or
  6 AM to midnight, and Windows signs in by itself (Sysinternals
  Autologon). Done 2026-10-20: zacrh is now a local account (it was
  a Microsoft account Zac doesn't use) and signs in by itself. Two tests
  fail only here, on unchanged code too: `test_ocr.py::test_unavailable_without_tesseract`
  (Tesseract really is installed) and
  `test_phone_server.py::test_mia_gives_herself_a_console_when_there_is_none`
  (stdout is Windows' `nul`, which says it's a terminal). Something loaded
  llama3.2 onto the graphics card forever earlier that day (the default
  config's model with keep_alive -1), costing ~1 s an answer; it was
  unloaded, and `ollama ps` should show only qwen2.5:14b. Git on the PC
  has no name/email set (Claude commits with `-c user.name=Claude -c
  user.email=noreply@anthropic.com`) and no auto-push hook.

- `tests/test_reference_library_manager.py` fails now and then on Zac's PC (a different test each time; passes on rerun, 2026-10-21): find what's timing-dependent.
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
