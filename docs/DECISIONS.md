# MIA Decisions

*The decision log (format and rules: `docs/COLLABORATION.md`). Only Zac
approves. A decision is never deleted: it becomes SUPERSEDED or
REJECTED. Seeded 2026-10-05 from decisions already made and recorded in
`docs/ROADMAP.md`, `docs/NEXT_SESSION.md` and
`docs/ENGINE_PHASE1_PLAN.md`.*

### DEC-0001: MIA is built for anyone; each person's data is their own
- Status: IMPLEMENTED
- Proposed by: claude, 2026-10-01 · Approved by: zac, 2026-10-01
- Decision: MIA is perfected for personal use but designed for any
  person or household. People sign in with an email; nothing is shared
  unless they join a household with a member's approval. Child accounts
  are looked after by a parent.
- Why: hundreds of different people may use MIA.
- Related: `core/personal_data.py`, `core/household_manager.py`,
  `core/child_accounts.py`

### DEC-0002: Real personal data never goes in the repo
- Status: IMPLEMENTED
- Proposed by: claude, 2026-10-05 · Reviewed by: chatgpt · Approved by: zac, 2026-10-05
- Decision: no real personal data in code, specs, mock-ups, prompts,
  tests or seed files. It enters through MIA itself (or a local,
  git-ignored `data/seed.json`) and stays on the device. Shared material
  uses placeholders.
- Why: MIA should know a person's life because they told it, not
  because a developer hardcoded it; git history is permanent.
- Related: DEC-0001, `docs/ENGINE_PHASE1_PLAN.md` §4a

### DEC-0003: Extend and connect what exists; don't rebuild from the mock-up
- Status: APPROVED
- Proposed by: claude, 2026-10-05 · Reviewed by: chatgpt · Approved by: zac, 2026-10-05
- Decision: the repo already holds the engine. Work connects and
  extends it, and keeps the existing architecture unless there's a real
  limitation.
- Why: the gap was between the engine and the designed interface, not
  missing features.
- Related: DEC-0005, `docs/ENGINE_PHASE1_PLAN.md`

### DEC-0004: Facts in code; the language model only phrases and proposes
- Status: IMPLEMENTED
- Proposed by: zac/claude, 2026-09 · Approved by: zac
- Decision: totals, dates, permissions, XP, scheduling, validation and
  safety are deterministic code. The model reasons over structured
  memory and is never the memory. Crisis handling never depends on it.
- Why: a small local model is unreliable at facts; safety must not
  depend on it.
- Related: `core/safety_floor.py`, CLAUDE.md "Known intentional simplifications"

### DEC-0005: Every surface consumes MIA through one read model
- Status: IMPLEMENTED
- Proposed by: chatgpt, 2026-10-05 · Reviewed by: claude · Approved by: zac, 2026-10-05
- Decision: the desktop, phone, Android app, design mock-ups, glasses,
  voice and future AR all read the same Life State
  (`/api/state`, `docs/schema/life_state.schema.json`). None of them is
  a separate implementation of MIA.
- Why: one coherent MIA; no screen invents its own interpretation.
- Related: DEC-0007, `core/context_assembler.py`, `docs/HANDOFFS/H-0003_claude-to-muse_where-mia-is.md`

### DEC-0006: History sits beside the stores (no event-sourcing rewrite)
- Status: IMPLEMENTED
- Proposed by: claude, 2026-10-05 · Reviewed by: chatgpt · Approved by: zac, 2026-10-05
- Decision: the existing stores stay the source of truth for the
  current state; `core/life_events.py` is an append-only history beside
  them; `core/links.py` holds relationships by reference, never as a
  copy.
- Why: rewriting ~30 working stores and their tests for theoretical
  event sourcing would risk everything for little gain.
- Related: DEC-0003, `docs/ENGINE_PHASE1_PLAN.md` §8

### DEC-0007: Status taxonomy on every capability
- Status: IMPLEMENTED
- Proposed by: muse (kickoff spec), 2026-10-05 · Approved by: zac, 2026-10-05
- Decision: every section, service and export is labeled REAL, DERIVED,
  SIMULATED, STATIC or PLANNED. No UI implies a capability the engine
  doesn't have.
- Why: honesty about what MIA can really do.
- Related: DEC-0005, the schema

### DEC-0008: The 10-question guardrail for every proposal
- Status: APPROVED
- Proposed by: chatgpt, 2026-10-05 · Approved by: zac, 2026-10-05
- Decision: every new screen or feature is run through the ten
  questions in `docs/COLLABORATION.md` before it's built.
- Why: stops design and engine drifting apart.
- Related: `docs/ENGINE_PHASE1_PLAN.md` §9

### DEC-0009: Read, propose, approve: no silent actions
- Status: IMPLEMENTED
- Proposed by: zac/claude · Approved by: zac
- Decision: MIA proposes and the person decides. Email is only drafted
  and is sent only when a person presses Send. Assistant changes are
  undoable. Unprompted messages go through the communication gate
  (daily limit, no repeats, "why did you tell me that?").
- Why: trust; the person stays in charge of their life.
- Related: `core/communication_gate.py`, `core/undo_log.py`, `core/email_drafts.py`

### DEC-0010: The AIs collaborate through shared files in the repo, not directly
- Status: APPROVED
- Proposed by: chatgpt and zac, 2026-10-05 · Reviewed by: claude · Approved by: zac, 2026-10-05
- Decision: a persistent shared project memory (this file,
  `COLLABORATION.md`, `CURRENT_STATE.md`, `QUESTIONS.md`, `HANDOFFS/`)
  replaces Zac relaying messages. No AI-to-AI connection. Start with
  files in the repo; a website on top is a later option (Q-0006).
- Why: simpler, auditable, works with what each AI can already reach.
- Related: DEC-0011

### DEC-0011: Make the MIA repo public so ChatGPT can read it
- Status: IMPLEMENTED
- Proposed by: zac, 2026-10-05 · Reviewed by: claude (privacy audit, 2026-10-05) · Approved by: zac, 2026-10-05 (repo is public)
- Decision: switch `github.com/TheKingCS/MIA` from private to public.
- Why: ChatGPT can only read public repos.
- Audit (claude, all 373 commits): no API keys, tokens, passwords,
  addresses, account or loan details, and no personal data files were
  ever committed. What would become public: all code and docs; the first
  names Zac and Faith and the household truck model in tests, comments
  and the roadmap; Zac's personal email as the author of about 50
  commits. There is no LICENSE file, which means "all rights reserved"
  (people can read it but not reuse it).
- Waiting on: Zac (Q-0005).

### DEC-0012: MIA's interface becomes one web front end, built by Muse
- Status: APPROVED (option A, with chatgpt's refinement)
- Proposed by: claude, 2026-10-05 · Reviewed by: chatgpt, 2026-10-05 (approved with refinement); muse (Q-0007 pending) · Approved by: zac, 2026-10-05 (forwarded chatgpt's review with its green light)
- Refinement (chatgpt): not one identical layout everywhere, but **one MIA
  component system with surface-specific compositions**. Desktop, phone
  and glasses share components, state, actions and visual language, and
  each arranges them for its surface.
- Decision: (A, recommended) a single HTML/CSS/JS front end in `web/`,
  written by Muse, served by MIA's own local server and shown in the
  desktop's PySide6 window (QtWebEngine), on the phone and, later, on the
  glasses. Claude provides the APIs. The Qt screens keep working until
  each one is replaced. (B) Keep the Qt UI: Muse designs, Claude
  implements every screen in Qt.
- Why: the front end lags because Muse's designs have to be
  hand-translated into Qt by Claude; one web front end removes that step
  and serves every surface.
- Risks: memory and performance on the devices MIA runs on (the new
  computer and the phone first, DEC-0015); a second language in the
  codebase.
- Related: H-0005, DEC-0005, DEC-0013

### DEC-0013: Phase 2 is "Experience": the front end catches up
- Status: APPROVED
- Proposed by: claude, 2026-10-05 · Reviewed by: chatgpt, 2026-10-05 · Approved by: zac, 2026-10-05
- Order (chatgpt's review): web foundation → action API → live updates
  → performance check (on the new computer and the phone, DEC-0015; it
  read "Pi 5 validation" before) → Home and presence → Talk → domain screens one at
  a time → glasses cards, with MIA's reasoning alongside. Prove one
  complete vertical slice (engine → `/api/state` → web Home → real data →
  an action → updated state) on the real devices **before** any broad
  migration: the new computer and the phone (amended by DEC-0015; it
  said "the Pi 5").
- The action API is a first-class contract: **Propose → Approve →
  Execute → Record → Undo**. The front end holds no business logic: it
  shows Life State and proposed actions, and the engine executes and
  owns safety, history and undo.
- Decision: the next phase is, in order: the foundation (`web/`, the
  action API, live updates, the Pi check); Home and MIA's presence;
  Talk; then the domain screens one at a time; glasses cards after
  Q-0003. Phase 2 reasoning ("opportunities") runs alongside. Every step
  goes through the hub as a handoff.
- Why: the engine is ahead; what MIA needs now is to feel like MIA.
- Related: H-0005, DEC-0012

### DEC-0014: The Witness Principle (companion proactivity)
- Status: APPROVED
- Proposed by: muse, 2026-10-05 · Approved by: zac, 2026-10-05 (via muse)
- Decision: MIA spends her proactivity on progression, not reporting. Earned progression (level-ups, quest completions, streaks, unlocked milestones) is celebrated loudly and game-like; everything else stays under the communication gate — calm, quiet, useful-or-silent.
- Extended by: zac, 2026-10-05 (via muse, from chatgpt's recommendation in H-0011): **MIA does not punish the user for being human.** Full form: "MIA witnesses what happened, celebrates earned progress, helps the user recover from setbacks, and does not punish the user for being human." Design guardrail for missions, streaks, XP, notifications, proactivity, and gamification: if a feature makes MIA feel like a source of guilt or pressure rather than a supportive second brain, reconsider it.
- Why: progress feels real because something notices it. Loud-about-progression is the companion's job; loud-about-everything is a notification firehose. This is the rule behind Q-0004's presence states and the game layer's celebration moments.
- Related: Q-0009, Q-0004, H-0005

### DEC-0015: Where MIA runs, in order: the new computer, the phone, the glasses, then Pi devices
- Status: APPROVED
- Proposed by: zac, 2026-10-05 · Approved by: zac, 2026-10-05
- Decision: MIA's devices, by priority: (1) **Zac's new computer**, the
  main home of MIA's engine and desktop; (2) **his phone**; (3) **Meta
  Display glasses**, soon; (4) **his own Raspberry Pi devices**,
  eventually. The Pi is not the primary target. Older docs that say
  "target: Raspberry Pi 5 kiosk" describe that later step, not now.
- Why: "the pi is one of the least relevant devices right now" (Zac).
- Consequences: Phase 2's performance check runs on the new computer and
  the phone, not the Pi. The phone composition of the web front end
  moves up, right after the desktop Home. The glasses are next after
  that, so Q-0003 becomes urgent. Pi and kiosk work (the installer's
  `--kiosk`, the AI HAT) stays supported but parked.
- Related: DEC-0012, DEC-0013 (amended below), Q-0003, Q-0010

### DEC-0016: The glasses: a Web App first, then the Android app for voice
- Status: APPROVED (zac, 2026-10-05, in chat with claude)
- Proposed by: claude, 2026-10-05 · Reviewed by: chatgpt, 2026-10-05 (see H-0010), muse, 2026-10-05 (see H-0012) · Approval: zac
- Decision: the first glasses surface is a Meta Ray-Ban Display **Web
  App**: Muse's `web/` components in a 600 × 600 composition, served by
  MIA through **Tailscale Funnel** (the platform needs a public HTTPS
  URL), with a revocable glasses-only device link, a narrow scope
  (glasses cards, child-safe actions), a rate limit, and Funnel off
  unless switched on. **Later**, MIA's Android app adds the native
  Device Access Toolkit for voice (the glasses' microphone).
- Why: the web path is the same front end as every other surface
  (DEC-0012) and the fastest to build; the native path is more private
  and adds the mic, so it follows.
- Risk: MIA's API becomes reachable from the internet while Funnel is
  on, which is why the scope is narrow.
- Related: H-0008, Q-0003, Q-0011, DEC-0012, DEC-0015
- Also approved with it (zac, 2026-10-05): a public **GitHub Pages
  preview** of `web/` that only ever shows the placeholder example
  (`.github/workflows/pages.yml`), so the screens can be seen on a phone
  and, later, tried on the glasses with nothing private exposed.
- Timing (Q-0011): Zac has no glasses yet and MIA isn't installed on the
  PC, so the Funnel link waits; the Pages preview comes first.

### DEC-0017: The web front end becomes all of MIA, function first, in the concept's look
- Status: APPROVED (zac, 2026-10-06, in chat with claude)
- Proposed by: claude, 2026-10-06, at zac's request ("use the original program, all of MIA's functionality, the repo and the concept pictures to build a functional MIA tied to the back end that looks like the concepts") · Review: muse, chatgpt · Approval: zac
- Decision:
  1. **Parity is the goal.** Every Qt screen and everything it can do
     gets a web screen that does the same, styled like the concept
     pictures (`docs/vision_assets/user_os_concept.png` and Zac's
     others). `docs/WEB_PARITY.md` lists every screen, tab and
     operation (from the 55 screens in `docs/design_handoff/screens/`)
     with three checkboxes: engine API, working web screen, matches the
     concept. "Lacking" becomes a number we can see shrink.
  2. **The engine exposes all of MIA, not a summary (claude).** Life
     State stays the summary for Home, the phone and the glasses. Each
     module also gets a full API: everything its Qt screen reads, and
     every operation it can do (add, edit, delete, log, complete), as
     action kinds through Propose → Approve → Execute → Record → Undo.
     This replaces DEC-0013's "if it isn't in Life State, ask": the rule
     becomes "if the Qt screen can do it, the API can".
  3. **Function first, then the look.** Claude builds each module's
     working web screen on Muse's tokens and components, so nothing
     waits on design. Muse owns the shell (top bar, sidebar, search,
     level and XP, the orb), the component system, and restyles each
     working screen to match the concepts, checking it against them.
     **The concept set** is the ten pictures Zac gave Muse: Home,
     Greenhouse, Garage, Kitchen, Workout, Real Estate, Missions, Skills,
     one asset's page (a mower), and an overview. They stay out of this
     public repo because they show real addresses and names (DEC-0002).
     The pattern they share, which every module screen follows:
     - **Every module page:**
       - a photo header with the module's name, tagline and the weather;
       - three tiles: Tracked, Needs Attention (overdue), Next Up;
       - a red Needs Attention list;
       - asset cards, each with its own tasks and due/overdue chips;
       - Related Missions;
       - tabs for the module's sections (Kitchen: Recipes, Pantry,
         Grocery List, Meal Log, Suggestions; Workout: Exercises,
         Templates, Log Session, History, Progress; Real Estate:
         Properties, Maintenance, Missions).
     - **An asset page:** Overview, Maintenance, Missions, Documents,
       Parts and History tabs; quick stats; gauges; current tasks; asset
       details; documents.
     - **Home:** a greeting; Today's Focus as a checklist; a quote;
       quick actions (Quick Add, Voice, Calendar, Journal, MIA
       Assistant); a sidebar of modules with level and XP at the bottom.
     - **Missions:** XP and streaks, plus MIA-assigned missions.
     - **Skills:** overall level, achievements, the next honest step,
       categories with tiers, and locked skills.
     - **Kitchen:** recipes unlocked by missions.
     Almost all of it is data MIA already has (maintenance, kitchen,
     workout, real estate, missions, skills, documents). The web just
     couldn't reach it.
  4. **Home matches the concept's desktop dashboard** (Today, Upcoming,
     Assets, XP and levels, quick actions, search), with the orb kept as
     MIA's presence. On the phone, the concept's mobile app. This
     supersedes the "one due item, never a module list" Home (Q-0004)
     for the desktop and phone; the glasses keep the one-card rule.
  5. **The Qt app stays the working MIA on the PC** until the web
     version reaches parity for a module; then that module's Qt screen
     can retire. Nothing is lost on the way.
  6. **Order:** the shell and Home dashboard; Money (bills, income,
     expenses, debts, summary); Garage and Maintenance (assets, tasks,
     the concept's inspection checklist); Missions, Skills and
     Character; Calendar, Notes, Inbox, Talk; Kitchen, Workout, Real
     estate; then the rest of the 38 modules.
- Why: the web screens look thin because the contract given to them
  was thin: one summary (`/api/state`) and five action kinds, with a
  rule against showing anything else. That is an engine-side gap, not a
  design one. Muse can't wire what the API doesn't expose.
- Risk: it's a lot of screens. Parity per module keeps each step
  shippable, and the Qt app covers anything not yet moved.
- Related: DEC-0012, DEC-0013 (amended), DEC-0015, Q-0004, H-0013, H-0016
- Amended (zac, 2026-10-06, in chat with claude): **Home is MIA
  herself** (her face and a chat with her, Muse's presence page), not the
  dashboard; the concept dashboard is its own Dashboard page. Navigation
  is one ⋯ button that opens every choice (phones, and Home at any size);
  desktop module pages keep the concept's sidebar.

### DEC-0018: The mobile concept set is the target look; Claude builds it
- Status: APPROVED (zac, 2026-10-06, in chat with claude). **Its target look is superseded by DEC-0023 (2026-10-15, the Stark engineering interface); the concept's layouts stay.**
- Proposed by: claude (options), zac chose, 2026-10-06 · Review: muse, chatgpt
- Decision:
  1. **The target:** the mobile concept set ChatGPT made for Zac
     (2026-10-06): Home, Apps, Greenhouse, Garage, Kitchen, Workout, Real
     Estate, Finances, Missions, Skills, MIA Assistant and the menu
     drawer. It is described in `docs/design/MOBILE_CONCEPT.md`; the
     picture itself stays out of the public repo because it shows a real
     name and addresses (DEC-0002).
  2. **Home is the concept's Home** ("Good morning", the weather and
     date, Today's Focus, the day's saying, quick actions, level and
     XP). This supersedes the DEC-0017 amendment that made Home MIA's
     face. Chatting with MIA is the **MIA Assistant** screen, one tap
     away from Home and from the bottom bar.
  3. **Navigation is the concept's bottom bar** on the phone (Home,
     Apps, Dashboard, More; More opens the menu drawer). The desktop
     keeps the sidebar. *Amended by zac, 2026-10-06: no More button
     (every app is on the Apps page), so the bar is Home, Apps,
     Dashboard; and no saying card on Home (the Dashboard keeps it).*
  4. **Claude builds the look** directly from the picture, on top of
     the working screens (every button, form and action stays). Muse
     reviews and polishes. This changes DEC-0017's split for this pass.
  5. **Photos come from ChatGPT:** the images listed in
     `docs/design/IMAGE_REQUESTS.md` (no names, addresses or personal
     details), uploaded to `web/img/` and shipped inside MIA so they
     work offline. Until one is there, its screen shows a plain scenic
     background.
- Why: Zac: "I like the direction this is going but it feels very off of
  concept still… make exactly this basically while maintaining
  functionality of all capabilities and features and modules."
- Related: DEC-0012, DEC-0017, H-0016, H-0018, H-0019

### DEC-0019: The phone is MIA's home; a computer becomes an optional helper
- Status: APPROVED
- Proposed by: claude, 2026-10-06 (at zac's request) · Reviewed by: (chatgpt, Q-0016, still welcome) · Approved by: zac, 2026-10-07 (Q-0015: "go with your recommendations")
- Decision: MIA's engine runs **on the phone, inside the MIA app**, so
  someone with only a phone, or a phone and Meta's Display glasses, has
  all of MIA, offline and private. A computer (or later a Pi) becomes an
  optional helper that adds a bigger model, bank sync, email, sensors
  and household sync. **Android first**, iPhone later. First step: a
  short spike proving the Python engine and the web screens run in an
  Android app (Chaquopy), before committing. Plan and phases:
  `docs/PHONE_FIRST_PLAN.md`.
- Why: Zac (2026-10-06): MIA should be sellable, so convenience and
  accessibility matter, and the destination is an AR gamified-life HUD
  that "has to run on the phone and connect to glasses." Meta's glasses
  already pair through the phone; the web front end (DEC-0012/0017)
  already runs anywhere; the engine already runs without the desktop.
- Changes: extends DEC-0015 (device order) for anyone who isn't Zac; the
  computer stays first for Zac's own setup until Phase 2 ships.
- iPhone (zac, 2026-10-07): he's on Android now and moving to an iPhone
  later, so every choice in the Android work must keep the iPhone path
  open (the engine stays plain Python; CPython supports iOS officially
  since 3.13, PEP 730; the phone shell stays thin), and iPhone follows
  right after phone-only Android works (plan Phase 5 moves up).
- Related: DEC-0001, DEC-0002, DEC-0012, DEC-0015, DEC-0016, DEC-0017,
  Q-0003, Q-0015, Q-0016


### DEC-0020: Eat, train and see it working: Kitchen + Workout + Missions, with a built-in food table
- Status: APPROVED
- Proposed by: claude, 2026-10-12 (at zac's request), with muse (H-0026) · Approved by: zac, 2026-10-12 ("Lets go with your recommendations")
- Decision: build `docs/KITCHEN_FITNESS_PLAN.md` with Muse's H-0026 spec:
  a per-person fitness plan (targets, training rotation, skill tree with
  timed holds, milestones, meals), weigh-ins and their trend, nutrition
  per day, meal plans and prep with a shopping list from the plan, and
  missions generated from the plan (training, skill, protein, lunch,
  prep) on the existing mission path (complete, +1, undo; streaks pause,
  never shame, DEC-0014). Completions can be said in plain words and are
  handled by MIA's code, no model needed. **Nutrition facts come from a
  food table built into MIA** (USDA FoodData Central, public domain),
  computed from a recipe's ingredients, offline; typed values win.
- Why: Zac wants meal plans, prep, workouts and nutrition tied to his
  goals, completed as daily and weekly missions, and to see whether it's
  working. Values stay on the device (DEC-0002); the repo holds the
  schema, the logic and the public food table.
- Related: DEC-0002, DEC-0014, DEC-0017, DEC-0019, H-0022, H-0026


### DEC-0021: The fitness screens: one My plan, plain words log at once, a page for each recipe
- Status: APPROVED
- Proposed by: claude and muse (H-0028), 2026-10-12; the recipe page by zac, 2026-10-14 · Approved by: zac, 2026-10-14 ("Go with your recommendations")
- Decision: (1) **One "My plan" screen** (`web/plan.html`) with two doors,
  Kitchen and Workout, instead of a plan editor in each. (2) **Plain-word
  completions log at once** ("lunch done", "workout complete"), and MIA
  says what it logged with "undo that"; no confirm card first (this
  overrides H-0028's confirm-sheet pattern for spoken and typed commands;
  buttons on screens still propose and confirm, as everywhere). (3) **Each
  meal and recipe card opens the recipe's own page** (`web/recipe.html`):
  the recipe, its nutrition, what the house has, the steps, and two
  buttons: **Schedule meal** (a day and a meal) and **Add to grocery
  list**, which adds only what isn't in the pantry or already on the list.
- Why: one place for the plan means it can't disagree with itself; saying
  "done" should be instant, and undo keeps it safe (the logs are the
  truth, DEC-0020); the recipe is where the cooking and the shopping meet.
- Related: DEC-0014, DEC-0018, DEC-0020, H-0028, H-0029


### DEC-0022: Capable offline, supercharged online: three levels, picked automatically
- Status: APPROVED
- Proposed by: claude, 2026-10-14 (from zac's idea) · Approved by: zac, 2026-10-15 ("Go with your recommendation")
- Decision: MIA works fully on the phone alone and gets stronger when she
  can reach more, choosing by herself and saying which level she's on:
  **1. phone only, offline** (everything works; code answers what it
  can, the phone's 1.5B model the rest); **2. home computer reachable**
  (same Wi-Fi, or anywhere through a private link like Tailscale): Talk
  uses the PC's bigger model and falls back to the phone's mid-
  conversation, then heavy jobs (voice, OCR, textbooks, email, bank
  sync), then two-way sync of the person's data; **3. internet**: web
  lookups (weather, recipes, labels) later. **A cloud AI stays off**
  unless the person switches it on (some of their words would leave
  their devices, DEC-0001/0002), and it always says when it's used.
- Build order: the PC's bigger model for Talk first, then heavy jobs,
  then sync (the hardest piece; it's Phase 4 of docs/PHONE_FIRST_PLAN.md
  moved up). **Waiting on:** Zac's PC specs (graphics card, memory, is it
  on most of the day), which decide the model size.
- Amended (zac, 2026-10-15): **reachable from anywhere, from the start.**
  From work Wi-Fi (or mobile data) the phone reaches the home PC the
  way you'd remote into a Pi, through Tailscale (MIA's existing private
  link: `core/phone_server.py`, `docs/PHONE_VOICE_SETUP.md`), not the
  public internet; same Wi-Fi is just the faster path. Nothing is opened
  to the internet; the PC still needs a password to sign in.
- Related: DEC-0001, DEC-0002, DEC-0015, DEC-0019, docs/PHONE_FIRST_PLAN.md


- Model picked (claude, 2026-10-19, from Zac's PC: MIA's 213 test
  questions on the Radeon RX 7900 XTX): **qwen2.5:14b**, 95.8% right, a
  typical answer in 2.8 s, 13 s to load, all on the graphics card.
  qwen2.5:32b got 98.1% but takes 9.0 s an answer and 61 s to load, and
  doesn't fit wholly on the card (92%). 2.3 points aren't worth three
  times the wait on every turn (the rule: the faster one when within
  3 points). Most of 14b's misses are questions it answered without a
  tool ("add a note", "what do I need to do", a new recipe, chores):
  routing hints and code answers can close those.
### DEC-0023: MIA's look becomes a Stark-inspired engineering interface
- Status: APPROVED
- Proposed by: zac, 2026-10-15 (his brief, in the session) · Approved by: zac, 2026-10-15
- Decision: reskin the whole web front end (`web/`, phone and desktop)
  as an original personal-technology interface inspired by Tony Stark's
  workshop, the Iron Man HUD and engineering software: near-black and
  graphite layered surfaces, **one electric-cyan accent** for active
  and selected states, cool white text, amber only for attention, muted
  green for healthy and done, red only for real errors and destructive
  actions; precise rectangular panels with small radii and fine lines,
  small technical labels, tabular numbers, a consistent line-icon set
  instead of emoji, restrained purposeful motion (reduced motion
  respected). All from shared tokens (`web/tokens.css` is the theme).
  Function, data, routes, progression rules and the glasses page's own
  layout are unchanged; nothing is mocked.
- Changes: **supersedes DEC-0018's target look** (the mobile concept set:
  per-screen neon colors and warm photo heroes). The concept's layout
  ideas stay (status strip, needs-attention, segmented tabs, bottom bar);
  their styling becomes the Stark language. Muse reviews and polishes
  it (H-0034), as with DEC-0018.
- Related: DEC-0012, DEC-0014, DEC-0016, DEC-0017, DEC-0018, H-0034


### DEC-0024: The glasses: favorites are the pinned cards, every app has a quick action menu
- Status: APPROVED
- Proposed by: zac, 2026-10-16 (in chat with claude); muse (H-0041, H-0043) · Approved by: zac, 2026-10-16 (H-0044, and in chat)
- Decision: the glasses boot to MIA's orb; a swipe flips through app
  cards; selecting one opens its quick action menu (H-0042). **The cards
  are the apps the person favorites** (the same star as the Apps page),
  in the order they starred them; every other app waits behind an "All
  apps" card; with no favorites, every app shows. Each menu ends with
  Pin to / Unpin from glasses, which sets that star. A change from the
  glasses shows MIA's sentence and needs a second select (two-gesture
  approve); only quick, non-destructive kinds (`GLASSES_KINDS` in
  `core/glasses.py`); money and the inbox stay read-only there.
- Changes: H-0044's "most used first" ordering is settled by Zac's own
  words in chat: **favorites, in the order starred**, no usage tracking.
- Amended (zac, 2026-10-16): **layout.** Home is the orb alone (idle animation; Saturn-like rings while listening), no chat bar or text anywhere on it; every screen fits one fixed 600×600 composition with no scrolling; navigation is two moves, move and select (every list ends with Back); the Missions card shows the active mission, its objectives and a Select mission button (H-0046).
- Amended (zac, 2026-10-16): **Missions right after the orb** (before pins); the Today card leaves the glasses and its due items move into Missions → Select Mission, sortable **Past Due / Due Today / Due Soon**, the format for every app with dated things (equipment, Rentals, the Calendar). A Calendar app filled from everything with a date, in the app and on the glasses. Kitchen on the glasses: Recipes (with photos), Today's Meal Plan, My Pantry, Grocery List. **Title Case** for buttons and headers everywhere (H-0048).
- Related: DEC-0016, DEC-0023, H-0041, H-0042, H-0043, H-0044, H-0045, H-0046, H-0048

### DEC-0025: Three apps for things you own: Garage, Real Estate, Greenhouse
- Status: APPROVED
- Proposed by: claude, 2026-10-16 (Zac asked whether Property and Maintenance were redundant) · Approved by: zac, 2026-10-16 ("Perfect lets cut those out")
- Decision: **Maintenance** and **Property** are no longer apps. **Garage**
  holds vehicles, power equipment, tools and anything else; **Real Estate**
  holds every building you own (your home included) with its money side,
  plus the house and its appliances and their upkeep (Home & Appliances,
  Past Due, Due Today, Due Soon); **Greenhouse** holds plants. All upkeep
  still shows in the Calendar and in Missions → Select Mission. No data
  changes: assets and tasks are where they were and show under their new app
  (`core/web_equipment.py` SCOPES). On the desktop the Maintenance module
  stays loaded (Garage and Greenhouse open it to add and edit things) but is
  listed nowhere (`core/web_surfaces.py` RETIRED); the old web pages redirect.
- Related: DEC-0017, DEC-0024, H-0049

### DEC-0026: No workout templates; no Set Aside for missions
- Status: APPROVED
- Proposed by: zac, 2026-10-16 · Approved by: zac, 2026-10-16
- Decision: **Workout templates are removed** from the web and the desktop
  ("you can remove templates from the desktop too. No user has used them
  yet"); a session is logged freeform, the plan's training rotation is the
  one way to say what a day's workout is, and Lifts is renamed **Personal
  Bests** (skill bests plus lift PRs). **Missions have no Set Aside** ("Set
  Aside should not be a thing in the missions app"): no Give Up button and
  no tab; Delete removes a mission. Missions tabs show their names only.
- Related: DEC-0014, DEC-0017

### DEC-0027: Home replaces the Dashboard
- Status: APPROVED
- Proposed by: zac, 2026-10-16 · Approved by: zac, 2026-10-16
- Decision: "we can delete the dashboard section all together because they
  have all the same info basically." Home shows the greeting, Today's Focus,
  Upcoming and the level card, with no quick buttons and no date; Apps
  reaches everything else. Selecting MIA on Home opens the chat with her.
  The Dashboard app is retired everywhere (`RETIRED` in core/web_surfaces.py);
  its data endpoint keeps feeding Home.
- Related: DEC-0017, DEC-0025

### DEC-0028: The game layer, built in order
- Status: APPROVED
- Proposed by: claude, 2026-10-17 (Zac asked what would make MIA feel like living in a video game) · Approved by: zac, 2026-10-17 ("I love all of your ideas so lets take note of them and work on them in your recommended order")
- Decision: the ideas in `docs/GAME_LAYER.md` are the game layer's plan.
  Build order: **1. Reward Shop** (spend credits on rewards you set),
  **2. Gear condition bars** (assets as equipment), **3. Boss battles**
  (big goals with an HP bar, starting with debts), **4. Real character
  stats** (from real data, ready for a smart watch); then buffs, the world
  map, questlines and seasons, the Chronicle, crafting, party/guild,
  sound, the watch health HUD and location quests as Zac picks them.
  Guardrails: never punishing (DEC-0014), health data stays on your own
  devices, no slot-machine patterns.
- Related: DEC-0014, DEC-0022, DEC-0024


### DEC-0029: Take Claude's Project ALICE picks
- Status: APPROVED
- Proposed by: claude, 2026-10-17 (`docs/future/PROJECT_ALICE_REVIEW.md`, Q-0017) · Approved by: zac, 2026-10-17 ("I want to take your recommended features from Alice")
- Decision: build, in order: (1) **What I Used**: MIA picks memories by
  relevance and shows the ones she used under each answer, each one
  fixable or forgettable; (3) **remembering at the right moment**
  through the communication gate; (2) **one conversation everywhere**
  (desktop, phone, glasses); (7) **one personality guide** for every
  word MIA writes. Using the PC's model from the phone stays DEC-0022.
  Vision ("what am I looking at") and hands-free glasses voice wait on
  the glasses (`docs/EXPANSION_AUDIT.md` §2: the glasses' web apps have no
  camera; photo capture goes through Meta's Device Access Toolkit in the
  phone app, explicit capture only).
- Related: DEC-0014, DEC-0022

### DEC-0030: Expansion phases (homestead businesses, memory vault, contextual AI)
- Status: APPROVED
- Proposed by: claude, 2026-10-17, from ChatGPT's "MIA Expansion Audit" handoff (`docs/EXPANSION_AUDIT.md`) · Approved by: zac, 2026-10-17 ("Lets also sign off on that 6 phase dev plan")
- Decision: phases in order: A. contextual AI (DEC-0029, then DEC-0022);
  B. crafting recipes end to end on the existing workshop stores
  (recipe → inventory check → shopping list → receive → build → photos →
  actual profit); C. quotes, customers and orders, portfolio; D. grow lab
  (crop batches, greenhouse readings with your own safe ranges, warn
  only, experiments); E. memory vault on the PC after the phone↔PC link
  (verify before ever offering to remove from the phone, never auto-
  delete); F. glasses camera via the Device Access Toolkit. A and B start
  now (A approved, B is the handoff's suggested first demonstration).
- Related: DEC-0022, DEC-0028, DEC-0029

### DEC-0031: Show-off mode runs on your own MIA, private things hidden
- Status: APPROVED
- Proposed by: zac, 2026-10-17 ("MIA show off for my friends") · Approved by: zac, 2026-10-17 ("We will build it for my real profile")
- Decision: "show off for my friends" starts a scripted, narrated tour of
  MIA's abilities on the person's **real** profile. For the tour, money,
  the journal, memories, health and people's details are hidden on every
  screen it opens (and anything Talk would say about them). Next / Back /
  Stop at every step; never an LLM-written script. Notes:
  `docs/future/SHOW_OFF_MODE.md`.
- Related: DEC-0014, DEC-0029

### DEC-0032: The rest of the game layer: questlines, kitchen blueprints, world map, party, sound, location quests
- Status: APPROVED
- Proposed by: claude, 2026-10-17 ("What's next?" list) · Approved by: zac, 2026-10-17 ("Lets start and 1 and build 1-6")
- Decision: build DEC-0028's ideas 6, 7, 9 (kitchen half), 10, 11 and 13.
  How Claude built them (Zac can change any of these):
  questlines are chains of missions with no countdowns, and a started one
  stays yours after its season; the world map clears ~2 km tiles from
  places you really reached (trip arrivals, finished trips, photo GPS,
  "I'm Here"), never from planned ones; the leaderboard is opt-in per
  person and counts wins only (never money, never misses); sounds are on
  by default and MIA's spoken lines are off by default; location is
  only checked on the device, only while MIA is open, only after the
  person switches it on, and arriving asks before doing anything.
  Notes: `docs/GAME_LAYER.md`.
- Related: DEC-0014, DEC-0028

### DEC-0033: A Security app for home cameras, local network only
- Status: APPROVED
- Proposed by: zac, 2026-10-18 ("an app for Security or Smart Home where i can monitor camera feeds") · Approved by: zac, 2026-10-18 (no cameras yet; "Cameras first, no HA")
- Decision: a Security app (grown-ups only) shows home cameras live:
  a still picture from the camera's own address where the brand has one,
  else one frame at a time from its RTSP stream through ffmpeg. MIA only
  ever talks to addresses inside the home network; camera passwords stay
  on the device and are never shown again or put in an action's record.
  Cameras are bought to fit: local-stream brands (Reolink first), not
  cloud-only ones. Lights, locks and the thermostat come later through a
  local Home Assistant. Notes: `docs/SECURITY_CAMERAS.md`.
  Amended 2026-10-18 (Zac: "the cameras … stay on the wifi that the pc
  is connected to and then still be able to remotely access it all from
  the phone"): the PC owns the cameras; a phone linked to it (DEC-0022's
  link, Tailscale when away) shows them through the PC, and can add,
  change and remove them there.
- Related: DEC-0015, DEC-0022

### DEC-0034: The insurance check-up
- Status: APPROVED
- Proposed by: zac, 2026-10-18 (`docs/future/IDEAS.md` #1: "compare my insurance and help me save with a better plan") · Approved by: zac, 2026-10-19 ("then do 5")
- Decision: an Insurance app (grown-ups only, household data): your
  policies with their premium, renewal date, deductible and coverage
  (typed in, or read from the policy's PDF or a photo, for you to check);
  what's worth a look, said as questions (a renewal coming, a price that
  rose, full coverage on an older car, a low deductible, no bundle); a
  heads-up about 45 days before each renewal through the communication
  gate; quote requests MIA drafts for you to send; the quotes you get back
  compared line by line against what you have, so a cheaper quote that
  covers less says so; switching as a mission (no gap in coverage) and the
  saving recorded as a money win. MIA never sends, never fills in an
  insurer's website, never pulls prices from anywhere, and isn't a
  licensed agent: it compares what you collect and you decide.
- Related: core/insurance.py, core/insurance_actions.py, web/insurance.*,
  `docs/future/IDEAS.md`

### DEC-0035: Passwords: a vault only your master password opens
- Status: APPROVED
- Proposed by: zac, 2026-10-20 ("a password/login manager as a feature for MIA too for all my different login details") · Approved by: zac, 2026-10-20 (the same request)
- Decision: a Passwords app (grown-ups only, the person's own data) with
  its own master password, separate from the MIA sign-in. One random
  vault key, kept twice: sealed (AES-256-GCM) with a key made from the
  master password and with one made from a recovery code shown once
  (scrypt for both). Each login is encrypted on its own, title included.
  Unlocked only in memory, it locks itself after 5 minutes unused; wrong
  guesses make you wait longer each time. MIA's assistant never sees a
  password: no tool reads one, and none ever appear in an action's
  record, the history, the undo log, Life State, the glasses or the logs;
  a password leaves MIA only on Show or Copy, one at a time. Phone and PC
  sync it still encrypted, only when they hold the same vault. Import
  from Chrome, Edge, Firefox, Bitwarden, 1Password, LastPass; a strong-
  password generator; reused and weak passwords pointed out.
- Honest limits: home-built on standard parts (the `cryptography`
  library), not independently audited like Bitwarden or KeePass; no
  autofill in other apps yet (an Android autofill service is the next
  step). Forgetting both the master password and the recovery code
  loses the vault: by design, nobody can get in.
- Related: core/password_vault.py, web/passwords.*, server/app.py
  (`/api/passwords/*`), core/sync.py (`password_vault.json`)

### DEC-0036: Homestead goods: batches, freshness, market day, labels
- Status: APPROVED
- Proposed by: claude, 2026-10-21 (Zac: "the business side ... crafting recipes and inventory management for things like the woodworking business or the homestead bakery") · Approved by: zac, 2026-10-21 ("build the bakery and we will fix later if needed"; sells at a mix of stand, market and orders; Kentucky's home-based processor rules)
- Decision: the Workshop's recipes grow into anything the household
  makes in batches (hot honey, salve, sourdough), on the same loop and
  stores (Materials, Jobs, Products, Ledger), never a second system:
  a recipe says what one batch makes ("12 jars"); ingredients in kitchen
  units (g, cup, tsp...) convert to the unit the stock is kept in when
  they measure the same thing (weight to weight, volume to volume); cost
  per piece; each finished batch is stock with its made date and a
  sell-by (the recipe's shelf life), oldest sold first, leftovers tossed
  as a recorded loss; a market day (take goods, tap what sold on the
  phone, close the day: revenue, leftovers, profit, XP); labels printed
  from the person's own business name, address, statement, allergens and
  net amount, with the batch's date and the ingredients heaviest first.
  The concept (Zac, 2026-10-21) is an anime "system" running a homestead:
  MIA shows the resources a craft will use, from what to what, before
  you begin, and a sale's tally after.
- Honest limits: MIA prints what the person enters for their own rules
  and never says a product is legal to sell; it can't convert cups to
  pounds (no densities), it says so instead.
- Note (zac, 2026-10-21): the household's own goods stay within
  Kentucky's home-based processor rules: banana bread, cookies, breads,
  honey and the like (no infused honey or salves).
- Related: core/craft_recipes.py, core/units.py, core/craft_actions.py,
  core/web_craft.py, web/workshop.*, docs/HOMESTEAD_GOODS.md

### DEC-0037: Eggs, the greenhouse's harvests, wood goods and dry goods for sale
- Status: APPROVED
- Proposed by: claude, 2026-10-21 (`docs/future/IDEAS.md` #2-#5) · Approved by: zac, 2026-10-21 ("start working on chickens, microgreens and plant starts, small wood goods, and seasonings and spices / dry goods in jars")
- Decision: on homestead goods (DEC-0036), never beside it:
  - **Into stock** from anywhere that isn't a crafted batch (gathered,
    harvested, potted up), as a batch with its date and a cost each.
  - **Chickens**: a flock log (birds, eggs collected each day, feed
    bought, birds added or lost); lay rate, eggs a week and feed cost per
    dozen; **Carton** puts dozens into goods on hand at that cost, **For
    baking** puts eggs into Materials at what they cost, eaten at home is
    counted too. A web screen of its own (Chickens).
  - **The greenhouse's harvests**: a Grow Lab harvest (microgreens, the
    starts that are ready) goes into goods on hand, or into Materials
    when it's an ingredient (dried herbs for a blend).
  - **Wood goods and dry goods**: no new machinery; starter recipes to
    copy (cutting board, planter, spice and herb blends, mixes in a jar)
    that the person changes to their own.
- Honest limits: selling eggs and plants has its own rules; MIA keeps the
  person's notes and never says what's legal.
- Related: core/goods_actions.py, core/flock.py, core/grow_actions.py,
  core/goods_starters.py, web/flock.*, docs/HOMESTEAD_GOODS.md

### DEC-0038: Freedom: the way out, in numbers (Life Runway, slice E)
- Status: APPROVED
- Proposed by: zac, 2026-10-21 ("I need my finances monitored and a clear view of my daily/weekly/monthly progress in saving towards getting out of this factory ... a quick viewable display that helps me get through these shitty nights at work and even helps me estimate when I can reasonably work from home selling my homestead goods full time") · Approved by: zac, 2026-10-21 (the same request)
- Decision: a Freedom app (grown-ups only, the person's own plan): what a
  month of living needs (their number, else their spending's 3-month
  average), what the homestead earns a month (the business's profit,
  3-month average), the gap between them, and the freedom fund that
  covers the gap for a cushion of months plus the homestead builds still
  to pay for (Projects with a budget: greenhouse, coop, solar, root
  cellar). Saved so far (bank cash from Plaid, else their own number),
  the saving pace, and the estimated day it's reached; what moves the
  day (more saved a month, more homestead profit). Progress today, this
  week, this month. A shift readout (what tonight's shift buys: days of
  living, the step toward the fund). Their own reasons ("remember why",
  slice B) on the same screen. Every number says where it came from;
  the date is an estimate and says so.
- Honest limits: transfers between your own accounts can look like
  spending until the bank sync sorts them; the estimate assumes the last
  three months' pace continues; MIA isn't a financial adviser.
- Related: core/freedom.py, web/freedom.*, core/why_graph.py,
  core/homestead_costs.py, docs/COGNITIVE_EXTENSION_PROPOSAL.md (slice E)

### DEC-0039: MIA knows her own model (the intelligence spec's first slice)
- Status: APPROVED
- Proposed by: zac, 2026-10-21 (`docs/specs/INTELLIGENCE.md`; the phone answered "What AI model are you using?" with "I don't have that kind of technical information") · Approved by: zac, 2026-10-21 (the spec's own first vertical slice)
- Decision: which model answers is asked of the runtime (Ollama's
  /api/show, /api/ps, /api/version; llama.cpp's /props; the home
  computer's /api/model/info), each fact saying where it came from, and
  the Assistant answers it in code (`get_model_info`, a direct lookup),
  never from the model's guess.
- Related: core/model_registry.py, core/assistant_self_actions.py,
  server/app.py (/api/model/info), docs/INTELLIGENCE_AUDIT.md

### DEC-0040: Business OS, first increment: the obligations calendar
- Status: APPROVED
- Proposed by: claude, 2026-10-21 (`docs/BUSINESS_OS_AUDIT.md` section 7, from Zac's `docs/specs/BUSINESS_OS.md`) · Approved by: zac, 2026-10-21 ("Lets begin")
- Decision (if approved): one store for tax and compliance obligations
  (authority, what, entity or activity, period, due date, the rule and
  its official source with a verified date, status, proof, next action);
  reminders at 90/60/30/14/7 days, on the day and overdue, through the
  communication gate and on the Calendar; a Compliance screen. Starts
  empty; a starter list of obligations *to verify* is offered as
  unverified tasks with their official sources, never as confirmed law.
  Needs from Zac: the real addresses, how each activity is owned, and
  whether taxes are filed jointly.
- Related: docs/BUSINESS_OS_AUDIT.md, docs/specs/BUSINESS_OS.md

### DEC-0041: Intelligence, next increments: capability registry, then docs retrieval
- Status: APPROVED
- Proposed by: claude, 2026-10-21 (`docs/INTELLIGENCE_AUDIT.md` section 5) · Approved by: zac, 2026-10-21 ("Lets begin")
- Decision (if approved): a capability registry built from the code
  (apps, tools, action kinds, status and limits; a test fails when a
  feature has no entry) answering "what can you do?" / "can you…?"
  truthfully; then retrieval over MIA's own docs (decisions, current
  state, specs, guides) answering "how does X work?" with the passage
  and its file.
- Related: docs/INTELLIGENCE_AUDIT.md, docs/specs/INTELLIGENCE.md

### DEC-0042: Business OS, the rest of the plan
- Status: APPROVED
- Proposed by: claude, 2026-10-21 (`docs/BUSINESS_OS_AUDIT.md` section 7) · Approved by: zac, 2026-10-21 ("OK to both of those")
- Decision: after the obligations calendar, in order: transaction kinds
  and own-account transfers never counted as income, workshop sales
  matched to their deposit so they count once, edit history kept (P0-2);
  legal entities vs. activities (P0-3); then P1 (deductions with
  evidence and review states, receipt ↔ transaction matching, email
  notices, accountant exports), P2 and P3 as the audit lists, each
  increment tested before the next.
- Related: docs/BUSINESS_OS_AUDIT.md

### DEC-0043: Intelligence, the rest of the plan
- Status: APPROVED
- Proposed by: claude, 2026-10-21 (`docs/INTELLIGENCE_AUDIT.md` section 5) · Approved by: zac, 2026-10-21 ("OK to both of those")
- Decision: in order: code retrieval (symbols and docstrings, cited by
  file; never data/ or config/), "why did that fail?" from the log and
  the action history, multi-step turns (reads freely, changes only as
  proposals), and the dev workflow (MIA writes proposals for Claude;
  MIA never changes her own code).
- Related: docs/INTELLIGENCE_AUDIT.md

### DEC-0044: One system, not a collection of apps
- Status: PARTLY REVERSED by DEC-0045 (zac, 2026-10-24): the five-places frame, Presence as Home and the World/Path/System hubs are undone; context in every turn stays
- Proposed by: zac, 2026-10-21 (Chat's handoff, `docs/specs/UX_SYSTEM.md`: "MIA ... feels like a collection of apps instead of a second smarter and more organized consciousness") · Approved by: zac, 2026-10-21 (the same request)
- Decision: navigation by intent: Presence, Conversation, My Hero's
  Path, World, System, then the person's pinned apps (every app stays
  reachable through World); Presence synthesizes what matters now across
  everything, each item with why, whether it's a fact, a deadline or a
  suggestion, and its next useful action; then context in every turn,
  objectives across modules with proposed plans, and verification after
  every change (`docs/UX_SYSTEM_AUDIT.md` section 4). One engine; no
  device gets its own logic. MIA never claims awareness she doesn't have.
- Related: docs/UX_SYSTEM_AUDIT.md, docs/specs/UX_SYSTEM.md

### DEC-0045: The apps stay the layout; the smarts go into MIA
- Status: APPROVED
- Proposed by: zac, 2026-10-24 · Approved by: zac, 2026-10-24 ("I dont like how we tried to fix MIA from just being a collection of apps. It was better before and I think that the old form was better. I really just wanted to fix MIAs feel of being a smart AI capable of using all those apps without the user digging through everything and her being more intuitive")
- Decision: the frame goes back to how it was before DEC-0044: the
  sidebar of the person's apps, the phone's Home and Apps bar, Home with
  Today's Focus and Upcoming. The five places, Presence as Home and the
  World / My Hero's Path / System pages are removed. What stays, and
  where the work goes now, is MIA herself: every question carries the
  person's world (`core/presence.py` `context_lines`: their goal and
  why, active missions, what needs them now), she knows what she can do
  (DEC-0041), and she works the apps for the person by voice and in
  Talk so they don't have to dig. A change to the layout itself is
  Zac's call, asked first, never part of a handoff about something else.
- Related: DEC-0044, docs/UX_SYSTEM_AUDIT.md (kept as history)

### DEC-0046: MIA as Game Master, and work as a dungeon you loot
- Status: APPROVED
- Proposed by: zac, 2026-10-27 (MIA as "my personal kind of dungeon master for playing the game of life": turning real-life trouble, like coming in unstocked after another shift, into the game instead of the negative way of thinking about it) · Approved by: zac, 2026-10-27 ("Lets create it. Then i could treat work like a dungeon that I visit and loot every day to stack resources until I can advance to the next dungeon and track my resource gain with Plaid ... Overtime can be boss battles that gain me increased loot. We can do a projected loot thing based on my hourly pay and overtime pay too")
- Decision: **Game Master mode** in Talk ("GM this", "game master",
  "make it a game", or the fourth answer when MIA asks what kind of
  support someone wants): she says plainly that the trouble is real, then
  frames it as the game from facts built in code (`core/game_master.py`):
  the hard-mode modifier's game name, what clearing it earns, the day's
  run, the loot, the next dungeon. She offers one quest ("make it a
  quest" → a HARD mission with its reward). Other people are characters,
  never villains, never named; she never invents loot, XP or wins.
  **The Dungeon** (`core/work_dungeon.py`, `web/dungeon.html`): a job is a
  dungeon, a shift a run, cleared or planned; hard-mode modifiers (Bare
  Shelves, Thin Party, Supply Raid...) add XP and are kept as a plain
  dated record, nobody's name, for if the person ever raises it at work;
  loot is gross pay with overtime by the pay week, a run with overtime is
  a boss whose bonus is the overtime premium; projected loot (week,
  month, year at this pace); banked loot is the paychecks from the bank
  (Plaid imports, matched by the paycheck's words), which also teach the
  take-home share; the next dungeon is the Freedom plan. Personal store,
  never a child's (money). Non-punitive: a missed planned run costs
  nothing.
- Related: DEC-0028 (the game layer), DEC-0038 (Freedom), DEC-0014

### DEC-0047: How missions work (the loop, adventures, real-gain rewards)
- Status: APPROVED
- Proposed by: claude, 2026-10-27 (from Zac's loop / adventure idea) · Approved by: zac, 2026-10-27 ("Take note of all your suggestions because I like them all", and his answers to the six questions)
- Decision: the mission system in `docs/MISSION_SYSTEM.md`. Loop missions
  appear automatically from what recurs; adventures are proposed from the
  day's project (guild quests, ranks, rank-up trials). A mission completes
  by evidence, a tap, or telling MIA. Rewards are what's actually gained
  (the finished craft, the recipe unlocked, the pay), with XP, ranks and
  titles beside them. No cap on missions (unprompted messages still go
  through the gate). Sunday morning check-in: last week's recap and this
  week's planned missions. A missed loop day shows plainly as nothing
  earned and the week's share cleared, with nothing taken away. Also
  approved to build: pattern noticing, titles, an emergent class, New
  Game+, the Codex, rest as camp, party quests, quarterly seasons,
  cutscenes, rare finds from real milestones only.
- Related: DEC-0014, DEC-0028, DEC-0046, docs/MISSION_SYSTEM.md

### DEC-0048: User Sync, and a design audit before more features
- Status: APPROVED (to plan; not built)
- Proposed by: zac, 2026-10-27 · Approved by: zac, 2026-10-27
- Decision: (1) **User Sync** (`docs/USER_SYNC.md`): handing MIA to a new
  person starts a deep getting-to-know-you conversation that fills their
  loop, first missions, garage, kitchen, workouts and goals, each record
  confirmed; then MIA stays curious and surveys what's working, switching
  features on and off to suit them. The person signs in to confirm it's
  them; their data is their own. (2) **A design audit**: Zac, "I have
  just kind of thrown my every idea at you to build her brain but not
  really worried about the design and flow of utilizing MIA or the apps
  pages and layouts". Every function and page gets audited for how it's
  organized and laid out to be the most intuitive, easy to use and easy
  to read, and the organization is agreed with Zac (and Muse) before the
  changes; the layout of the apps stays his call (DEC-0045).
- Related: DEC-0045, DEC-0047, docs/USER_SYNC.md

### DEC-0049: The Fix-It Log, and three tiers of self-improvement
- Status: APPROVED
- Proposed by: zac, 2026-10-27 · Approved by: zac, 2026-10-27 ("Yes, build the failure log first and go with your recommendations")
- Decision: MIA records where she stumbles (`docs/FAILURE_LOG.md`):
  what the person says (corrections, reports, 👎) and what she can see
  (tool errors, the model down, no tool matched, the right tool offered
  but ignored, rephrasing, a quick undo, slow answers, broken pages);
  each person's own, never private turns, redacted. Grouped into
  ranked issues (Apps → Fix-It Log; "what's been going wrong?") and a
  fix report Claude reads on the PC. Tier 1: she learns phrasings
  herself only after the person says yes. Tier 2: settings are asked
  first. Tier 3: she never changes her own code; each issue becomes a
  failing test and bench case first, then the fix, full suite and bench
  green, Zac approving. Built before the design audit (DEC-0048) so the
  audit starts from real evidence.
- Related: DEC-0048, docs/FAILURE_LOG.md

### DEC-0050: She talks like a person; User Sync defaults; quiet hours; the EULA's facts
- Status: APPROVED
- Proposed by: claude, 2026-10-27 (`docs/BODY_AND_RELATIONSHIP_PLAN.md` section 9) · Approved by: zac, 2026-10-27 ("Yes, go ahead with the I don't know fix … Yes to 3 and 4 off until set")
- Decision: (1) Only a how-to or teach-me question about MIA is held to
  her own docs; everything else is answered as a person (the person's
  context, her own knowledge, the offline reference packs when they
  match), never "I don't know what to do": one short question or two
  concrete offers instead; facts about the person's data still come only
  from their data. Verified on the PC's model with
  `tests/live_model_check.py` (PERSON_CASES) before it's trusted.
  (2) User Sync: voice and typing, in chapters over days, and Zac can
  run it too. (3) Quiet hours: off until each person sets them. (4) The
  EULA: MIA will eventually be offered to others; the business structure
  isn't decided yet, so the draft uses placeholders for the licensor and
  governing law and gets a lawyer's review before release.
- Related: DEC-0048, DEC-0049, docs/BODY_AND_RELATIONSHIP_PLAN.md

### DEC-0051: Kokoro is MIA's voice on the computer
- Status: APPROVED
- Proposed by: claude, 2026-10-29 (her voice is Piper's low-quality models plus a robotic ring/chorus effect) · Approved by: zac, 2026-10-29 ("log the Kokoro voice decision. Lets get her voice sounding premium")
- Decision: the home computer speaks with Kokoro-82M (Apache-2.0, offline,
  24 kHz), run locally; nothing leaves the machine. Piper stays as the
  fallback (Kokoro missing or failing) and for the phone and the later
  Pi. The robotic voice effect is off by default for Kokoro. A custom
  voice made just for MIA is a later step, not this one.
- Related: core/voice_manager.py, core/voice_catalog.py

### DEC-0052: MIA's reasoning: one owner per fact, answers that combine, findings, continuity
- Status: PROPOSED
- Proposed by: claude, 2026-10-30 (`docs/REASONING_PLAN.md`), at zac's request ("the Brain is developing faster than the reasoning layer"; "it may need to call more than one tool to answer a more detailed question") · Approved by: —
- Decision (proposed): in order: (1) one owner per fact, in
  `core/ownership.py` with a test (pay → the Dungeon, the week's timing
  → the Loop, repeating chores → recurring missions); (2) answers that
  combine: question plans in code for the commonest detailed questions,
  then a tool loop for the rest (results back to the model, up to N
  more lookups, changes only as proposals, every number checked against
  what was looked up, a time budget; N from the PC's bench); (3)
  findings across apps, worked out in code with evidence refs, the
  first ten listed in the plan; (4) conversation state (what it's about,
  what's open, a running summary); (5) the companion layer on top.
  Facts and arithmetic stay in code; the model chooses and phrases.
- Related: DEC-0043, DEC-0050, docs/REASONING_PLAN.md, docs/INTELLIGENCE_AUDIT.md
