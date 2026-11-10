# Waiting On

*The running list of what Zac and the other agents need to do (Zac, 2026-11-06: "keep a running track of what other
agents or I need to do and I will address those later"). Claude adds to it as work needs someone, and strikes an
item when it's done. Newest first within each person. Read with `docs/NEXT_SESSION.md`.*

*Last updated: 2026-11-08*

## Zac

### Start here (2026-11-08 evening: the short list, in order; everything else is below)
0b. [ ] **The glasses' camera for Look** (2026-11-09; the only parity gap left to build): in Meta's Wearables Developer Center, approve Camera for the MIA app. Then Claude adds mwdat-camera to the phone app and a CI build goes on the glasses to try (the steps are in work/parity.json, sight:glasses).

0. [ ] **Let Claude commit again** (2026-11-08 night): the session's safety check blocks commits, since the post-commit hook pushes them. Create `C:\Users\zacrh\MIA\.claude\settings.local.json` allowing `Bash(git add *)`, `Bash(git -c user.name="Claude" -c user.email="noreply@anthropic.com" commit *)`, the same with `merge *`, and `Bash(git push origin master)` (and add it to .gitignore). Waiting on disk, uncommitted and tested: core/greenhouse_setup.py + tests/test_greenhouse_setup.py + K-0157 (with edits to greenhouse_link, greenhouse_provision, assistant_turn, ATLAS, DECISIONS, NEXT_SESSION, WAITING_ON); the workshop_circuit and root_cellar jobs (core/trade_jobs.py, tests/test_trade_session.py, K-0158); the hoop-house and cold-room calculators and plans (core/build_calcs.py, core/plan_library.py, core/assistant_plan_actions.py, core/trades.py CALC_FOR, tests/test_plan_library.py, K-0159); all of Trade Master's first list written (49 of 49: home building from site layout to gutters, and the furnace diagnosis) and the second to sixth tiers written too (99 of 99: the fourth the plans shelf's builds, the fifth the land and its water, the sixth the workshop's subpanel; core/trade_jobs.py, core/trades.py, K-0160, K-0168). The node's email password from the vault (core/greenhouse_provision.py push_secret, core/greenhouse_setup.py step 8, tests/test_greenhouse_secret.py, K-0161). What's Next's spring case (core/development_engine.py WINDOW_BONUS, tests/test_development_engine.py, K-0162). The "the job" question plan (core/question_plans.py, tests/test_trade_session.py, K-0163). Every silent except the audit found is gone: seven given a log line, the five best-effort ones narrowed to the error they expect or logged. Two partial apps finished: Real Estate records a sale (property.sell, record_property_sale, Record Sale on the page; K-0164) and The Dungeon counts tips and shift differentials (K-0165). The Workshop compares cups to pounds for materials on a sourced density table (K-0166). A password or sign-in email changed at the desktop now reaches the security log, and a changed email alerts you (K-0167). A set-aside mission is kept in the history, and the newer event types have words (core/life_events.py). Screens MIA makes for you work by voice now (make, list, publish, roll back, remove, add an entry, read it back; K-0169). Boss battles, questlines and your places ("I'm at the gym") by voice too (K-0170). The greenhouse's live link (DEC-0150 answer 3c): the node's dashboard and digital twin served read-only, "show me the greenhouse live", and "how's the greenhouse?" read fresh (K-0171). **DEC-0151 to approve or undo:** the self-knowledge map (T-0007), built under your /goal: "what breaks if Ollama stops?" (core/service_map.py, K-0172). Health changes and ID wallet cards now reach your own history without their names or details. The greenhouse setup and each Trade Master job are missions (Zac, 2026-11-09: not on Today): the setup's steps are its objectives, ticked in Missions or seen done by MIA, with the step you're on in the Greenhouse page's What's Next; a job is its mission from the start, a phase an objective (K-0182). **Projects and Missions connected (DEC-0152, from your handoff):** a project lists its missions and its progress worked out from tasks and missions; a mission links back to its project and shows the step it's on, with Next Step or Checked for a job; "make the coop mission part of the homestead" by voice; your concept is with Muse for the look (H-0101; K-0183). The desktop's 18 duplicated tool handlers (alarms, notes, inventory, missions...) now hand off to core/core_runtime.py, one body each (K-0174). The self-audit's store connections, worked through: seven stores marked as holding machinery or copies (core/self_audit.py BY_DESIGN, with why), a finished or stopped Trade Master job recorded by its own store, and the greenhouse in the life state's areas (core/life_areas.py; K-0175). Eight more kinds of thing can be linked to a goal, project or debt (a class subject, a workout, a grow-lab batch, a questline, a workplace, a direction, a campaign, a letter in the inbox), and directions, workplaces, worlds and questlines are life-state areas; the audit's store gaps went from 47 to 20 (K-0176), then to 16: art, creations, plans, play, the world map, boss battles and the fitness plan are life-state areas, and a build plan, a creation, a note and a GPS track can be linked (links read dict records now; K-0177). Then to none: the asset page shows a tool's business use this year with Log Use and Remove (core/business_use_actions.py), the Chronicle page has a Kept tab for the moments kept for the Chronicles with their marks (core/saga_actions.py), a prestige or reward unlocked is a line in that person's history (core/progress_history.py), and health, the ID wallet and memories stay unlinked on purpose (links are the household's, and a link names its record). The self-audit's interconnection findings are zero (K-0178). Voice tools that run an action now share one runner, core.actions.run_as_tool, which always checks first as the screen does (three copies had skipped the checks; K-0179). The self-audit no longer counts an elif as a level of nesting, which had made 54 flat chains look deeply nested (15 real ones are left, none deeper than 6), and the plan importer's goals and meals lines are their own helpers (K-0180); the food table's portions and sync's folder scan are their own helpers (K-0181). Full suite 6,121 passed. 
       To commit it yourself instead, stage exactly these (not the Plaid, email or specialists files other sessions have open): `git add core/assistant_plan_actions.py core/assistant_turn.py core/build_calcs.py core/development_engine.py core/greenhouse_link.py core/greenhouse_provision.py core/greenhouse_setup.py core/plan_library.py core/question_plans.py core/trade_jobs.py core/trades.py docs/ATLAS.md docs/DECISIONS.md docs/NEXT_SESSION.md docs/WAITING_ON.md tests/test_development_engine.py tests/test_greenhouse_secret.py tests/test_greenhouse_setup.py tests/test_plan_library.py tests/test_trade_session.py work/knowledge/K-0157* work/knowledge/K-0158* work/knowledge/K-0159* work/knowledge/K-0160* work/knowledge/K-0161* work/knowledge/K-0162* work/knowledge/K-0163* core/actions.py core/browser.py core/lab_actions.py core/offline_maps.py core/party.py core/saga.py core/memory_vault.py core/real_estate_manager.py core/estate_actions.py core/web_screens.py core/application.py web/real-estate.js core/work_dungeon.py core/dungeon_actions.py core/web_dungeon.py core/assistant_dungeon_actions.py web/dungeon.js core/capabilities.py tests/test_web_screens.py tests/test_work_dungeon.py tests/test_capabilities.py work/knowledge/K-0164* work/knowledge/K-0165* core/units.py core/craft_recipes.py tests/test_homestead_goods.py work/knowledge/K-0166* core/security_log.py core/core_runtime.py server/app.py tests/test_security_log.py tests/test_server_app.py work/knowledge/K-0167* docs/HANDOFFS/H-0100_claude-to-muse_portal-art-batch-2-confirmed.md core/life_events.py core/mission_manager.py tests/test_mission_manager.py work/knowledge/K-0168* docs/CURRENT_STATE.md tests/run_module.py core/assistant_creation_actions.py core/web_surfaces.py tests/test_creations.py work/knowledge/K-0169* core/assistant_game_actions.py tests/test_boss_battles.py tests/test_questlines.py work/knowledge/K-0170* tests/test_places.py homestead/viewer/serve_exports.py tests/test_greenhouse.py work/knowledge/K-0171* core/service_map.py tests/test_service_map.py work/tasks/T-0007.md work/knowledge/K-0172* core/assistant_turn.py docs/EVENTS.md core/health_manager.py tests/test_health.py core/today.py core/actions.py core/loops.py docs/LOOPS.md tests/test_greenhouse_setup.py tests/test_trade_session.py work/knowledge/K-0173* work/knowledge/K-0174* core/self_audit.py core/trade_session.py core/trade_actions.py core/life_areas.py tests/test_life_areas.py work/knowledge/K-0175* core/links.py tests/test_links.py work/knowledge/K-0176* tests/test_history_and_links.py work/knowledge/K-0177* core/business_use_actions.py tests/test_business_use_actions.py core/web_equipment.py web/asset.js core/saga_actions.py tests/test_saga_actions.py core/chronicle.py web/chronicle.js core/progress_history.py tests/test_progress_history.py core/web_more.py core/event_catalog.py docs/EVENTS.md docs/PARITY.md work/knowledge/K-0178* core/assistant_answer_style_actions.py core/assistant_domain_actions.py core/assistant_trip_route_actions.py core/assistant_world_actions.py core/assistant_asset_part_actions.py core/assistant_health_actions.py core/assistant_proposal_actions.py core/assistant_cooking_actions.py core/assistant_goods_actions.py work/knowledge/K-0179* work/parity.json core/plan_import.py tests/test_self_audit.py work/knowledge/K-0180* core/food_table.py tests/test_food_table.py core/sync.py work/knowledge/K-0181* core/today.py core/trade_actions.py core/web_equipment.py web/equipment.js work/knowledge/K-0182* core/mission_projects.py core/mission_guide.py core/mission_manager.py core/web_progress.py core/web_projects.py core/assistant_game_actions.py core/greenhouse_setup.py web/missions.js web/projects.js tests/test_mission_projects.py tests/test_web_projects.py docs/HANDOFFS/H-0101_claude-to-muse_projects-and-missions-concept.md docs/design/assets/concepts/projects_and_missions.png work/knowledge/K-0183* core/id_wallet.py tests/test_id_wallet.py core/inbox_mail.py core/mail_send.py core/browser_routines.py`, then commit and `git push origin master`.
0. [ ] **Push the homestead merge** (you said yes; the session's safety check held the push itself): in
       `C:\Users\zacrh\MIA` run `git push origin master`. It carries the merge (verified: MIA's suite unchanged,
       the node's scenarios as before) and the greenhouse work on top of it.
1. [ ] **Restart MIA** (close both copies, start it once): turns on everything built 2026-11-07/08, including the
       encryption at rest. Then **save the recovery key** (Settings, or `python -m tools.data_key recovery`) in your
       password manager.
2. [x] ~~The homestead merge~~: you said yes; merged (item 0 is its push).
3. [ ] **Decide three proposals:** DEC-0147
       the Woodworking Studio (four questions), the iOS path (three options,
       below), and T-0051 the phone's old security packages (three options, below).
4. [ ] **Your history's older lines** (DEC-0126): seal them (close MIA, then
       `.venv\Scripts\python -m tools.data_key seal --history`) or say leave them plain.
5. [ ] **Start SearXNG** for online lookups (`docs/ONLINE_LOOKUP.md`: Docker Desktop and one command).
6. [ ] **Commit the DEC-0133 email files and finish Plaid** on the PC (both are your uncommitted work: details below).
7. [ ] **Encrypt the PC's drive** (Windows 11 Home has Device Encryption: details under Security).

### The greenhouse (2026-11-08: approved and built, DEC-0150)
- [ ] **When you start:** say "let's set up the greenhouse". MIA keeps the ten steps in order and "what's next?"
      tells you the step, the device, what you need and exactly what to say; "the Pi is ready" / "done" / "skip that"
      move it on. The two items below are the same steps, for reference.
- [ ] **When the pilot build starts:** "walk me through building the aquaponics system", then the controls job, then
      "walk me through the fishless cycle". Install PlatformIO on the PC (`pip install platformio`) before "flash the
      safety MCU".
- [ ] **When the Pi is ready:** "prepare the Pi" (it writes the configs and the Imager steps), then "push the
      greenhouse to mia-greenhouse", then on the node run `viewer/serve_exports.py --bind <its address>`, then "take
      over the greenhouse at <its address>".

### Trade Master (2026-11-08: approved and built, DEC-0149)
- [ ] **Try it after the restart:** "walk me through building the coop" (or the greenhouse, the workshop, the cold
      room), then "next", "why?", "what should I watch for?", "checked" at a hold point, "make it a mission", and
      "stop the job". For a diagnosis: "my toilet keeps running, help me figure it out", then yes or no.
- [ ] **Confirm the jobs as you use them:** each is drafted from its sources; tell Claude what's wrong or missing,
      and say "that one's right" when a job held up on the real build.
- [ ] **Start the Carpentry apprentice program** when you want it: "I want to learn carpentry".

### Natural Momentum (2026-11-08: approved and built, DEC-0148)
- [ ] **Try it after the restart:** tell MIA what you did, in your own words ("I just put away the dishes and
      started a load of laundry"). A routine it names is counted (say "undo that" if it's wrong), and she may offer
      once to tick off a matching task or mission step, or to make something you keep doing a routine: "yes" does
      it. After a few good runs she'll know what usually starts them, and she holds her non-urgent messages while
      you're in the middle of one.

### Woodworking Studio and iOS (2026-11-08, from the engine session)
- [ ] **DEC-0147, the Woodworking Studio** (docs/WOODWORKING_STUDIO_PROPOSAL.md): approve the first version (actual lumber
      sizes, a design made of parts, cut list / materials / cost from the parts, 2D drawings, structural labels, a Studio
      page); woodworking-only or one shared Make space for the workshop, kitchen, garden and flock; 2D views first or
      wait for 3D; a print-ready page or a PDF.
- [ ] **iOS: which path?** (1) installable on your iPhone now (no Mac, no Apple account); (2) a macOS GitHub Actions
      job that runs MIA in the iOS Simulator and gives Claude screenshots (macOS minutes cost 10x); (3) a native app,
      which needs a Mac and an Apple Developer account ($99/yr). Claude recommends starting with (1).

### Restart MIA to activate this session's work (2026-11-08)
- [ ] **Restart MIA once.** It turns on everything from the 2026-11-08 engine session and the encryption at rest
      (DEC-0126): your three **standing directions** (consumer→producer, the café/workshop/tavern aesthetic, whimsy &
      tranquility) and the **whimsy seeds** that grow from them; **self-knowledge** (ask her "what are you?" / "what
      do you know about me?"); **Living Worlds** play; and the **Garage + properties** already imported from the life
      pack (seven assets with their maintenance tasks, three properties — all in your profile, nothing committed to
      the repo). Your memories and directions are written plain so MIA seals them under her own key on first run;
      then do the "Save MIA's recovery key" step below.
- [ ] **Commit the DEC-0133 files from your PC.** The new `email_*` modules under `core/`, the `watch_email` tool and
      their two tests are built and passing locally, but a cloud session can't commit them (the safety classifier
      holds them back). `git status` on your PC lists them as untracked — `git add` those five and commit.

### The new look: Nexus, rooms, themes and painting (2026-11-08, design session)
- [ ] **Look at the 3D Nexus and the Garage room on the PC** (DEC-0130): open MIA, the Nexus opens first in the
      Spatial look. Drag or use the arrows, go through the Garage portal. Tell Claude what feels off; the other
      areas' rooms are built one at a time after your look.
- [ ] **Pick your look** (DEC-0135/0136): Settings → Look: Spatial or Cards (by device by default), and a theme
      (Stark, Y2K, Cyberpunk, Glass, or your own from the Theme Studio, in the System area).
- [ ] **Install the image engine** (DEC-0140, `docs/ART_ENGINE.md`): ComfyUI and one SDXL model on the PC, then say
      "paint me a fantasy castle village for my background". Only tested against a stand-in so far.
- [ ] **Try Portal Pictures** once the image engine runs (DEC-0140): Settings → Portal Pictures, or the Nexus card's
      "Change its picture"; Paint One for an area, or say "paint a misty forest for the Plants portal".
- [ ] **Play a turn in Living Worlds** (DEC-0134 Phase 2): Recreation → Living Worlds, make a world, a campaign and
      your character, then "What do you do?" (or say "in my campaign I search the cartographer's desk"). Tell Claude
      how the narration reads on the local model.
- [ ] **Pull and run the full suite on the PC** after the design session's work (the cloud can't run the server
      and Qt tests).

### When you're ready
- [ ] **Fill MIA with your life (Zac, 2026-11-07, "later"):** a guided session at your PC, app by app, so she's
      as helpful as she can be. Claude asks before reading any folder; everything goes in through MIA's own actions
      (undoable, kept in your profile, never committed). Best first: Plaid for Money, then Garage, Calendar,
      Workout, Kitchen, Chickens, Freedom, People. Say "let's fill in MIA" to start.

### MIA across your technology (2026-11-08, docs/DEVICE_FABRIC_PROPOSAL.md)
- [ ] **DEC-0128:** approve MIA's device fabric — recognize, talk to, secure, and install herself onto your tech
      (Field Kit grown from USB/serial to the whole network). The read-only defensive half (network discovery +
      identify + security audit + a screen) can start on approval with no further decision. Then decide: inventory
      scope, how far into active testing and against which of your devices, Smart Home via Home Assistant or direct
      adapters, and whether the device inventory is sealed at rest (Claude proposes yes). Say "start the device
      fabric" to begin the defensive half.

### Selling MIA (2026-11-08, https://claude.ai/artifact/CXMdLtnXhy4XzUMAW4aLLR)
- [ ] **DEC-0127:** approve MIA becoming a product (reverses DEC-0119), then the price, launch platforms, bank
      linking, Tailscale or a relay, the payment provider, and a trademark search on "MIA". The plan's last section.

### Connecting your apps (2026-11-08, https://claude.ai/artifact/H8gYSX2rvneRMp5mgA4qFa)
- [ ] **Which apps first** (Google Sheets, QuickBooks, TurboTax, OwnerRez, Hostaway, Airbnb...), one-time imports or
      some on a schedule, and which is the source of truth for rental income. Read the audit doc's plan.

### Security (2026-11-08, docs/SECURITY.md)
- [ ] **Encrypt this PC's drive.** It isn't encrypted (Windows 11 Home, checked 2026-11-08). Settings → Privacy &
      security → Device encryption, if it's there; if not, Windows 11 Pro's BitLocker or VeraCrypt (free). The
      biggest single protection for everything MIA keeps.
- [ ] **Save MIA's recovery key** (DEC-0126, built 2026-11-08). After restarting MIA once, on the PC: Settings →
      Sign-ins → Your Files on This Computer → Show the Recovery Key (your password), and put it in your password
      manager (not a file on this PC). Without it, a Windows reinstall or a new PC can't open your conversations,
      memories, notes, people and finances. Optional: `.venv\Scripts\python -m tools.data_key seal` seals the
      existing files now instead of at each one's next save.
- [ ] **Later, DEC-0126's open part:** an extra MIA passphrase on top of DPAPI, or not?

### Try it
- [ ] **Talk to MIA on the PC (2026-11-07):** restart MIA, open Talk (the orb, bottom right), press the mic, say
      something, press it again. The first time, nothing should ask about the microphone (MIA's own page is allowed);
      Windows may ask once. Tell Claude if she didn't hear you.
- [ ] **The desktop opens on the web (DEC-0124):** close both copies of MIA that are running and start it once. It
      should open straight onto MIA's web screens, full size. Ctrl+Shift+C (or the header's "Main screen") switches to
      the classic screens and back; Power, Toolbox, The Lab and Field Kit open from the Apps page ("Open on this PC").
      Tell Claude anything that looks wrong or missing.
- [ ] **The phone app, no test header, keeps your place (2026-11-07):** install the new build (GitHub's Android build
      from this push, or `app-debug.apk` built on the PC: `adb install -r android-phone/app/build/outputs/apk/debug/app-debug.apk`).
      It's called "MIA" now, with no title bar; lock the phone on any page with Talk open and come back: same page,
      same scroll, Talk still open with what you'd typed.
- [ ] **Your email for receipts (DEC-0120):** in Gmail, make an app password (Google Account, Security, 2-Step
      Verification, App passwords; don't paste it into a chat). Then MIA's Inbox page, Email section: imap.gmail.com,
      your address, the app password, your journal passphrase, "everyday mailbox" ticked, Save. She looks back 30 days
      for receipts and orders and leaves your mail untouched. Emailed receipts file themselves (DEC-0121): the
      Inbox's "Filed By MIA From Your Email" list shows each with Undo, or say "undo the Kroger receipt". Tell Claude
      which stores' receipts read badly.
- [ ] **MIA's browser (DEC-0117, `docs/BROWSER.md`):** restart MIA, then say "open the county website" (or any
      site): her own Edge window opens. Try "read the page", "click ...", and something that commits (she should
      ask first, and a "yes" after she names the button presses it). Then teach her one real task: open where it
      starts, "learn this: <name>", do it in her window, "done", and "do <name>" twice. Tell Claude what she got
      wrong (the new Browser page in the sidebar shows what's waiting, with its screenshot, and your taught tasks).
      One choice for you in the doc's Known limits: whether typing in ordinary fields should be limited to
      words you said that turn.

- [ ] **Plans in the Library (DEC-0118):** after the restart, ask "what do I need to build a 10 by 12 shed?" or
      "how many bags of concrete for a 10 by 12 slab?"; open Knowledge in the sidebar for the Plans shelf; save
      plan PDFs and drawings into `reference_library\plans\` (subfolders like `woodworking\` become the kind) and
      she finds them. Free ones: ask "where can I get free plans?". Tell Claude which structures to add next
      (a chicken coop? a lean-to? shelving?).
- [ ] **Her humor:** say "be funnier" or "no more jokes for now" and see her change; tell Claude how often feels right.

- [ ] **The Claude Design brief** ("MIA: Screens and Flows for Claude Design", a Claude Doc:
      https://claude.ai/artifact/3R3ZjAWg4JzV1yE6dXK515): read it, answer its five open questions, then hand it to
      Claude Design for round one (the frame plus six screens).

### Decisions
- [ ] **The audit and organization (a Claude Doc, "MIA: Audit and Organization of Everything Built":
      https://claude.ai/artifact/56xyaTxEQThT1vrYh484Ay):** seven areas, eight hubs, four screen tiers, the ways to
      use each feature, six flows. Four decisions at its end: the areas, the merges (above all the game layer into one
      Progress hub), missed missions, and building step 1 now.
- [ ] **Taught procedures (DEC-0123 PROPOSED, `docs/PROCEDURES_PROPOSAL.md`):** your "universal skill system" idea as
      one engine (browser routines and workflows folded in). Four questions at its end: the direction, the name,
      phase 1 first, and which desktop apps you'd want her to learn.
- [x] **Child-account code (DEC-0119):** leave it (Zac, 2026-11-07); it only reaches MIA's prompts for a child.
- [ ] **The Highest Self (H-0089 → H-0090, DEC-0114 PROPOSED):** read H-0090 (one page) and decide its four questions (the foundation, faith for everyone's MIA, three new modes, keep the tuned prompt); and rate MIA's twelve new answers in `pc-check/conversation-highest-self-tune2.md` (faith, meaning, vulnerability, grand plans, dependency, free will, flattery): your ratings decide the next tuning.
- [x] **Experience Maturity (DEC-0113):** approved by Zac 2026-11-07, amended: the design canvas is the reference, no concept round.
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
- [ ] **Your history is sealed now; its older lines aren't yet** (2026-11-08, DEC-0126): MIA's history repeated the
      names your sealed stores keep (people, places, policies, goals), so each new line of `life_events.jsonl` is now
      sealed as it's written. Lines from before today are still plain. Sealing them means rewriting the file once,
      every line kept (the history is otherwise never rewritten): close MIA, then
      `.venv\Scripts\python -m tools.data_key seal --history` (it refuses while she's open). Or say if you'd
      rather the history stayed plain.
- [ ] **Start MIA's own search engine (SearXNG)** so she can look things up online when you ask (DEC-0053, your
      pick 2026-10-31; `core/online_lookup.py` built 2026-11-08, T-0017): Docker Desktop, then the one command and
      the JSON setting in `docs/ONLINE_LOOKUP.md`. Only search words leave the PC; no account, no tracking.
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
- [ ] **Start guitar (DEC-0111)** after the restart: say "I want to learn guitar" (and why, and how much time you
      have: "20 minutes a day, 4 days a week"). She sets the plan and this week's homework (in Missions). Then
      "give me my next guitar lesson", "show me the G chord shape", "I practiced guitar for 20 minutes",
      "I did 22 chord changes in a minute, E minor to A minor", "how's my guitar going?". For the checks she
      hears (tuning, clean chords), open the Guitar page (`/web/guitar.html`) on the phone or the PC and press
      Record. If she says a chord you played cleanly isn't clean, tell Claude: her ear was tuned on synthetic
      strings and real ones may need adjusting.
- [ ] **Anything else you want to learn (DEC-0112):** "I want to learn to weld" (or bake bread, or speak Spanish):
      she drafts a plan from what her specialists know, describes it, and starts it only when you say "start it".
      Each path gets its own homework in Missions; "how am I doing on welding?" for its stats.
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

- [ ] **Portal art batches 2-4** (H-0096/H-0097): the remaining areas' portal pictures for `web/img/portals/`
      (batch 1 is in and confirmed, H-0098). And a review of the Nexus room and the Garage room's look.
- [ ] **Handoff numbers collided again:** two H-0098s (claude's batch-1 confirmation and Muse's walipini call).
      Next free number: check `docs/HANDOFFS/README.md` before writing one.

- [ ] **Experience Maturity (H-0088):** read the audit, the identity draft and the design-system spec; after round one,
      shortlist the concepts with Claude, set the values for the design system's proposals and the orb's seven
      states, then turn `docs/design/applications/workout.md` (a brief) into Workout's spec.
- [ ] **Handoff numbers:** H-0080 and H-0081 were each used twice (`H-0080_chatgpt-...`, `H-0081_chatgpt-...`). The
      next free number is **H-0087** (H-0086 is Muse's savings-hound reply).
- [ ] **Screens waiting on your look**: working screens are built on the shared frame (2026-11-07), formatting
      only: `web/operating.html` (the Operating Journal), `web/play.html` (games and training load), `web/news.html`
      (Good News Radio), `web/council.html` (owner only), and 2026-11-06 `web/kept.html` (promises, decisions,
      ideas and goals set aside, DEC-0054; its demo shows sample notes). Still engine-only: the Night School panel's
      look, and the education transcript (if DEC-0102 is approved).

## ChatGPT (Chat)

- [x] **Round one of visual concepts:** skipped by Zac (DEC-0113 amendment); the canvas replaces it.
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
