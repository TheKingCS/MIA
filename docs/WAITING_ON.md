# Waiting On

*The running list of what Zac and the other agents need to do (Zac, 2026-11-06: "keep a running track of what other
agents or I need to do and I will address those later"). Claude adds to it as work needs someone, and strikes an
item when it's done. Newest first within each person. Read with `docs/NEXT_SESSION.md`.*

*Last updated: 2026-11-24*

## Zac

### The hub and the engineer (2026-11-24, `docs/future/HUB_AND_ENGINEER_PLAN.md`)

0zq. [ ] **May MIA find what's on your home network?** Read-only, your network only: she'd list your devices by make
   and model (the device fabric's first layer, DEC-0128, still a proposal). Nothing is changed or controlled.
   Recommended: yes, read-only first.
0zr. [ ] **Your printer and devices.** Which 3D printer, smart plugs, ESP32 or Tasmota devices you have or will buy.
   Recommended: a printer with a local connection (Klipper or Moonraker, OctoPrint, or a Bambu in LAN mode), and
   devices that talk MQTT or ESPHome on your network, not through a company's cloud.
0zs. [ ] **The order.** Recommended: finding and listening to your devices first (read-only), the 3D printer
   second, writing firmware and designing printable parts third, circuit boards after. The other way: design tools
   first, before connecting anything.
0zt. [ ] **Unfinished work lost (my mistake, 2026-11-24).** An unfinished change from 2026-11-08 (transfers between
   your own accounts kept as transfers, DEC-0042) sat uncommitted in budget_manager.py and plaid_manager.py; a
   careless restore of mine wiped it. The plaid half is recovered (in the private audit folder); the budget half has
   to be redone. Plaid is on hold anyway; nothing you use broke. Nothing to do unless you want it rebuilt now.

### The homestead's brain (2026-11-24, `docs/future/SMART_AG_PLAN.md`)

0zn. [ ] **What's in your orchard?** MIA has nothing for an orchard yet, and it's being built now. Tell her which
   trees you have or plan (apples, peaches, pears...), roughly how many, and where, and she'll date the year's work
   (pruning, spraying, thinning, harvest) from your frost dates.
0zo. [ ] **Your water and power hardware.** Which well pump, tank or cistern, inverter or charge controller you
   have or will buy. Their makes decide how she can read them; open, local ones (Modbus, MQTT, a local web page)
   are recommended over cloud-only ones.
0zp. [ ] **The order of the homestead work.** Recommended: MIA's side now (the orchard, whole-property water and
   power, a homestead morning sheet: it needs nothing), then the greenhouse taking her directions in simulation
   (DEC-0185, the node's command interface), then the 55-gallon pilot when you're ready to buy parts (about $263),
   then outdoor irrigation, the well and house power. The other way: the pilot hardware first.

### One intelligence (2026-11-24, `docs/future/UNIFIED_INTELLIGENCE.md`)

0zl. [ ] **When you confirm a plan, may MIA record what it touches?** "I'm planning to build a greenhouse" now gets
   a picture of everything it touches: the build's materials and cost against what's on hand, your money and
   freedom date, garden plans, water, power, time, goals and research. The next step is for a *confirmed* plan to
   keep those connections (the greenhouse uses these materials, depends on water at the site, supports your growing
   goal), so your money, garden, materials and week answers start counting it. Recommended: yes, worked out from the
   plan itself and undone with the plan. The other choice is that you state each connection yourself.
0zm. [ ] **Should MIA bring up the picture on her own?** Today you get it when you say you're planning something.
   She could also offer it when a plan comes up in conversation without your asking, once, through the usual
   pacing. Recommended: offer once per project, never repeat it.

### From the Jarvis brainstorm (2026-11-23, `docs/future/JARVIS_BRAINSTORM.md`)
0zk. [ ] **Read the safety floor's new phrases** (`core/safety_floor.py`, 2026-11-24): besides "kill myself" and
   the like, MIA now answers with the fixed crisis text (numbers for your country, then a listening mode) when
   someone says things like "nobody would miss me", "what's the point of living", "I wish I'd never been born",
   even after "I'm not suicidal, but...". Ordinary talk ("what's the point of this meeting", "nobody would miss
   me at the potluck") is kept out, and each phrase is tested both ways. Two things for you: any phrase you'd add
   or take out; and whether the crisis reply should end by saying "say 'back to normal' when you want me to
   look things up again" (today the listening mode lasts until you say it or start a new chat).
0zj. [ ] **May a workflow work the homestead's equipment?** (brainstorm 7.2) Today MIA only reads the greenhouse
   and aquaponics system's snapshots; she can't switch anything there. A workflow step like "when the tank is low,
   run the fill pump" would be a new path from MIA into real pumps and vents. Claude's recommendation: not yet; first
   let a workflow *suggest* the homestead action as a card you press in the homestead's own screen, and only later,
   if you want, let it act within limits the homestead itself enforces.
0zi. [ ] **Which model, after reading the comparison** (DEC-0291): `pc-check/model-compare.md` on the PC has your
   Intelligence Benchmark answered by five models side by side. By MIA's own checks qwen2.5:14b (today's) and
   qwen3:14b tied; the bigger ones were slower and no better. Say "keep it" or "switch to qwen3"; nothing changes
   until you do.
0zh. [ ] **Let Windows run libzim again**: since 2026-11-23 Windows' Application Control (Smart App Control) blocks
   the libzim library MIA uses to read her offline library packs (Kiwix). Until it's allowed she can't search those
   packs on the PC (the rest of MIA is fine). Windows Security, App and browser control, shows the block. If it's
   Smart App Control, it has no allow-one-file setting, and once turned off it can't be turned back on without
   reinstalling Windows, so don't flip it in a hurry: Claude can look for another way with you at the PC.
   Checked 2026-11-24: Smart App Control is On. The ways round it, for you to choose (Claude won't test one
   without your say-so, since each gets past a Windows security setting): (1) turn Smart App Control off, which
   can't be undone without reinstalling Windows; (2) run her library on the Linux side (WSL or MIA OS), where
   it isn't blocked, and let Windows MIA ask it; (3) a reader written in plain Python: it still needs a zstd
   decompressor, a compiled library Smart App Control would likely block the same way; (4) leave the library to
   MIA OS and the phone for now. Claude's recommendation: (2), or (4) until MIA OS is on the new PC.
0zg. [x] (Zac, 2026-11-23: all four hobbies, the picture of him, test a bigger model, the evening wrap: DEC-0289 to
   DEC-0292. Then the last two: event triggers with email waiting for his yes, DEC-0293; habit routines offered once,
   DEC-0294. Nothing from the brainstorm waits on him now.)
   **Pick from the brainstorm** (or say "go in your order"): 30-odd ideas for a smarter, more aware MIA. Three
   need you: which hobbies get a companion first (3.3); may she build a "picture of you" page you can correct (1.3);
   try a bigger local model on your PC, a 10 to 20 GB download (1.5). Claude keeps building the ones that need no
   decision meanwhile (the weather against your garden and flock is in).

### From the Windows backlog (2026-11-22)
0ze. [x] (Zac, 2026-11-23: yes; DEC-0288, built as the Daylight theme) **Q-115: may a Light theme use darker shades of the meaning colours?** A light theme (dark words on light
   panels) is the last piece of WP-06. Green "done", amber "needs you" and red "wrong" are tuned for MIA's dark
   glass; on white, amber words are hard to read. A rule (DEC-0136) says no theme may change them. The choice: let
   a light theme use darker shades of the same three colours (same meaning, still checked for readability by
   code), or keep MIA dark-only. Claude's recommendation: yes, darker shades, with Muse's eye on the look.
0zf. [ ] **Choose where the second backup copy goes** (WP-09): Settings, Backups, "Second copy of the nightly
   backup": a folder on your external drive (like E:\MIA Backups). Until then the nightly backup is only on the PC.
   (Not the 512 GB USB stick: that one is for Fedora and MIA OS, Zac 2026-11-22.)

### From Fable's review of 2026-11-20
0zc. [x] (Zac, 2026-11-23: never by itself; DEC-0287, and MIA now says when one waits) **Q-114: should MIA OS ever restart your PC by itself to finish an update?** As built now it never does: an
   update is downloaded at night and goes in the next time *you* restart or shut down (a snapshot of your files is
   taken first). The other choice is a restart at night when the PC is idle; but your disk asks for its PIN at every
   start, so the PC would sit at that prompt, with MIA off, until you typed it. Claude's recommendation: keep it as
   built (never by itself), and have MIA tell you when an update is waiting for a restart.
0zd. [ ] **At install day (MV-01), two things to check that the VM couldn't:** the login screen offers MIA first
   without you choosing it, and MIA's window draws properly on your graphics card. Both are on the roadmap's FW-03
   note. And run `mia-disk-enrol finish` only after a restart you opened with your PIN.

### From Prompt 21 (2026-11-18)
0zb. [ ] **Look at your backups folder** ("MIA Backups" in your home folder): Claude's test runs on 2026-11-18 wrote seven
   backups dated Nov 23 to 29 there (now moved out). Backup rotation counted them as newest, so a backup from Nov 16 or
   17, if there was one, may be gone; Nov 15 and Nov 18 are there. Tonight's backup runs as usual. Nothing to do unless
   you wanted those two days.
0za. [ ] **The envelope** (your yes to Q-111): write MIA's recovery key on paper (run `python -m tools.data_key recovery` yourself in a terminal in
   the MIA folder; never paste it into a chat, not even to Claude), seal it in an envelope with your important papers, and tell the person you trust where it is. When MIA
   OS is installed, its disk's printed recovery key goes in the same envelope.
0z. [x] ~~**Three questions**~~ (answered 2026-11-18: yes to all) (Q-111 to Q-113, `docs/mia_os/MIA_LIVING_SYSTEM_GAP_ANALYSIS.md` §9): someone you trust
   able to open MIA's data if something happened to you (a sealed envelope you keep); removing copies on your phone
   of four files that should have stayed on the PC; building the living system work alongside the OS work.

### From Fable's review (2026-11-18)
0x. [x] ~~**Things that now work differently, from the review's fixes.**~~ (Zac, 2026-11-18: "Go with your
   recommendations": all kept.) Say if you want any of them back:
   - **Approve From Now On** is offered only for routine entries in your records (logging, adding, marking done).
     Changing a setting, anything in her browser, a connection, a skill, the lab, or anything that removes or
     forgets something always asks.
   - **Approving by voice:** a card that reaches outside MIA or can't be undone needs your press on the screen.
     "Approve 2" means the second card she just read to you.
   - **"Undo my change"** (one of her own code changes) and **starting a team** by voice now leave a card for
     your yes instead of running.
   - **Erase** (what she noted about your apps) is for good: no copy is kept, so it can't be undone.
   - **Web pages are noted as "a web page"**, not by their title, because a private window can't be told from an
     ordinary one. Tell Claude if you want page titles kept (a switch for it isn't on the Settings screen yet).
   - **Her own code changes** go in on Claude's pass only for proposals Night School makes from now on; the ones
     already waiting need your press.
   - **Floor joists:** the span table is shorter (a 12 ft span now gives 2x10, not 2x8). Check any floor or deck
     plan made before today against the span table for your lumber before building from it.
   - **A specialist's answer** leads with the doubt when a second model doubts it, and says when Claude hasn't
     inspected the model that planned it.
0y. [x] ~~**One question:**~~ (answered 2026-11-18, as recommended: yes) while you've said "stop everything", MIA
   still restarts Ollama if it has stopped, so your own questions can be answered.

### From Prompt 17 (2026-11-18)
0w. [x] ~~**Six questions**~~ (answered 2026-11-18: "Yes to all") (Q-105 to Q-110, `docs/mia_os/MIA_OS_FINAL_OPEN_QUESTIONS_AND_APPROVALS.md`): a narrower
   first version with later releases checking the rest; a PIN at each start for the encrypted disk; trying Windows
   from the USB enclosure first; a licence for the repository; starting FW-01 (a reproducible image build, in a VM);
   the 53 proposed decisions as a batch.
0v. [ ] **When the 4 TB drive and the enclosure come** (HW-02, before anything is installed): put the old drive in
   the enclosure and try starting Windows from it (about 15 minutes). If it won't start, that's fine: the fallback is
   the drive back in the slot.

### From the Opus night (2026-11-17 into the 18th)
0u. [ ] **Buy when convenient** (Q-96, Q-97): an external USB drive for the second backup copy (about $60 for 2 TB) and a UPS (about $150 to $250).
0t. [ ] **The laptop's model name** (Q-89): tell Claude its make and model (or open MIA on it and say "check this computer"), so the plan knows how much it can do itself.
0s. [x] ~~**Prompt 11, the look: four questions**~~ (answered 2026-11-18) (Q-83 to Q-86, `docs/mia_os/MIA_OS_VISUAL_OPEN_QUESTIONS.md`): the
   Theme Studio starting from one of your pictures; quiet interface sounds (listening, "needs you", errors on; done
   and message chimes off; alarms always); a Light theme now, Graffiti and Neon later; Zeta Astralis tried on a small
   Android phone in a forearm mount first. Then say go for Prompt 12 (every device).
0r. [ ] **Try the second monitor** (Q-80): restart MIA with both monitors on. The ambient view (clock, day, weather,
   what's due, music, what MIA is doing) should open on the monitor MIA's window isn't on; turn that monitor off and
   on and it should go and come back. `gui.ambient_screen: false` in config turns it off.
0q. [ ] **Look at the new indicator** (Q-44): the sidebar says "Noting your active app" while MIA notes which program
   is in front of you. Settings › MIA has the switch and Erase. Ask "what am I working on?".
0p. [ ] **Try by voice:** "what's waiting for me?", "approve it from now on", "what do I have about the greenhouse?",
   "what did you change in yourself?", "what can't you change?".

### From the Fable run (2026-11-16)
0n. [x] ~~**MIA OS architecture: five questions**~~ (answered 2026-11-16) (Q-47 to Q-51, `docs/mia_os/MIA_OS_CORE_ARCHITECTURE_OPEN_QUESTIONS.md` section 1). In short: is the PC's base Fedora's KDE desktop as an image built from the repository (Ubuntu the fallback)? Should MIA's own screen run on KDE's window manager so ordinary programs can open beside her? May the tests be run? Should system changes always ask your password? Should MIA keep running when you're signed out?
0m. [ ] **The graphics card test** (part of Q-49): start the PC from a Fedora 45 KDE USB stick, install nothing, and run MIA's three models to measure their speed. About an hour; a Claude session can talk you through it. It decides Fedora or Ubuntu. **2026-11-22: the stick is here** (Zac: "That USB is for you, it will be for the linux fedora thing and then eventually will house the whole program/OS we build"; the 512 GB removable drive). The Fedora 45 KDE live image is downloaded and checked (Fedora's signed checksum) in Downloads, "MIA OS". Left for you: writing it to the stick needs your Windows yes (an administrator prompt): with Fedora Media Writer, or with Ventoy so the stick keeps room for MIA OS's files later; then start the PC from it.
0l. [ ] **Prompt 23, Universal Intelligence: four questions** (Q-43 to Q-46, `docs/mia_os/MIA_OS_UNIVERSAL_INTELLIGENCE_REVIEW.md` section 13): what the shelf may keep; whether MIA may note which program is in front of you (recommended: not yet); whose browsing Recall may search; when the work runs.

### Start here (2026-11-08 evening: the short list, in order; everything else is below)
0h. [x] ~~Navigation: review the eight-destination architecture~~ (answered 2026-11-11; built: the eight, the glasses' three screens, the Nexus as Living Worlds).
0k. [ ] **Set your town for the weather, and sort your orders and quotes** (2026-11-11): on the Dashboard, type your town in the Weather card (or say "my town is ..."). In Finances › Businesses, if it says some orders and quotes have no business yet, open the link and pick each one's business (Edit → Business). Then look at a business's own dashboard, and at Missions: your upkeep due this week shows there as scheduled missions.
0i. [ ] **Try the eight destinations** (2026-11-11): open MIA on the PC and the phone. It opens on the Dashboard; the sidebar has the eight; Home opens to Kitchen, Smart Devices, Homestead, Recreation, Personal Tools and Learning; Living Worlds (Home › Recreation) opens the Nexus with your stories. On the glasses: the orb, the menu (the eight), the Nexus (just before the log). Say if anything sits in the wrong place.
0j. [ ] **Look inside Toolbox, Trade Master, the Lab and Field Kit** (2026-11-11) and say where each belongs. Toolbox: four calculators (Ohm's law, a unit converter, board feet, concrete volume). Trade Master: any repair or job walked through step by step. The Lab: readings you log over time, charted (and other apps' series, read only). Field Kit: what's plugged into the PC, network checks (a hash's kind, a subnet) and your script library. For now they sit in Garage, Garage, Smart Devices and Smart Devices.
0g. [ ] **Try the music** (2026-11-10): start a song in Music, then open other apps, on the PC window and in the phone app. It should keep playing, with a small bar on each page. Known limits: closing the PC window ends MIA and the song; on the phone it plays with the screen off but not after the app is swiped away; Good News Radio has its own player and can play over a song. The phone part was only compiled, never run on a phone.
0f. [ ] **Conversation mode: read the plan and decide five things** (2026-11-10): `docs/CONVERSATION_MODE_PLAN.md`, section 8: keep the small speech recognizer or add Whisper on the PC; let Claude add a streamed call to `core/llm_manager.py`; which device after the web page; how long a silent call stays open; whether a spoken yes approves a routine action.
0e. [ ] **Organization: read the review and decide** (2026-11-10): `docs/ORGANIZATION_REVIEW.md`, section 6: eight rooms or another cut (replaces DEC-0129's fifteen); one home per app; Kitchen's own portal (DEC-0130); a page that is MIA; which pages to merge; The Council and Made By MIA (a door, or out); the rooms' names.
0d. [ ] **How she talks: choose from five proposals, and try three things** (2026-11-10): `docs/CONVERSATION_REVIEW.md`, section 8. To try: ask her about herself ("do you have a greenhouse app?", "how do you work with my glasses?") on the PC and through the glasses; press Summary on a chat; save a chat to Files.
0c. [ ] **Read the audit and say what to start** (2026-11-10): on the PC in `audit/` (three files; not in git). Eight decisions are yours, listed in section 8 of `AUDIT_2026-11-10.md`; the first is whether this repository, which is public today, should be. Tiers 1 to 3 are done as far as they go without you; what's left needs your decisions: 1.1 (public or private), 2.1 (measure a larger model; it runs over your records), 2.5 (a quiet window for the engine move), 2.6, 2.10, 2.11 (where the lab's tests may run), 3.7. Restoring a backup now finishes when MIA restarts, and a second copy of MIA says so instead of starting.
0b. [ ] **The glasses' camera for Look** (2026-11-09): built by the design session (GlassesCamera.kt, mwdat-camera 1.0.1) and passing CI's emulator check. Left for you: in Meta's Wearables Developer Center, approve Camera for the MIA app, then on the phone Settings → Glasses → Let MIA Use the Glasses' Camera, and say "what am I looking at?" through the glasses.

0. [x] **Let Claude commit again**: done 2026-11-09 (Zac made .claude/settings.local.json); the held work was committed, merged with the design session's, and pushed.
0. [x] **Push the homestead merge**: pushed 2026-11-09 with the rest.
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
   **Plaid deferred (Zac, 2026-11-17):** "I will not be connecting Plaid until this is much further along and secure."
7. [ ] **Encrypt the PC's drive** (Windows 11 Home has Device Encryption: details under Security).

### Zac's feedback on the window, 2026-11-17 (to fix, Claude)
- [x] **The window is too tall** (fixed 2026-11-17: it opens maximized, the Dashboard uses two columns on wide screens and fits, the sidebar tightens on short screens): the sidebar and the page run past the bottom of the screen, so he has to scroll to
      reach the bottom. Everything should fit his screen.
- [x] **The page is crammed to one side with empty space beside it**: use the width. (Fixed the same day.)
- [x] **Navigation isn't the portals any more** (built the same day: each area opens a dashboard of cards, one per subcategory and app, each with what needs you there; the room is one button away): clicking an area (Home, Garage, Finances...) opens that area's own
      dashboard, holding all its subcategories and their dashboards.
- [ ] **No USB stick yet** for the graphics card test from Fedora (`os/poc/README.md`); it waits.

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
