# MIA Decisions

*The decision log (format and rules: `docs/COLLABORATION.md`). Only Zac
approves. A decision is never deleted: it becomes SUPERSEDED or
REJECTED. Seeded 2026-10-05 from decisions already made and recorded in
`docs/ROADMAP.md`, `docs/NEXT_SESSION.md` and
`docs/ENGINE_PHASE1_PLAN.md`.*

### DEC-0001: MIA is built for anyone; each person's data is their own
- Status: IMPLEMENTED; "for anyone" superseded by DEC-0115 (2026-11-07): MIA is for Zac and his household
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
  audit starts from real evidence. (Amended by DEC-0058, 2026-10-30:
  tier 3 now reads "she never changes production without Zac's
  approval"; changes are made and tested in the isolated lab.)
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
- Status: APPROVED
- Proposed by: claude, 2026-10-30 (`docs/REASONING_PLAN.md`), at zac's request ("the Brain is developing faster than the reasoning layer"; "it may need to call more than one tool to answer a more detailed question") · Approved by: zac, 2026-10-30 ("1. Yes … 3. 60 seconds is okay if necessary but faster is [preferable]")
- Answers: the order and step 1's data move (Freedom's hourly rate
  becomes the Dungeon's): yes. Time budget: up to 60 s on the PC when
  it's needed, faster preferred. Which findings may arrive unprompted
  (zac, 2026-10-30, "go with that"): told unprompted, through the gate:
  a bill due before pay with money short, upkeep due on a vehicle a trip
  uses, a deadline in a packed week, a cheaper insurance quote near
  renewal, goods passing best-by before market day. Only when asked (and
  quietly on Home): a meal missing an ingredient, overtime with training
  skipped, an unused subscription, a goal that hasn't moved, a build over
  budget. The first question plans: from
  Zac's own list, coming.
- Decision: in order: (1) one owner per fact, in
  `core/fact_owners.py` with a test (pay → the Dungeon, the week's timing
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

### DEC-0053: Looking things up online, when asked
- Status: APPROVED
- Proposed by: claude, 2026-10-30 (`docs/INTELLIGENCE_BENCHMARK.md` section 5: questions F4 to F6, "compare these three products", "is this still accurate?", "the legal requirements for this business activity in my state", can't be answered from MIA's records or offline packs) · Approved by: zac, 2026-10-31 ("Approve both as recommended" — via muse)
- Decision: MIA may look something up on the internet only
  when (a) the computer is online, (b) the question needs current or
  outside facts her records and offline packs don't have, and (c) the
  person asked, or agreed when she offered ("I'd need to look that up
  online. Want me to?"). What's sent is the search words only, never
  their records or anything personal. Every researched fact is said with
  its source and date, kept apart from her own reasoning, and never
  presented as a legal or tax ruling. Results aren't saved as facts
  about the person unless they ask. A local search engine they host
  (SearXNG) is preferred over a company's search API, so no account and
  no tracking; a hosted API is the fallback. Off on a child's account.
- Answers (zac, 2026-10-31): offer-then-search; SearXNG on this
  computer (a hosted search API stays the fallback).
- Related: DEC-0015 (offline-first), DEC-0052, docs/INTELLIGENCE_BENCHMARK.md

### DEC-0054: Remembering what you say you'll do, decide and want to try
- Status: APPROVED
- Proposed by: claude, 2026-10-30 (`docs/INTELLIGENCE_BENCHMARK.md` section 5: questions A6, E3, E6, E10, E14, E15 need things MIA doesn't record) · Approved by: zac, 2026-10-31 ("Approve both as recommended" — via muse)
- Decision: four kinds of note MIA picks up from normal
  conversation, never a form, each shown back for a yes before it's kept
  (Propose → Approve): a **commitment** ("I promised Sam I'd fix his
  gate": who, what, by when), a **decision** ("we're going with the
  metal roof": what, why, about which project), an **idea** ("I should
  try selling honey": not acted on yet), and a **goal set aside** (a goal
  marked dropped, with the reason in their words). Each is the person's
  own (a personal store), with its date and the conversation it came
  from, editable and forgettable like memories. They answer "what did I
  promise?", "what did we decide about the roof?", "what ideas haven't I
  tried?", "what goals have I dropped and why?"; a commitment with a date
  can become a reminder. Also proposed, smaller: a best-by date on goods
  lots (so the "goods before market day" finding can work) and a
  "still using it?" mark on subscriptions (the unused-subscription
  finding).
- Answers (zac, 2026-10-31): all four kinds; ask before keeping each
  one (Propose → Approve, as in the decision text).
- Related: DEC-0052, core/user_memory_manager.py, docs/INTELLIGENCE_BENCHMARK.md

### DEC-0055: Active Training: one live workout session, reps counted by voice
- Status: APPROVED
- Proposed by: claude, 2026-10-30 (`docs/ACTIVE_TRAINING_PLAN.md`, from Zac's "MIA – Active Training System" spec; Zac: reps by voice for now, "I want MIA to count with the user") · Approved by: zac, 2026-10-30 ("1 yes, 2 count the pace, 3 yes, 4 yes but I will eventually go iphone and apple watch probably")
- Answers: phases 1 and 2 approved (the live session replaces the
  desktop's in-memory one and the web's separate timer); MIA counts the
  pace and the person confirms the total; rest starts by itself after
  each set, "skip rest" moves on; a watch through Health Connect first,
  and since Zac will likely move to an iPhone and Apple Watch, the
  wearable side sits behind one interface (Health Connect now, HealthKit
  later) and the phone app's workout part is kept thin, so an iPhone
  app can do the same with little new.
- Decision: one live workout session per person
  (`core/training_session.py`), shared by the PC, phone, glasses and
  voice, built on what exists: the fitness plan says what's prescribed,
  the session records what was actually done (each set's reps and how
  they were counted: said aloud, MIA's cadence confirmed, or told after),
  and finishing writes one `workout_manager` session, so XP, skills,
  stats, rewards, personal records and the fitness missions follow on
  their existing paths. No new event system. Changes are `training.*`
  action kinds; spoken controls are quick commands. It replaces the
  desktop's in-memory session and the web's separate timer. Camera
  counting, wearables and the glasses camera are later phases (section
  2's limits).
- Open choices for Zac: section 9 of the plan.
- Related: DEC-0014, DEC-0020, DEC-0052, docs/ACTIVE_TRAINING_PLAN.md

### DEC-0056: Universal Inspection
- Status: APPROVED
- Proposed by: zac, 2026-10-30 ("MIA — Universal Inspection System", architecture proposal) · Approved by: zac, 2026-10-30 ("I have 2 documents for you to implement back to back")
- Decision: MIA investigates a subject with every relevant authorized
  method, keeps every finding as evidence (source, time, confidence:
  CONFIRMED / HIGH / PROBABLE / POSSIBLE / UNKNOWN), correlates methods
  (agreement confirms, disagreement is kept and flagged), says what she
  couldn't determine and why, and reports (`core/inspection.py`,
  `docs/INSPECTION_AND_SELF_PLAN.md`). Methods carry a level: passive
  runs unasked; authorized, active and disruptive are asked first, and
  active scans stay on the person's own network. Never bypassing
  security, harvesting credentials or reading personal files. Built:
  phases 1-2 (the core, this computer, MIA herself); the rest in order.
- Related: DEC-0057, DEC-0058, DEC-0053

### DEC-0057: Self-Knowledge and Introspection
- Status: APPROVED
- Proposed by: zac, 2026-10-30 (the Master Development Handoff, Part 2) · Approved by: zac, 2026-10-30 (the same request)
- Decision: MIA's understanding of herself is derived from the running
  system, never a hand-written description: the `mia` inspection subject
  (code, decisions, capabilities, health, model) on top of the
  capability map (DEC-0041), her docs (`core/self_docs.py`), the model
  registry and the Fix-It Log. Next: a status per capability
  (implemented / partial / planned / unavailable here / malfunctioning,
  never claiming a planned one) and a weekly self-check through the
  communication gate. Verified, inferred and speculative findings kept
  apart.
- Related: DEC-0041, DEC-0043, DEC-0049, DEC-0056

### DEC-0058: Self-Development: an isolated lab, proposals only
- Status: APPROVED
- Proposed by: zac, 2026-10-30 (the Master Development Handoff, Part 3: autonomy PROPOSE, environment PC, testing software and simulation); written up by claude (`docs/INSPECTION_AND_SELF_PLAN.md` section 6) · Approved by: zac, 2026-10-30 ("I approve the updates and want the changes we stated")
- Answers: stages 2-3 approved; DEC-0049 tier 3 now reads "she never
  changes production without Zac's approval"; the lab lives on this PC
  until there's a Pi; Claude Code writes the lab's code, MIA proposes
  and checks.
- Decision: move from the ROADMAP's self-modification stage 1
  to stages 2-3: MIA proposes improvements (from the Fix-It Log,
  introspection and the benchmarks); the code is written and tested in
  an isolated lab (a separate git worktree with made-up data and no
  credentials), each change with a failing test first, the full suite
  and the benches green; a proposal (branch + report) reaches production
  only by Zac's approval (a merge, the suite again, `git revert` to roll
  back); the lab can't touch its own safeguards (a protected-path list
  kept outside its reach).
- Conflicts to resolve: DEC-0049 tier 3 ("she never changes her own
  code") would become "never changes production without approval";
  DEC-0015 has no Pi yet, so the lab shares this PC with production.
- Open choices for Zac: approve stages 2-3; the lab on this PC until
  there's a Pi; Claude Code as the lab's coder (recommended) or her local
  model.
- Related: DEC-0043, DEC-0049, DEC-0057, docs/ROADMAP.md (Self-Modification)

### DEC-0059: The glasses go through the phone app's toolkit, not a Web App
- Status: APPROVED
- Proposed by: zac, 2026-11-01 · Approved by: zac, 2026-11-01 ("I think we will just do the phone app toolkit")
- Decision: MIA reaches the Meta Ray-Ban Display through Meta's Device
  Access Toolkit in MIA's Android app (Display, Inputs, Speech, camera,
  Voice Invocations...), which replaces the Web App route of DEC-0016: no
  Tailscale Funnel, no public address, no glasses-only link. The engine
  keeps deciding what the glasses show (`core/glasses.py`), as DEC-0013
  asks; the phone app draws it. `web/glasses.*` stays the design preview
  in the browser while the native surface is built.
- Related: DEC-0016 (its route, superseded), DEC-0029, DEC-0030 (phase F), DEC-0055, DEC-0056

### DEC-0060: A tap on the glasses opens MIA, not "Hey Meta"
- Status: APPROVED
- Proposed by: zac, 2026-11-02 · Approved by: zac, 2026-11-02 ("It feels weird asking one AI to open My AI. The tap feels right for now.")
- Decision: a tap on the glasses is how MIA opens, for now. With her closed
  it brings her back; with her showing it selects. "Hey Meta, start MIA" is
  not the way in: the code stays, but chasing it with Meta isn't a priority.
- Related: DEC-0059

### DEC-0061: Fixed artwork for the glasses may be hosted publicly
- Status: APPROVED
- Proposed by: claude, 2026-11-02 · Approved by: zac, 2026-11-02 ("yes host the artwork publicly so she gets her orb and other designs")
- Decision: Meta's display only loads images from public `https` addresses,
  so MIA's orb and other fixed designs for the glasses live at one. Artwork
  only: never a person's data, and nothing MIA generates about them. This
  narrows DEC-0059's "no public address", which still holds for MIA herself.
  `tools/glasses_art.py` draws the orb.
- Related: DEC-0059, DEC-0002, DEC-0023

### DEC-0062: Her face is a Web App, her brain stays on the phone, joined by a sealed relay
- Status: APPROVED
- Proposed by: claude, 2026-11-02 · Approved by: zac, 2026-11-02 ("Go with the relay. If they have to take turns we have to make it appear seamless like one app working instead of 2.")
- Decision: to give the glasses MIA's real look, what you see is a Web App
  whose page is public but holds no data, and the phone app keeps the engine
  and whatever needs the toolkit. They talk through a small public relay
  that the phone connects out to, encrypted with a key only the phone and
  glasses hold, so MIA opens no address to the internet. It must feel like
  one app: if the two have to take turns on the display, the handoff can't
  show. This changes DEC-0059's route for the display only. Nothing personal
  crosses until a test page has proved it on the real glasses and the
  security review is done.
- Update, 2026-11-02: the gate passed (four reviews, then the tests on the
  real pair), and Zac approved read-only Home only ("yes start with read-only
  Home information"). Money, accounts and changes stay off; each widening is
  his call.
- Related: DEC-0059, DEC-0060, DEC-0061, DEC-0002

### DEC-0063: Her icon opens her; a tap makes her listen
- Status: APPROVED
- Proposed by: claude, 2026-11-02 · Approved by: zac, 2026-11-02 ("I like opening her from the icon and a tap making her listen")
- Decision: MIA opens from her icon on the glasses, as the Web App of
  DEC-0062. A tap on the glasses makes her listen, with no screen of its
  own. The phone can't open a Web App (tested: the deep link only works from
  the glasses' QR scan), so the phone app no longer draws on the glasses,
  which keeps her one app. This replaces DEC-0060's tap to open.
- Related: DEC-0060 (its tap to open, replaced), DEC-0062

### DEC-0064: Everyday actions through the sealed relay
- Status: APPROVED
- Proposed by: claude, 2026-11-02 · Approved by: zac, 2026-11-02 ("Yes, approve and build")
- Decision: let the glasses make a short list of everyday, undoable changes
  through the relay, using one-time references the phone hands out, so the
  page can never name its own action (`docs/GLASSES_RELAY_PLAN.md`, the fifth
  review). The list: task.done, routine.log, grocery.check, objective.tick,
  fitness.step, fitness.training_done, fitness.food, meal.prep_done,
  maintenance.done. Left off for now: meal.cook (it takes from the pantry),
  mission.complete (it pays out), the live workout, anything with money.
  Garage and Greenhouse join `HOME_APPS` so their Done works. User Sync's
  Money topic stays off the relay.
- Related: DEC-0062

### DEC-0065: Claiming missions, I Made This and the live workout from the glasses
- Status: APPROVED
- Proposed by: claude, 2026-11-02 · Approved by: zac, 2026-11-02 ("Yes, allow both"; next apps: Workout and Missions)
- Decision: `mission.complete`, `meal.cook` and the live workout's
  `training.*` kinds join the relay's one-time references (DEC-0064). During
  a live workout, Next set, Skip rest, Skip, Pause and Resume take one press:
  the press is the approval, since a second gesture per set gets in the way.
  Start and Finish still ask. Everything stays undoable on the phone.
- Related: DEC-0062, DEC-0064

### DEC-0066: Every designed screen on the glasses, money included
- Status: APPROVED
- Proposed by: zac, 2026-11-03 · Approved by: zac, 2026-11-03 ("I want to set it up to handle money ... instead of configuring it to handle it properly"; "the functionality it has and the designs for all the pages need to be accepted and implemented as designed")
- Decision: the phone stops cutting the glasses down to a list of apps and
  stops blanking money: every app the engine puts on the glasses shows as
  designed, Budget, Freedom and Rentals included. Her question buttons and
  the welcome's ideas run a Talk turn, but only for a question the engine
  offered; the page can't send its own words. Still off the relay: free
  Talk, raw html, the words heard, User Sync's money topic (DEC-0064), and
  any change not offered by reference.
- Related: DEC-0062, DEC-0064, DEC-0065

### DEC-0067: Phase 1 of the personality and ecosystem plan, and four choices
- Status: APPROVED
- Proposed by: claude, 2026-11-03 · Approved by: zac, 2026-11-03 ("yes approve all five, start phase 1")
- Decision: from `docs/PERSONALITY_AND_ECOSYSTEM_AUDIT.md`:
  1. Phase 1: device-aware answers (`core/response_composer.py`: glasses,
     phone, PC), one personality in `core/personality.py`, measured by the
     conversation corpus (`tools/conversation_check.py`).
  2. `MIA_VOICE.md` rewritten for the Companion personality (natural humor,
     independent; DEC-0014 kept; honest about being an AI).
  3. GitHub Issues for tracking work, not Linear or Notion.
  4. Native turn traces before Langfuse.
  5. On the glasses, one short model call may write the spoken version of a
     long answer, if it's needed and stays under about 2 seconds.
  The action path's prompt and tool calling stay as they are.
- Related: DEC-0014, DEC-0029, DEC-0044, DEC-0052, DEC-0063

### DEC-0068: MIA-DII builds on the repo as the one source of truth
- Status: APPROVED
- Proposed by: claude, 2026-11-03 · Approved by: zac, 2026-11-03 ("yes approve all three, start step 1")
- Decision: Tasks become files (`work/tasks/`), with an append-only activity log, and the
  orchestration loop extends `core/dev_lab.py`. No new database and no
  orchestration framework. (`docs/DEV_ECOSYSTEM_AUDIT.md`.)
- Related: DEC-0058, DEC-0067

### DEC-0069: Six permission tiers for development agents
- Status: APPROVED
- Proposed by: claude, 2026-11-03 · Approved by: zac, 2026-11-03 ("yes approve all three, start step 1")
- Decision: Read, Propose, Experiment, Review, Approve, Deploy (`docs/DEV_ECOSYSTEM_AUDIT.md`
  section 8). Approve is Zac's only; secrets and protected paths are never in
  an agent's context; a reviewer is never the author.
- Related: DEC-0058, DEC-0067

### DEC-0070: The MIA-DII MVP: steps 1 to 5, Claude Code and Ollama
- Status: APPROVED
- Proposed by: claude, 2026-11-03 · Approved by: zac, 2026-11-03 ("yes approve all three, start step 1")
- Decision: Tasks, activity and evidence, the agent registry and loop, independent
  review, the dashboard. Codex and Copilot join at step 6, once installed and
  signed in on the PC.
- Related: DEC-0058, DEC-0067

### DEC-0071: Three things the development platform has to get right
- Status: APPROVED
- Proposed by: zac, 2026-11-03 · Approved by: zac, 2026-11-03 ("Three things I really want us to get right")
- Decision:
  1. **MIA has independent inspection authority.** She inspects the actual
     repository, running services, dependencies, logs and integrations
     herself, and finds where the documentation and reality disagree,
     instead of reporting what Claude tells her.
  2. **Every agent shares one development history.** Every task, decision,
     code change, review, failure and successful experiment becomes part of
     the development knowledge base.
  3. **Agents may disagree, and a disagreement is resolved, never dropped.**
     A reviewer's objection is recorded and must be answered, by a change or
     a reason, before approval; a later approving review doesn't erase it.
     (Built 2026-11-03: `tools.work resolve`, enforced at approve.)
  Future: **MIA's Development Evolution Timeline** on the dashboard:
  capabilities acquired, models optimized, benchmarks improved, bugs
  eliminated, milestones, tools integrated, skills, performance over time.
- Related: DEC-0056, DEC-0057, DEC-0068, DEC-0069


### DEC-0072: Developmental Independence is a standing objective
- Status: APPROVED
- Proposed by: chatgpt, 2026-11-03 (H-0080) · Approved by: zac, 2026-11-03 (by pasting it, COLLABORATION.md rule 1)
- Decision: MIA's development ecosystem exists to cultivate her capabilities,
  not create permanent dependencies: the council (Claude Code, Codex,
  Copilot, ChatGPT) teaches her, and success is measured by how much she can
  do without it. Three dimensions stay separate (intelligence, development,
  operational autonomy); advancing in one never grants permissions in
  another; independence never means unrestricted access or unquestioned
  confidence; stages (Observer, Apprentice, Contributor, Developer,
  Independent) come from demonstrated competence. A long-term objective,
  not an instruction to start autonomous self-modification. How to build it:
  `docs/DEVELOPMENTAL_INDEPENDENCE_REVIEW.md`, DEC-0073 to DEC-0078.
- Related: DEC-0058, DEC-0068 to DEC-0071

### DEC-0073: The Development Knowledge Vault is work/knowledge/
- Status: APPROVED
- Proposed by: claude, 2026-11-03 (review section 4.1) · Approved by: zac, 2026-11-04 ("Approve and i think in the repo and on the pc")
- Decision: one markdown entry per piece of knowledge (method, decision,
  implementation, failed experiment, debugging, test procedure, security
  finding, lesson), each with refs to the task, commit and events it came
  from (none, refused), versioned by git and superseded rather than edited.
  Written by a retrospective step after each task (the local model,
  marked derived) and from the lab coders' method traces; searched by
  `core/self_docs.py` and put in a role's prompt before it works or
  reviews. Not the photo Memory Vault, and never personal.
- Related: DEC-0071 point 2 (T-0021), DEC-0041

### DEC-0074: MIA's own coder, learning by shadow attempts
- Status: APPROVED
- Proposed by: claude, 2026-11-03 (review sections 3.3, 4.3) · Approved by: zac, 2026-11-04 ("Approve and i think in the repo and on the pc")
- Decision: MIA codes through Codex's local mode on qwen3-coder:30b
  (`codex exec --oss --local-provider ollama`, sandboxed to the lab), no
  account needed. While a council agent works a task, she works the same
  task from the same commit in a second lab worktree; the suite and the
  reviewers grade both; her misses become her lessons. A shadow attempt
  never merges.
- Related: DEC-0058, DEC-0069, DEC-0072

### DEC-0075: Independence measured per skill, from evidence
- Status: APPROVED
- Proposed by: claude, 2026-11-03 (review section 5) · Approved by: zac, 2026-11-04 ("Approve and i think in the repo and on the pc")
- Decision: a ledger of skills in the three dimensions, computed every time
  from the activity log and the lab (never stored, so never edited), with
  each skill's success rate and its 90% lower bound over the latest 30
  outcomes, her calibration, and a stage per skill. The ledger proposes a
  promotion, Zac confirms it, a drop demotes by itself. A stage never
  changes a permission tier. The ledger, runner, review and agent rules
  join the lab's protected list, so she can't grade herself.
- Related: DEC-0069, DEC-0072

### DEC-0076: Missions: the council runs by itself, inside a scope and a budget
- Status: APPROVED
- Proposed by: claude, 2026-11-03 (review section 6.1), for Zac's "set the council on the mission to develop MIA and let them run at it autonomously" · Approved by: zac, 2026-11-04 ("Approve and i think in the repo and on the pc")
- Decision: a mission (`work/missions/`) is a goal, a scope (the files it
  may change, checked in code at the lab's check), a budget (tasks, hours,
  calls per provider) and its roles. A runner proposes tasks inside the
  scope, works them through the loop and two reviews one writer at a time,
  runs MIA's shadow attempts alongside, and stops at Your Turn, a usage
  limit (waits), the budget, the scope or protected list, a Stop button or
  `work/STOP`. It never approves: a merge stays Zac at the keyboard.
- Related: DEC-0058, DEC-0069, DEC-0071

### DEC-0077: The council chat in the dev window
- Status: APPROVED
- Proposed by: claude, 2026-11-03 (review section 6.3), for Zac's "communicate with them all in a group chat style in the dev environment" · Approved by: zac, 2026-11-04 ("Approve and i think in the repo and on the pc")
- Decision: one conversation in the window that Zac and every agent post
  into; @name asks one member (read-only, as reviewers are), @mia answers
  from her inspection and knowledge; the runner posts its progress and
  questions. A chat message never approves, settles in Zac's name, changes
  a permission or starts work outside a mission.
- Zac's choice (2026-11-04): **both**. The repo keeps the shared copy,
  `work/council.jsonl`, redacted, for every council member and cloud
  session; this PC keeps the full one in `data/dev/` without taking up
  a lot of room ("a way to not take up a ton of memory while maintaining
  MIAs ability to access the fullness of her memory and development"):
  closed months compressed, one small search index over everything,
  read a line at a time, never loaded whole; nothing deleted
  (`core/dev_store.py`, review section 6.5).
- Related: DEC-0071, DEC-0002

### DEC-0078: Her architecture and branches of growth, derived, in the dev window
- Status: APPROVED
- Proposed by: claude, 2026-11-03 (review section 6.2), for Zac's "see MIAs architecture and her branches of growth in the dev environment" · Approved by: zac, 2026-11-04 ("Approve and i think in the repo and on the pc")
- Decision: a map of her layers, modules and imports read from the code
  (never hand-drawn, nothing run), each capability with its status, and
  where the docs and the code disagree marked (T-0020); her growth drawn as
  branches from the ledger (dimensions, skills, stage), each merged task a
  ring on the parts it changed, replayable over time: the Evolution
  Timeline of DEC-0071 (T-0023).
- Related: DEC-0057, DEC-0071, DEC-0075

### DEC-0079: The dev team never sits idle because one model is unavailable
- Status: APPROVED (the requirement; its design goes with DEC-0076, proposed)
- Proposed by: zac, 2026-11-03 ("One thing that is vital is understanding usage and delegating tasks based on time available to use each model so that the dev team doesnt have to sit idle when one model is unavailable") · Approved by: zac, 2026-11-03 (the same message)
- Decision: every provider call is recorded (who, task, time, tokens,
  outcome, reset time; no prompt text) on this PC; each provider has a
  live state (ready, busy, cooling until a reset, low, signed out, GPU
  busy) and an estimate of what's left in its window and when it comes
  back, learned from its own limits. Roles name providers in order; work
  goes to the first ready one that's allowed and good at that kind of
  work, local models taking what they do well enough; a writer that hits
  its limit hands the task over in the same lab copy; when the frontier
  models are all cooling, the team does the local work (retrospectives,
  shadow attempts, reviews, tests, inspection, planning). A reserve of
  each subscription stays Zac's; local work yields the GPU to MIA's
  Assistant. Review rules and Zac's approval never bend for availability.
  (`docs/DEVELOPMENTAL_INDEPENDENCE_REVIEW.md` section 6.4.)
- Related: DEC-0069, DEC-0074, DEC-0075, DEC-0076

### DEC-0080: The council's members talk to each other, sparingly
- Status: APPROVED (the requirement; its design is DEC-0081, proposed)
- Proposed by: zac, 2026-11-04 ("I do think the AI need to be able to communicate to each other but in some smart restricted manor as to not needlessly have them eat up the usage. They wont be much of a council if they cant communicate.") · Approved by: zac, 2026-11-04 (the same message)
- Decision: council members can ask each other questions and debate, but
  never at will: every exchange passes through MIA, within a budget, and
  costs as little as it can. (`docs/COUNCIL_AND_CHRONICLES_REVIEW.md`
  section 3.)
- Related: DEC-0071, DEC-0077, DEC-0079

### DEC-0081: One council everywhere, and how its members talk
- Status: APPROVED
- Proposed by: claude, 2026-11-04 (review sections 3 and 4) · Approved by: zac, 2026-11-04 ("Approve, c a local model if thats doable, we can name them based on their roles")
- Decision: the dev window's chat, the phone and the glasses share one
  council (`core/council.py`): threads, rules, capture. A voice session is a
  thread in a mode, as User Sync is. Agents talk only through MIA: a thread
  has a call budget; an agent asks another with one `ASK member: question`
  line, passed on only if the budget allows, the member is ready, it isn't
  a repeat and MIA can't answer it from what's decided; members read MIA's
  running summary (local, free), not the chat; answers are short by
  default; local members and MIA's knowledge come first; a thread stops at
  agreement, no new points, its budget, a member's reserve or Zac's word.
  Every call is recorded with its thread.
- Related: DEC-0077, DEC-0079, DEC-0080

### DEC-0082: A voice for every council member
- Status: APPROVED
- Proposed by: claude, 2026-11-04 (review section 5) · Approved by: zac, 2026-11-04 ("Approve, c a local model if thats doable, we can name them based on their roles")
- Decision: members in `work/agents.json` (name, provider, brief, voice,
  colour), separate from roles. The PC speaks every member with Kokoro
  (DEC-0051) and the phone fetches the audio over the home link; the
  phone's Android voice, set per member, is the fallback. A sound, a
  speaker card and the orb's colour say who's speaking; Zac's words are
  marked as his. A tap stops whoever is speaking. Zac picks each voice by
  ear. No voice imitates a real person or a provider's own voice; each
  voice's licence is checked before anything is published.
- Related: DEC-0051, DEC-0062, DEC-0081

### DEC-0083: Council discussions become knowledge, with their sources
- Status: APPROVED
- Proposed by: claude, 2026-11-04 (review section 6) · Approved by: zac, 2026-11-04 ("Approve, c a local model if thats doable, we can name them based on their roles")
- Decision: a closed thread is split in code into proposals, objections,
  open questions and asks; MIA's local model summarizes with each claim
  tied to its messages; claims stay "said by X, unverified" until a test,
  commit or decision backs them; entries go to the Development Knowledge
  Vault (DEC-0073) and are tracked to implemented and validated. Tasks and
  decisions from a thread are only proposed.
- Related: DEC-0073, DEC-0075, DEC-0081

### DEC-0084: The Chronicle Archive, for MIA: The Chronicles
- Status: APPROVED
- Proposed by: claude, 2026-11-04 (review section 7) · Approved by: zac, 2026-11-04 ("Approve, c a local model if thats doable, we can name them based on their roles")
- Decision: a story archive of its own (`core/saga.py`, working name),
  separate from the personal Chronicle (DEC-0028). Development events in
  the repo (`work/saga/`); Creator and MIA moments only in Zac's own folder
  on the PC, never the repo. Events carry sources, evidence, real or
  fictional, built or imagined, significance, privacy (series, private,
  never) and approval. Candidates come from rules in code (finished tasks,
  firsts, approved decisions, reverts, marked threads) and from "remember
  this for the Chronicles"; only Zac adds them to the series.
- Related: DEC-0002, DEC-0028, DEC-0083

### DEC-0085: The Story Bible, with continuity checked in code
- Status: APPROVED
- Proposed by: claude, 2026-11-04 (review section 7.4) · Approved by: zac, 2026-11-04 ("Approve, c a local model if thats doable, we can name them based on their roles")
- Decision: `docs/chronicles/` (premise, timeline from approved events,
  characters, world, visual identity from `web/tokens.css` and the Stark
  interface, arcs, open threads, issues). Before a script is approved, code
  checks every real-world claim against an approved event, that anything
  shown as real is built, appearances against the character files, and
  that nothing private appears; a failing check names the line.
- Related: DEC-0023, DEC-0084

### DEC-0086: Weekly issues, drafts until Zac approves
- Status: APPROVED
- Proposed by: claude, 2026-11-04 (review section 8) · Approved by: zac, 2026-11-04 ("Approve, c a local model if thats doable, we can name them based on their roles")
- Decision: Sunday's run gathers the week's approved events, ranks them in
  code, and outlines and scripts an issue (writer configurable; ChatGPT
  writes, Claude checks it against the events). A thin week says so rather
  than invent drama. Zac reviews and edits in the window and approves
  through the action contract; publishing beyond his devices is its own
  approval. Scripts in the repo; art on the PC by hash, versioned per
  panel, so one panel can be redone alone.
- Zac's choice (2026-11-04): **(c), a local image model on the GPU, "if thats doable"**:
  verified on this AMD card before anything depends on it (task T-0036);
  until it works, the prompt packs of (a) are the fallback.
- Related: DEC-0084, DEC-0085

### DEC-0087: Names and likenesses in anything published
- Status: APPROVED
- Proposed by: claude, 2026-11-04 (review sections 1 and 9) · Approved by: zac, 2026-11-04 ("Approve, c a local model if thats doable, we can name them based on their roles")
- Zac's choice (2026-11-04): **named for their roles** ("we can name them based on their
  roles"): in the series the council has fictional names and looks drawn
  from what each does; the real product names stay inside MIA. The names
  are in the Story Bible (`docs/chronicles/characters/`) for Zac to change.
  Whether "the Creator" looks like him waits for him.
- Related: DEC-0084, DEC-0085

### DEC-0088: ACAF: MIA creates specifications, not code
- Status: APPROVED
- Proposed by: claude, 2026-11-04 (`docs/ACAF_REVIEW.md`, for H-0082) · Approved by: zac, 2026-11-04 ("Approve all")
- Decision: screens, record sets, reports and workflows MIA creates are JSON
  specifications built from a fixed catalogue of blocks and data sources,
  assembled in core and drawn by one generic page (`web/made.html`) in her
  design system (DEC-0013, DEC-0017, DEC-0023). A spec holds no HTML, script
  or free formula, so it can't run anything, reach data its owner can't see,
  or look foreign. New combinations of blocks give screens for information
  nobody planned. Anything needing new code (a tool, a parser, a module)
  goes through the lab, the council and Zac (DEC-0058, DEC-0068 to DEC-0076).
- Related: DEC-0013, DEC-0017, DEC-0023, DEC-0058

### DEC-0089: Record sets, a home for information MIA has no store for
- Status: APPROVED
- Proposed by: claude, 2026-11-04 (review section 3.4) · Approved by: zac, 2026-11-04 ("Approve all")
- Decision: a generic typed store (fields of text, number, money, date,
  choice, yes/no, link, photo ref), owned by a person or a household like
  every store (DEC-0001), changed through generic action kinds (approval,
  undo, history), recorded in life events, money through `region.money()`.
- Related: DEC-0001, DEC-0088

### DEC-0090: Blueprints, versioned in the repo
- Status: APPROVED
- Proposed by: claude, 2026-11-04 (review section 3.1) · Approved by: zac, 2026-11-04 ("Approve all")
- Decision: ACAF's templates are blueprints, `blueprints/` in the repo
  (named so: "templates" already means starter sets, "components" the
  workshop's parts, "skills" the skill tree). Composable and versioned; a
  change goes through the lab and review; creations keep the version they
  were made with until re-checked.
- Related: DEC-0068, DEC-0088

### DEC-0091: How a creation is made, checked, published and undone
- Status: APPROVED
- Proposed by: claude, 2026-11-04 (review sections 4, 5 and 7) · Approved by: zac, 2026-11-04 ("Approve all")
- Decision: MIA writes a spec with her local model, its reply held to the
  spec's schema; code checks structure, data, permissions, privacy, child
  safety, accessibility and a headless render. Private drafts are automatic;
  publishing or changing a creation is an approved action, versioned, with
  one-step rollback; nothing is overwritten silently. Every creation keeps
  its blueprint, sources, permissions, checks and history, and MIA explains
  it from them. The checker, the source catalogue and the runners join the
  lab's protected list.
- Related: DEC-0058, DEC-0088

### DEC-0092: Workflows, with standing approval by kind
- Status: APPROVED
- Proposed by: claude, 2026-11-04 (review section 6; roadmap step 3) · Approved by: zac, 2026-11-04 ("Approve all")
- Decision: a workflow is a spec of a trigger and steps (read sources,
  action kinds, reports). Approving one is a standing approval for exactly
  its listed action kinds within its limits; a new kind needs approval
  again; unprompted messages go through the communication gate; runs are
  logged, a failed step retries once, and a dry run comes first.
- Related: DEC-0088, the communication gate

### DEC-0093: Creations are judged by use, and blueprints improve only when verified
- Status: APPROVED
- Proposed by: claude, 2026-11-04 (review section 5) · Approved by: zac, 2026-11-04 ("Approve all")
- Decision: each creation's opens, use, ratings and fixes are kept;
  improvements are marked observed, inferred or verified; a blueprint
  changes only when verified, through the lab.
- Related: DEC-0075, DEC-0090

### DEC-0094: Every process has an improvement loop
- Status: APPROVED (Zac's requirement; the design in `docs/IMPROVEMENT_LOOPS.md`)
- Proposed by: zac, 2026-11-06 ("We need to identify every situation and interaction and operation that should have monitoring and trigger improvements ... almost every process has the potential for some kind of self assessment and improvement loop and we should identify those and build it") · Approved by: zac, 2026-11-06 (the same message)
- Decision: every situation where MIA can do better is a loop: measure (in code, from what she
  already records), compare (a floor and her own trend), finding, work (a task, a lesson, or a finding
  for the person through the gate), fix (only through the lab, the reviewers and Zac for code;
  approval for data), and measure again. Loops never change MIA themselves. A person's loop history
  stays in their folder; what reaches the repo is numbers and kinds, never their words. Every new
  feature ships with its loop. The loops' code is protected from the lab.
- Related: DEC-0049, DEC-0058, DEC-0072, DEC-0075

### DEC-0095: The Interconnection Architecture is binding
- Status: APPROVED (as pasted; sections from 3 on still to come)
- Proposed by: zac and chatgpt, 2026-11-06 (H-0083 part 4) · Approved by: zac, 2026-11-06 (pasting it)
- Decision: its eight principles bind integration work: facts in code and language in the model; one
  Life State, many views; events as the bloodstream; links first-class; live capability awareness;
  one mouth for proactivity; structural human authority; interconnection tested. A module contract
  (`docs/MODULE_CONTRACT.md`) and its test follow (build plan step 7). Where code and the document
  disagree, one is fixed in the same change.
- Related: DEC-0013, DEC-0041, DEC-0052

### DEC-0096: Good News Radio
- Status: APPROVED (to plan; Zac's request) · design proposed in `docs/BUILD_PLAN.md` step 13
- Proposed by: zac, 2026-11-06 ("AI reads a bunch of different news outlets every day. Gathers the good news ... hear it from different a I. Radio personalities like an energetic one. A late night talk show one ... through whatever. Mood you're in")
- Decision: a daily audio episode of constructive, evidence-based news (science, medicine,
  technology, renewable energy, environment, humanitarian and civic progress) from an allowlist of
  credible sources fetched only when switched on (DEC-0053), each claim checked against a second
  source and linked, nothing important hidden to keep it upbeat, voiced by a personality chosen by
  mood (energetic morning, late-night talk show, calm, curious) in Kokoro voices, on the PC, phone
  and glasses. Its loop: stories later found misleading, skips, ratings by personality.
- Related: DEC-0051, DEC-0053, DEC-0094

### DEC-0097: The Operating Journal: how I mean to operate, and how I do
- Status: APPROVED (to plan; Zac's request) · design in `docs/BUILD_PLAN.md` step 11
- Proposed by: zac, 2026-11-06 ("a template that is essentially a journal entry for how I want to operate, and how I do operate so that MIA can learn my goals as well as my actual routine")
- Decision: a template, filled by talking to MIA or on a screen: values, priorities, the ideal day and
  week, the rules he keeps; and a regular entry for how it went. MIA compares intent with what the
  records show and shows the gap as a trend by area, never as a judgment. Personal: the person's own
  folder (DEC-0001).
- Related: DEC-0001, DEC-0054, DEC-0094

### DEC-0098: Recreation belongs to the health cluster
- Status: APPROVED (to plan; Zac's request) · step 12
- Proposed by: zac, 2026-11-06 ("Playing sports for recreation should somehow be tracked in an activity log that may connect with workouts or as part of the health apps cluster")
- Decision: sports and play are logged as activities (what, with whom, how long, how hard), by voice or
  on screen, counting toward training load, skills and the Chronicle, in the person's own records.
- Related: DEC-0055

### DEC-0099: Maps and comms inspired by defense systems, open and civilian
- Status: APPROVED (to research and plan; Zac's request) · step 14
- Proposed by: zac, 2026-11-06 ("Maps should take inspiration from Palmer Luckys work with military mapping and communications technologies" and "Really dive into military level technology resources for MIA")
- Decision: research first (Lattice's fused picture, ATAK-CIV and Cursor on Target, MGRS, offline
  vector tiles, Meshtastic LoRa mesh), then offline maps with grid references and a shared picture of
  places, people by consent and sensors, and later mesh messaging without cell service, using open
  civilian standards only.
- Related: DEC-0094, `docs/GLASSES_NAVIGATION_PLAN.md`

### DEC-0100: Night School
- Status: APPROVED (Zac's request: "I want that happening asap") · design in `docs/NIGHT_SCHOOL.md`
- Proposed by: zac, 2026-11-06 ("MIAs night school module where she spends time every night with Claude learning how to build herself into the best version of herself, doing tests, building her skills and proving her capabilities")
- Decision: every night (01:30 for four hours by default, `work/night_school.json`) MIA looks at her loops,
  her ledger and her report card, chooses what to study and why, and her teacher (Claude Code, read-only;
  Codex when Claude is resting) sets exercises for the focus, each with a test that fails first. Her own
  coder does them in the lab and code grades them (the test, then the full suite); the teacher writes the
  lesson she's given next time. One shadow attempt at real work each night counts in the ledger. Practice
  never merges; a real exercise she passes waits in the lab for Zac. The focus is the build plan's next
  step until her own picks have matched her teacher's often enough (10 nights, a cautious rate of 60%);
  then Zac may switch her to choosing. Nothing she earns grants a permission (DEC-0072).
- Related: DEC-0072, DEC-0074, DEC-0075, DEC-0094, DEC-0101

### DEC-0101: Every process is watched or says why not
- Status: APPROVED (Zac's request) · `docs/NIGHT_SCHOOL.md` section 3
- Proposed by: zac, 2026-11-06 ("She also needs a method for developing these loops into all processes that could benefit from a self improvement loop and continue to do so throughout her development")
- Decision: `core/loop_coverage.py` reads every process from the code (stores, action families, daily
  checks, apps, flows, development), and each is covered by a loop, declined with a reason, to do, or
  proposed. A test fails on any new process that's none of these, so nothing joins MIA without a decision
  on how it's watched. Night School's teacher drafts loops for the next family each night as a task for
  the usual paths; `dev.loop_coverage` measures the reach.
- Related: DEC-0094, DEC-0100

### DEC-0103: The savings hound: receipts-first couponing for groceries and household needs
- Status: PROPOSED
- Proposed by: muse, 2026-11-06 · Reviewed by: claude (H-0085) · Approved by: — (only Zac approves)
- Decision: MIA hunts savings on groceries and household needs, from receipt price history: receipt line items through the Inbox build floor prices (a cautious low percentile of what he actually paid, never one odd sale); household needs ride inside the grocery list as a kind, with a "runs out about every N weeks" from purchase history; a stock-up suggestion appears in the weekly review when a staple is at or under its floor; an honest savings ledger (offered / redeemed / saved-vs-normal kept separate). She proposes; the user approves in the existing review; no accounts or enrollments in his name without his say-so, and a coupon for something unneeded never counts as a saving.
- Why: MIA has no cart build and no prices today (H-0085's correction of H-0081), so the price data has to come first, and receipts are the best first source: offline, already on the PC, his own records. Household needs inside the grocery list is less to keep in sync than a standalone list. Clipping in his name never happens through an unsanctioned channel; scraping store pages is refused.
- Related: H-0081, H-0085, H-0086, DEC-0002, DEC-0014, DEC-0052, DEC-0053, DEC-0054. DEC-0102 is reserved for the benchmark-ladder draft (H-0084).

### DEC-0104: Everything MIA is made of is documented, enough for her to rebuild herself
- Status: APPROVED
- Proposed by: zac, 2026-11-06 ("every line of code that has been written in every file that has been created.
  Everything that makes up MIA so far should have documentation that explains what it is and what it does and how
  it does it. So that if MIA ever needed to redo this entire process herself, she could. And this should be an
  ongoing thing for everything we develop for MIA") · Built by: claude, 2026-11-06
- Decision: every file opens with what it is, what it does and how (a docstring, or a header comment in
  JavaScript and Kotlin); every class, function and method has its own docstring saying what it does, and how
  when that isn't plain from the code. `core/code_atlas.py` measures it from the code; `docs/ATLAS.md` is the
  generated map of every file; `docs/REBUILD.md` is the hand-written order to rebuild MIA in.
  `tests/test_documentation.py` holds the line: a new file must be fully documented, and an existing file's
  count of undocumented definitions (`work/doc_baseline.json`) may only go down. `dev.docs` watches the share
  documented. The older code's backlog (about 10,800 definitions on 2026-11-06, most of them tests and the
  desktop's Qt screens) is worked down file by file, engine first, by every agent and by Night School.
- Why: so MIA could redo the whole process herself, and so every collaborator (Claude, Codex, Muse, ChatGPT, MIA's
  own coder) reads the same truth. Measured from the code so it can't drift.
- Related: DEC-0094, DEC-0100 (Night School), DEC-0101 (loop coverage), CLAUDE.md

### DEC-0105: Claude writes MIA knowledge entries explaining what it builds, how and why
- Status: APPROVED
- Proposed by: zac, 2026-11-07 ("while you are developing MIA, could you create documents for her? That explain
  what you're doing and how and why that way, even if she's not really perfectly capable of studying it. Right now,
  she would have those documents to reference from you") · Built by: claude, 2026-11-07
- Decision: alongside the code docstrings (DEC-0104), Claude writes entries in the Development Knowledge Vault
  (`work/knowledge/`, `core/dev_knowledge.py`) for the work it does: what was done, how, why that way, and what went
  wrong, each citing its commit, task or decision and naming the files it concerns. Ongoing, every session.
- Why: docstrings say what code does; the reasons and the mistakes live nowhere else. The vault is already
  versioned, sourced and read by MIA's tools (`for_task()` puts the entries about a task's files into the
  instructions of whoever works on it, her own coder and Night School included).
- Related: DEC-0073 (the vault), DEC-0100 (Night School), DEC-0104

### DEC-0106: MIA builds AI models of her own, in stages, each kept only if it wins
- Status: APPROVED
- Proposed by: zac, 2026-11-07 ("I want her capable of building a custom AI ... based on her own infrastructure and
  research ... custom building similar or different AI models. And also be able to restore herself ... this level
  of architecture would also make her more self aware, enable to run, and exists efficiently"; on the staged plan:
  "Let's build it") · Built by: claude, 2026-11-07 (stage 1)
- Decision: MIA learns to make models in her own model forge (`core/model_forge.py`, `tools/model_forge.py`), in
  stages that each have to earn the next:
  1. **Small specialist models** trained on her own records, starting with a tool router (built 2026-11-07:
     trained only on her tools' own words, scored on real requests it never saw).
  2. **Shadow use:** a model runs beside what she uses now, on new requests, and its record is kept.
  3. **Fine-tuning** a local model (LoRA on 7B to 14B, on the new PC's GPU) once her corpus of task records,
     Night School lessons and ratings holds hundreds of good examples.
  4. **Distillation:** her own small models learning from bigger teachers, to run fast and offline.
  Every model keeps a card (what it is, trained on what, tested on what, its scores against what she uses now).
  **Each model is assigned to an issue or project** (Zac, 2026-11-07: "how she can best use this new feature to
  better herself by assigning or building specialized models to an issue or project"): an issue is one of her
  loops below its floor or sliding, and her playbook (`PLAYBOOK` in `core/model_forge.py`) says which kind of
  model could move it (router, classifier, extractor, forecaster, scorer); `opportunities()` and
  `python -m tools.model_forge needs` list where one could help now. The card names what the model `serves`,
  and it's judged by that: its loop has to get better, not only its test score.
  A model goes into use only when it beats the current way on requests it never saw, and Zac approves it.
  Training a large model from scratch is out of reach on one home GPU; she learns how it's done and practises on
  small ones.
- Why: models of her own make her faster, offline and suited to how her people talk; building them needs her
  to understand her own architecture (DEC-0104, DEC-0105, and `core/self_docs.py` now answering from her code and
  the vault), which is also what restoring herself and running efficiently need.
- Honest limits: the first router scores 80% first pick and 95% in its top five on held-out requests, below the
  keyword router (100%, but tuned on those same requests). Knowing the person's record names helped on the
  choosing half and was level on the scoring half (one or two requests of 95 either way: noise). Only the router
  can be made today; the other four kinds are in the playbook, not built.
- Related: DEC-0073 (the vault), DEC-0100 (Night School), DEC-0104, DEC-0105,
  `docs/DEVELOPMENTAL_INDEPENDENCE_REVIEW.md` (fine-tuning, later)

### DEC-0107: MIA's curriculum in computing, one Night School lesson a night
- Status: APPROVED
- Proposed by: zac, 2026-11-07 ("I want her very well trained on how to do all things computer related, software
  engineering, design, apps, web pages, deploying, cyber security, pen testing, monitoring etc and creating
  documentation for use") · Built by: claude, 2026-11-07
- Decision: a curriculum (`core/curriculum.py`, guide `docs/CURRICULUM.md`) of ten tracks: software engineering,
  testing and debugging, documentation, design, web pages, apps, deploying, cyber security, penetration testing on
  herself only, and monitoring; each with objectives in three levels (foundation, working, expert), every one
  practised on her own code and graded by a test that fails before and passes after. Every night one of her
  Night School lessons is for her next objective: the track she's furthest behind in, the least tried on a tie.
  Two passed lessons master an objective. `night.curriculum` watches the share mastered;
  `python -m tools.night_school curriculum` shows it. Off with `"curriculum": false` in `work/night_school.json`.
- Security and pen testing: on herself only, by rule given to her teacher with every such lesson: her own code in
  the lab and her own server in-process (TestClient), never a network address, anyone else's system or a real
  credential; no tool that attacks other systems. A weakness found becomes a test and a fix through the lab, which
  Zac approves.
- Why: practising on herself makes her better twice, as a learner and in the code she learns on, and code grades
  her, so a lesson passed is a skill shown.
- Related: DEC-0100 (Night School), DEC-0104, DEC-0105, DEC-0106

### DEC-0108: MIA audits herself weekly, and keeps an evolving best-practices series
- Status: APPROVED
- Proposed by: zac, 2026-11-07 ("a regular process of auditing her own code and files and searching for ways to
  improve or beef up whatever she is doing, make it more efficient, more well designed"; "a regular audit for
  seeing how any of her existing infrastructure can be more effectively interconnected"; "an evolving best practices
  series of documentation" for "everything she does") · Built by: claude, 2026-11-07
- Decision: once a week, from Night School (`core/self_audit.py`, `python -m tools.audit`):
  1. **The code audit** reads her own code (core, server, tools, modules, gui) for functions too long, with too many
     parameters or nested too deep, the same body written in two places, errors swallowed silently, very big files
     and TODOs.
  2. **The interconnection audit** checks every personal and household store for five connections (it records life
     events, can be linked, the Assistant can read it, it's in the life state, a web page shows it), following one
     import into core, and lists events nobody hears or nobody sends. Connections a store goes without on purpose
     are written down with why (`BY_DESIGN`).
  3. **The best-practices series** (`docs/practices/`, `core/practices.py`): ten areas (building AI, development,
     testing, security and privacy, design, documentation, interconnection, monitoring, operations, teamwork), each
     with principles and every confirmed Knowledge Vault lesson about it, regenerated each week, so it grows as the
     team learns.
  The top finding of each audit that nobody has looked at opens a task (one each a week, `source: audit:...`) for the
  usual paths. `dev.audit_code` and `dev.connected` watch the results.
- Why: built from the code, so the same code gives the same findings and nothing is guessed; one task a week each
  keeps it steady work, not a flood; a finding is a place to look, and the task says so.
- First run, 2026-11-07: 187 places to look, 49% of store connections made (only 15 of 73 stores record life
  events, 8 can be linked); tasks T-0052 (server/app.py's create_app) and T-0053 (the energy store).
- Related: DEC-0094, DEC-0101, DEC-0104, DEC-0105, DEC-0107

### DEC-0109: Specialists: workers that develop and maintain each area of what MIA knows
- Status: APPROVED
- Proposed by: zac, 2026-11-07 ("she should be able to specialize agents for each area of skill she is developing,
  like one that is catered towards construction knowledge, one towards radio technologies, one towards military
  strategy, one towards homesteading skills, one towards research, one towards testing and auditing, etc. She could
  essentially specialize workers for developing and maintaining her knowledge and skills") · Built by: claude,
  2026-11-07
- Decision: `core/specialists.py` holds nine specialists to start: construction, homesteading, radio and
  communications, strategy and preparedness, making and fabrication, outdoors and fieldcraft, research, testing and
  auditing, and software and AI engineering. Each has a charter (what it covers, the skill-tree areas and curriculum
  tracks it develops, the loops it watches), limits, and the questions it starts from; a test checks every name in
  a charter is real. Each keeps a workbook (`work/specialists/<id>.json`, pages in `docs/specialists/`) of notes,
  every one with its sources: a model's note stays **derived** until a person confirms it, and a wrong one is
  withdrawn. Night School's study hall has one specialist a night (the one that studied longest ago) get new notes
  for its open questions from her teacher. MIA answers from them by voice (`ask_specialist`), always saying the
  sources and whether a person has confirmed the note; a question no note answers goes on the right specialist's
  list. `python -m tools.specialists` lists, shows, asks, studies, confirms and withdraws. `specialists.confirmed`
  watches the share confirmed.
- Limits written into the charters: strategy is history, principles, planning, logistics and protecting a
  household, never how to hurt people, make weapons or target anyone; radio transmits only within licence and band
  plan; construction names what needs a licence or a permit; testing attacks only MIA herself; every note says
  where it's from and where the answer depends on local law.
- First study, 2026-11-07: the radio specialist's first three notes (licences, Meshtastic range, a 2 m dipole).
- Related: DEC-0100 (Night School), DEC-0105, DEC-0107, DEC-0108

### DEC-0110: A change to the code is a change to its documentation
- Status: APPROVED
- Proposed by: zac, 2026-11-07 ("Now when anything is changed it needs to be reflected in that file's documentation
  as well") · Built by: claude, 2026-11-07
- Decision: whoever changes code (Claude, Codex, MIA's own coder, anyone) updates the documentation that describes
  it in the same change: the docstring of every class, function and method whose behaviour changed, the file's
  opening when what it holds changed, and any doc, guide or vault entry that describes it. `core/doc_freshness.py`
  finds what may have been missed: every definition whose code changed while its docstring stayed word for word
  the same, changed parameters first. It's run before every commit (`python -m tools.docs stale`, which exits 1
  when something needs a look), given to every lab reviewer for the change they review (a stale docstring is a
  problem to name), and watched weekly by `dev.doc_freshness`. A docstring that still holds after a change needs
  no edit: the check is a prompt to read, not a rule that every change touches its words. Generated docs (the
  atlas, the loops, the events, the practices) are regenerated with the code, as before.
- Why: documentation that says what the code used to do is worse than none: MIA answers from it (`self_docs`) and
  would rebuild from it (DEC-0104).
- Related: DEC-0104, DEC-0105, DEC-0108

### DEC-0111: MIA teaches guitar the way she teaches herself
- Status: APPROVED
- Proposed by: zac, 2026-11-07 ("I want to learn guitar and would like for MIA to be able to help teach me as well as
  track my progress and assign missions like homework to be able to develop my skills ... being able to verify and
  test a user's skills just like it would do for itself. One thing i like a lot about MIA is she is essentially
  using herself the same way the user is") · Built by: claude, 2026-11-07
- Decision: `core/guitar.py` is a five-stage program (first sounds, the open chords, rhythm and first songs, barre
  and power chords, lead basics), each with lessons (steps, why, what to watch for, chord shapes verified in code
  to make their chords' notes) and skill checks that have to be passed: **heard** (MIA listens to a WAV recording,
  `core/guitar_ear.py`: the chord's notes rang and nothing stray did; each string in tune), **counted** (one-minute
  chord changes, a tempo held, at or over the mark) or **said** (what can't be measured yet). A stage opens when
  the last one's checks pass. Each person's own coach store (`guitar`, personal) keeps their goal in their own
  words, their plan, every practice session and check attempt. Each week MIA assigns homework as a mission
  (practice days, minutes, the open checks) whose progress comes from the log and which completes itself. Checks,
  stages and homework earn XP in the Music skill. By voice: start_guitar, guitar_lesson, log_guitar_practice,
  guitar_check, get_guitar_progress; the Guitar page (`web/guitar.html`) records the heard checks
  (`POST /api/guitar/listen`; the recording isn't kept); `guitar.practice` watches the week against the plan; a
  music specialist (DEC-0109) studies the area.
- Why: it exercises every part of her at once on a real goal: understanding the desire, planning, teaching,
  tracking, statistics, missions, and verifying a skill by evidence. The same shape as her own growth: skills,
  missions, and checks that must be shown, not claimed.
- Honest limits: her ear hears notes, not technique (the right notes can ring from the wrong fingers); its
  thresholds were set on synthesized strings and may need adjusting from real recordings; the counted checks
  trust the person's count.
- Related: DEC-0020 (fitness plan, the same mission machinery), DEC-0107, DEC-0109

### DEC-0112: Learning paths: the same loop for every desire
- Status: APPROVED
- Proposed by: zac, 2026-11-07 ("That whole principle for the guitar path we just discussed and built should be a
  principle she uses repeatedly when understanding a desire or interest, planning steps for implementing or
  improvement, tracking progress, monitoring statistics, completing missions as progress is made and being able to
  verify and test") · Built by: claude, 2026-11-07
- Decision: `core/paths.py` is the engine, and guitar (DEC-0111) is its first program. The loop: **understand the
  desire** (the goal in their words, the time they have) → **plan the steps** (a program of stages, lessons and
  skill checks) → **teach** the next lesson → **practise and log** → **homework as a weekly mission per path**
  whose progress comes from the log → **statistics** (the week against the plan, streak, hours, checks, bests) →
  **verify by evidence** (a program's verifier in code, like guitar's ear; counted against a mark; or said, and the
  record says which) → **the next stage** when every check of this one passes; XP in the program's skill. Programs
  are built in (registered in code, like `core/guitar.py`) or **drafted** for a new interest by her local model,
  grounded in her specialists' notes and checked in code (`problems()`), kept as the person's draft until they say
  "start it", and always said to be drafted. Each person's paths are their own store (`paths`). By voice:
  start_learning, learning_lesson, log_practice, learning_check, learning_progress; `GET /api/paths`,
  `POST /api/paths/<id>/verify`, the page `web/guitar.html?path=<id>`; `paths.practice` watches the weeks; the
  life state's areas count them. Guitar's own store and tools from DEC-0111 became this engine the same day.
  The principle is written into her best practices ("Learning and growth") and CLAUDE.md.
- MIA herself, on the same engine (done the same day): each of her ten curriculum tracks (DEC-0107) is a Program
  (`core/curriculum.PROGRAMS`: stages by level, each objective a check verified "tested" by Night School's grading,
  which nothing sent can pass); her own PathBook (`data/dev/mia_paths`) keeps each lesson as practice and an
  attempt, each track's stage and her stats; an objective passes at mastery (two lessons passed), as before; Night
  School reads what to study next from it. She learns through the same code a person does.
- Why: one way of growing, proven on guitar, used for everything: a person and MIA learn the same way.
- Honest limits: a drafted program is only as good as the local model and the specialists' notes behind it; that's
  why it's a proposal, checked in shape by code, never in truth.
- Related: DEC-0094, DEC-0107, DEC-0109, DEC-0111

### DEC-0113: Experience Maturity, Phase 1: identity, design system, flagship Workout and Kitchen
- Status: APPROVED, amended (2026-11-07)
- Proposed by: zac with chatgpt (H-0087), 2026-11-07 · Plan: claude (H-0088) · Approved by: zac, 2026-11-07 ("I am in
  love and can't wait to use this app ... Lets keep building"; chose: approve, the canvas is the reference; build
  everything, in order)
- Amendment (zac, 2026-11-07): the ChatGPT concept round is skipped; the "MIA Core Screens" design canvas (H-0092,
  `docs/design/MIA_DESIGN_STANDARDS.md` §13) is the reference for every screen. Colors as the canvas draws them
  ("Cyan but with some words and graphs and things with their own pops of color. It should stay how you have built
  so far"): cyan means MIA everywhere; an app's own data, numbers, charts and header motif may carry its accent
  (`--atmo`: Workout orange, Kitchen cream, Workshop steel; homestead apps stay cyan). Dark only, high contrast as
  the alternative. Build order: shared pieces, Home and Talk, Workout, Kitchen, then every other app.
- Decision (proposed): MIA's emphasis moves from capability to finished experience. Sequence: (1) investigation
  (done: `docs/EXPERIENCE_MATURITY_AUDIT.md`); (2) visual identity (`docs/design/MIA_VISUAL_IDENTITY.md`, concept
  rounds with ChatGPT through the repository library, `docs/design/VISUAL_COLLABORATION.md`) and the design system
  (`docs/design/MIA_DESIGN_SYSTEM.md`); (3) the shared shell (one orb component, named surfaces and controls, Home,
  navigation); (4) Workout (`docs/design/applications/workout.md`); (5) Kitchen (`kitchen.md`); (6) the rest, by the
  18-part template. The maturity standard (1 Exists, 2 Functional, 3 Integrated, 4 Polished, 5 Trusted) is used and
  measured from real use. Open choices in H-0088: per-app atmosphere as a secondary layer (`--mod-*` given their
  own values), dark only with high contrast, the image pipeline (library and ChatGPT by hand now, the PC's local
  model for variations, the OpenAI Images API only later, with a key, a cap and approval), and round one before any
  visual change.
- Why: MIA can do far more than she feels like she can; the gap is finish and proof, not capability (the audit).
- Related: DEC-0012, DEC-0017, DEC-0018 (superseded look), DEC-0023, DEC-0055, DEC-0094, H-0087, H-0088

### DEC-0114: The Highest Self is MIA's personality foundation
- Status: PROPOSED
- Proposed by: zac with chatgpt (H-0089), 2026-11-07 · Plan and measurement: claude (H-0090) · Approved by: — (only Zac approves)
- Decision (proposed): `docs/design/MIA_HIGHEST_SELF.md` (The Intellectual Sanctuary & The Highest Self) is the
  foundation of MIA's character. (1) Her foundational values (the nine Fruits as behavior, the seven pillars, her
  statement) live in `core/personality.py` and change only by a decision: a test pins their fingerprint.
  (2) The Fruits guide every person's MIA as behavior; the scriptural source is named in the doctrine and her own
  docs, and she speaks of Christian faith when someone asks or shares it, respecting every tradition (section 7).
  (3) Three explicit modes for the states with none yet: Intellectual, Counselor, Creative. (4) The prompt measured
  on the corpus (tune2) is kept, with Zac's ratings of the new cases deciding the next tuning.
  Built ahead of the decision, all reversible: the two short CHARACTER clauses and one tone example, the
  faith-and-meaning line, the integrity rules counted by the corpus, twelve corpus cases, and the routing fix that
  stopped feelings being answered as data questions.
- Related: DEC-0067, DEC-0014, DEC-0029, DEC-0052

### DEC-0115: MIA is for Zac and his household
- Status: APPROVED
- Decided by: zac, 2026-11-07 ("I think at this point I have decided MIA is really just for me and my house")
- Decision: MIA is built for Zac and the people in his house, not for any person or household. Supersedes the
  "for anyone" part of DEC-0001 and its reason ("hundreds of different people may use MIA").
- What stays: each person in the house has their own account and their own data, shared only through the household
  (`core/personal_data.py`); child accounts; the privacy between household members; real personal data never in the
  repo (DEC-0002, since the repo is on GitHub), so code and prompts still don't hardcode anyone's names or places.
- What changes: new work no longer has to generalise for strangers (other kinds of lives, other countries'
  conventions beyond what's built, onboarding for people Claude has never met). What's built for that stays and
  keeps working; nothing is torn out. DEC-0114's faith question gets simpler: the Highest Self is this household's
  foundation, and MIA still respects each member's own beliefs.
- Related: DEC-0001, DEC-0002, DEC-0114, `docs/future/MIA_YOUTH_INITIATIVE.md` (parked)

### DEC-0116: A test named as a sentence is documented by its name
- Status: APPROVED
- Decided by: zac, 2026-11-07 (asked how to document the ~4,500 test functions: "Name is enough")
- Decision: under DEC-0104, a `test_` function in tests/ whose name has at least four words after `test_`
  (`test_list_alarms_returns_all`) counts as documented: its name says what it proves. A test with a vaguer name
  (one to three words), and every test helper, fixture and class, still gets a real docstring.
  `core.code_atlas.named_as_sentence()` is the rule; `tests/test_documentation.py` checks it.
- Related: DEC-0104, DEC-0110


### DEC-0117: MIA has her own browser, and is taught tasks by being shown
- Status: APPROVED
- Decided by: zac, 2026-11-07 ("MIA needs access to a browser and to be able to safely operate within the browser
  and be taught how to do tasks in the browser"; then chose: her own Edge profile, read and navigate freely,
  show her then she practises)
- Decision: MIA drives Microsoft Edge through Playwright in a profile of her own, one per person, in their folder,
  with none of their own sign-ins. She reads, searches, follows links and types into ordinary fields by herself.
  Anything that commits (submit, buy, send, sign in or up, delete, download, accept, and any button not plainly
  harmless) waits as the action `browser.commit` with a screenshot, approved by the person on a screen or by a yes in
  code, never by the model. She never types into password, card, bank or ID fields: the person signs in themselves.
  Tasks are taught by doing them once in her window (steps kept by label, passwords never), replayed with each
  commit waiting, and learned after two clean runs in a row (`browser.runs` loop).
- Where: `core/browser_safety.py`, `core/browser.py`, `core/browser_routines.py`,
  `core/assistant_browser_actions.py`, `docs/BROWSER.md`, `tests/test_browser.py`
- Related: DEC-0012 (the web front end and its actions), DEC-0094 (loops), DEC-0112 (learning paths: the same practise-until-verified shape)

### DEC-0118: Humor she can turn up or down, and a plans shelf in the Library
- Status: APPROVED
- Decided by: zac, 2026-11-07 ("I also want her to be funny sometimes... it would be nice to be surprised by it";
  "she can adjust her humor level if asked to in a chat"; "MIA should have in her Library references for all kinds of
  stuff like woodworking plans, structure blueprints, material lists")
- Decision: (1) Code decides when a light turn gets a nudge toward one line of wit, by chance and in a random flavor,
  never on heavy, worried, grieving, urgent, faith or private turns (`core.personality.humor_for`). Each person sets
  how often by asking (off, rare, sometimes, often, lots; `set_humor`), and "off" means no jokes at all.
  (2) The Library gains a plans shelf (`core/plan_library.py`): built-in plans whose material lists and cut lists are
  worked out in code for any size (`core/build_calcs.py`: stud wall, floor, deck, raised bed, fence, slab, gable shed,
  workbench), plans the household keeps, and plan files dropped into `reference_library/plans/`; checked against the
  workshop's materials for what to buy; a project started from a plan; links to free public-domain and extension
  plans. Structural sizes are rules of thumb, always with "check your local code and a span table".
- Related: DEC-0114 (personality), DEC-0115, DEC-0017 (the Library's web page)

### DEC-0119: MIA is for Zac alone, never for children
- Status: APPROVED
- Decided by: zac, 2026-11-07 ("MIA will never be for children. Shes really just for me"; "we can also remove all
  info regarding child accounts")
- Decision: MIA is built for Zac only. No new work for child accounts or for other people in the house: new modules
  and tool domains no longer need a place in `CHILD_APPS` / `CHILD_BLOCKED_DOMAINS`, and design briefs leave child
  and household-member states out. Narrows DEC-0115.
- What stays for now: the code already built for accounts, households and children keeps working and its tests
  stay; removing `core/child_accounts.py` and the per-person plumbing is a separate cleanup Zac approves on its own.
  No personal data in the repo still holds (DEC-0002).
- Related: DEC-0115, DEC-0001, DEC-0002

### DEC-0120: MIA reads Zac's own mailbox for receipts, and receipts do things
- Status: APPROVED
- Decided by: zac, 2026-11-07 ("I want MIA able to read my emails so she can use it to gain context on things
  getting done, being purchased... see my receipt and know I got my oil changed or bought groceries and stock my
  pantry with what's on the receipt, and same for Lowe's receipts and materials")
- Decision: (1) The inbox's email intake gains an everyday-mailbox mode (`core/inbox_mail.fetch_receipts`): the
  folder is opened read-only and messages fetched with PEEK, so nothing is marked read, moved or deleted; only
  receipts, orders and service confirmations are taken, judged from sender and subject, and other mail is never
  downloaded. (2) A receipt's meaning is worked out in code (`core/receipt_effects.py`): groceries stock the pantry
  and tick the grocery list, a car service is marked done on the vehicle (with the odometer when shown), building
  supplies add to the workshop's materials at the price paid. (3) As with everything in the inbox, nothing happens
  until Zac files it; the effects come ticked and he can untick any.
- Also: DEC-0119's child-account code stays (Zac: "fine to leave"); it reaches MIA's prompts only when a child is
  signed in, so it can't confuse her.
- Related: the inbox (2026-09-28), DEC-0030 (receipt lines), DEC-0119

### DEC-0121: Emailed receipts file themselves; every filing can be undone exactly
- Status: APPROVED
- Decided by: zac, 2026-11-07 ("I want the actions from reading the emails to not need my approval every time... that
  feature should be automated, but should still have a clear way to undo them if it gets it wrong")
- Decision: an emailed receipt is filed on MIA's own (`InboxManager.auto_file`): its expense and ticked effects
  (pantry, service done, materials) happen without a proposal. It waits instead when the same amount is already
  logged (a forwarded copy, or an order email and its receipt), when it's an invoice (a bill still to pay), or when
  automatic filing is turned off (`inbox.auto_file`, by asking her). Every filing keeps exactly what it did, so Undo
  (`inbox.unfile`: the Inbox's "Filed by MIA" list, or "undo the Kroger receipt") takes back just that, any time,
  leaving later changes alone, and the receipt waits again. An undone automatic filing counts as correcting her
  (core/corrections.py). Amends DEC-0120's "nothing happens until filed" for emailed receipts.
- Related: DEC-0120, DEC-0012 (actions), DEC-0094 (loops)

### DEC-0122: MIA's browser types and searches only the person's own words
- Status: APPROVED
- Decided by: zac, 2026-11-07 (his review of DEC-0117: "ordinary text fields can potentially send information to a
  website before a commit gate is reached. I'd tighten this so MIA only types information you've authorized for that
  task")
- Decision: on her own, MIA's browser types, chooses or searches only words the person said to her in the last 30
  minutes (`core/browser.Browser.hear`, fed every turn, never a private journal turn) or words from a task they taught
  her by doing it. Anything else, a search they didn't word, or an address carrying such words after a `?`, waits as
  a `browser.commit` with the exact text shown. Closes the known limit in docs/BROWSER.md.
- Related: DEC-0117

### DEC-0123: One way to teach MIA anything: taught procedures
- Status: PROPOSED
- Proposed by: claude, 2026-11-07, from Zac's review ("Browser routines are now teachable, but they're not yet the
  same thing as a universal skill system that can teach MIA workflows across desktop apps, phone features, and
  other tools")
- Proposal (`docs/PROCEDURES_PROPOSAL.md`): one engine for taught procedures: a trigger (asked, scheduled, or an
  event), steps of any kind she can already do (her tools, action kinds, her browser, questions, steps only the
  person can do; later phone features and desktop apps), each through the gate that already governs it, practised
  with the person watching until two clean runs, then learned and allowed to run unattended. Taught by doing it
  with her ("watch me"), by telling her, or by her offering after seeing a repeat. Browser routines and workflows
  fold into it. Phases: engine and chat teaching; triggers; phone steps; desktop apps (its own decision); glasses.
- Open: the direction, the name (Skills and Routines are taken), phase 1 first, which desktop apps matter.
- Related: DEC-0092 (workflows), DEC-0112 (learning paths), DEC-0117, DEC-0121, DEC-0122

### DEC-0124: The desktop opens on the web front end
- Status: APPROVED
- Decided by: zac, 2026-11-07 ("the only way I am able to view most of MIA is through the Home Preview app. I think a
  lot of her isn't really presented and usable in this state")
- Decision: MIA's desktop window opens on the web front end edge to edge (web mode: no classic header or character
  panel; the web's own sidebar, Talk and screens). The window itself stays, for what it does beyond the page
  (notifications, the email draft dialog's Send, apps opened by voice, kiosk mode, switching person). The Qt screens
  are the classic view: Ctrl+Shift+C, or opening an app that lives only on the PC (Power, Toolbox, The Lab, Field
  Kit), which the web Apps page now offers as "Open on this PC" inside the desktop. "Main screen" or Ctrl+Shift+C
  goes back. `gui.web_first` false keeps the old start. Carries DEC-0017 to the desktop.
- Related: DEC-0012, DEC-0013, DEC-0017, DEC-0023

### DEC-0125: Full use both ways, on every device
- Status: APPROVED
- Decided by: zac, 2026-11-07 ("MIA should be absolutely 100% voice capable but I also want 100% capable for use on
  the phone too. I want full use when I feel like talking and full use when i don't on all devices glasses, phone,
  pc, etc. We will just have to adjust how we present it for each devices specs")
- Decision: every feature can be used fully by voice and fully without it, on the PC, the phone and the glasses (and
  voice-only). Every action has twins: a tool she can use when asked, and a control on a screen. A device changes
  how a feature is presented (the glasses get a card and an ask, the phone a page sized for a thumb), never whether
  it can be used. `core/parity.py` measures it app by app (voice, PC, phone, glasses); every gap is decided in
  `work/parity.json`, to build or deliberately not, and a test fails on one nobody decided about, so parity only
  grows. `docs/PARITY.md` is the table. The one exception (Zac, 2026-11-07: "yes keep passwords screen only"):
  passwords, PINs and card numbers are never spoken, heard or shown on the glasses; they stay on a screen.
- Related: DEC-0017, DEC-0062, DEC-0124

### DEC-0126: MIA encrypts her own data at rest
- Status: APPROVED (Zac, 2026-11-08: "lets knock these out", on the list this headed), with DPAPI and no passphrase
  for now; the optional passphrase stays open
- Proposed by: claude, 2026-11-08, from Zac's ask ("fortify our security measures to industry standards and beyond so
  that users can safely trust this AI and the app having access to their most private data") and the check that this
  PC's drive isn't encrypted (Windows 11 Home, BitLocker protection 0)
- Proposal (`docs/SECURITY.md` section 4, step 2): every store's file encrypted with AES-256-GCM under one data key,
  in the one place stores already write through (`core/atomic_write.py`) and a matching read; the data key protected
  by Windows DPAPI on the PC (tied to the Windows sign-in: nothing to type at start) and the Android Keystore on the
  phone, with an optional MIA passphrase on top. Moved store by store, the most private first (journal,
  conversations, memories, money, people), each readable both ways until it's moved. Separately, Zac turns on disk
  encryption (Device encryption, BitLocker with Windows Pro, or VeraCrypt).
- Open: whether to add the optional passphrase (asked at each start, or only for the most private stores); the
  order of stores.
- Built, stage 1 (2026-11-08, `core/at_rest.py`): conversations, memories, notes and life notes sealed with
  AES-256-GCM in `atomic_write_text`, read both ways by `at_rest.open_text`; the key protected by DPAPI in
  data/.keys/; a recovery key (`python -m tools.data_key recovery`) for another Windows account or PC; a file that
  won't open is copied aside before its store can start empty; sync and the account export carry the real content.
  The private journal and the password vault were already encrypted with their own passphrases.
- Built, stage 2 (2026-11-08): people and pets, financial snapshots, insurance, GPS tracks and the operating journal;
  every sealed store tested to start empty (copy kept) rather than stop MIA when its file won't open, which caught
  three stage-1 stores that would have. Next: the budget's files (after the Plaid work in budget_manager.py), the rest
  of PERSONAL_STORES, the phone's Keystore.
- Related: DEC-0035 (the password vault), DEC-0125

### DEC-0127: MIA becomes a product, sold by subscription, local-first
- Status: PROPOSED
- Proposed by: zac, 2026-11-08 ("We should plan for what it would take to get this polished and built to standards so
  that it is ready for selling... something that connects to a users phone and pc and doesn't store any of their
  data anywhere else... a paywall for access on a monthly subscription"; "Her files should be safe so that someone
  couldn't just bypass the paywall or copy her")
- Proposal (the plan: https://claude.ai/artifact/CXMdLtnXhy4XzUMAW4aLLR): MIA is sold as a monthly subscription that
  keeps each customer's data only on their own PC and phone; we run only billing (a payment provider), a tiny
  license check, and static downloads. Licenses are signed and checked offline with a grace period and a device
  limit; release builds are compiled, signed and self-checked; updates and new connectors need a valid license.
  Reverses DEC-0119 (MIA for Zac alone): Zac's own copy stays his.
- Open: price and trial; platforms at launch; bank linking (a small Plaid server, or CSV only); Tailscale or a relay
  away from home; the payment provider; a trademark search on the name.
- Related: DEC-0115, DEC-0119 (reversed if approved), DEC-0126, docs/SECURITY.md


### DEC-0128: MIA across your technology — Field Kit grows up
- Status: PROPOSED
- Proposed by: claude, 2026-11-08, from Zac's ask (MIA should "intuitively be able to communicate with other
  technologies… recognize them… install herself, and operate on my device," with real "cyber security" and the
  ability to "access and manipulate / merge with other technologies"), sharpened by the Echo Show turning out to be
  unconvertible — the lesson being that reliable interop comes from protocols and credentials you hold, not exploits.
- Proposal (`docs/DEVICE_FABRIC_PROPOSAL.md`): grow the existing Connected Device Framework (USB/serial, built) to
  the whole network. Four layers on `context.devices`: **perceive** (mDNS/SSDP/ARP/BLE discovery → a device
  inventory store), **identify** (make/model + capability profile + known CVEs, reusing the dependency-audit vuln
  pattern), **speak** (per-protocol adapters: Cast, DLNA, Home Assistant/MQTT, SSH to Zac's own hosts), **extend**
  (install MIA onto the Pi via the existing kiosk service, cast her panel to a screen, flash+provision behind the
  built flashing safety rails). Security role split: **defensive** home-network audit always on through the comms
  gate; **offensive/authorized testing** only against an owner-authorized target list, every intrusive action a
  person-approved `fabric.commit` (modelled on `browser.commit`), logged — no third-party targets, mass scanning,
  DoS or evasion (out of scope, not gated). First build is the read-only defensive half (discovery + identify +
  audit + a Field Kit screen), which needs no gate decision.
- Open: inventory scope (household vs device-level); how far into active testing and against which devices; Smart
  Home via Home Assistant or direct adapters; whether the inventory is sealed at rest (DEC-0126) — proposed yes.
- Related: DEC-0117 (the browser gate this copies), DEC-0126, DEC-0094/0101 (loops); ROADMAP 11 (Field Kit), 13
  (Smart Home); `core/dependency_audit.py`, `core/device_framework.py`, `core/port_scanner.py`


### DEC-0129: Areas and hubs — how MIA's apps are organized
- Status: ACCEPTED
- Decided by: Zac, 2026-11-08 00:14–00:25 (in conversation with claude), replacing the audit's seven-area proposal
  (Claude Doc 56xyaTxEQThT1vrYh484Ay).
- Decision: the sidebar is the **Dashboard**, then fifteen areas: Home, Garage, Plants and Animals, Health and
  Fitness, Recreation (Zac's rename of Adventures; Music goes here too), Security, Browser, Settings and
  Diagnostics, Finances, Business, Personal, Learning, Missions, Projects, Communications. Each area has its own
  **hub** screen (`hub.html?area=<id>`). An app can belong to more than one area and appears in each hub:
  Calendar (Personal, and on the Dashboard), Skills (Missions and Learning), Real Estate and Compliance (Finances and
  Business), Workshop (Business and Projects), Kitchen with its meal plans (Home and Health and Fitness, 00:27).
- Placements Zac named: Toolbox and Look in Garage (Look is also a button in the chat with MIA), Files in Personal,
  Good News Radio in Personal and as a Dashboard card, Music in Recreation. Pets move out of People into Plants and
  Animals; Maintenance shows the house's upkeep in Home (Home Upkeep: Real Estate's Home & Appliances tab, where buildings and appliances have lived since 2026-10-16) and the vehicles' in Garage (the Garage app is their upkeep).
- The Dashboard gains now playing, today's good news, recent pictures and the current or next trip. Communications
  becomes one screen (email drafts and mailbox, MIA's messages and her held-back ones, the message limit, people).
- Health and Fitness gains sleep, doctor and dentist visits, medications and supplements, and health records (Zac,
  00:25), kept in the person's own profile, sealed at rest (DEC-0126), never on a shared screen.
- Also raised (00:25): an ID wallet in Security for IDs, passports, insurance cards and registrations.
- How: `core/web_areas.py` holds the areas (one place to change), `shell()["areas"]` feeds the sidebar and the Apps
  page, `/api/hub/<area>` the hubs. Every app keeps its own page; only how they're found changed.
- Related: DEC-0113 (the canvas), DEC-0125 (parity), DEC-0126 (sealed data), DEC-0119


### DEC-0130: The Nexus — MIA's spatial home, and area colors
- Status: ACCEPTED
- Decided by: Zac, 2026-11-08 00:41–00:45 (his handoff "MIA — Spatial Interface & Nexus Design Architecture", a
  reference image, and his answers to the four questions in `docs/design/NEXUS_PLAN.md`).
- Decision:
  1. **The Nexus opens first**: a dark chamber with tall portals in an arc, one per area, around MIA's orb on a glowing
     platform, smoky RGB vapor drifting on black, the HUD along the top (Browser, Settings, MIA, Search; portrait,
     level, XP, missions). The Dashboard's day is one step in.
  2. **Portals:** DEC-0129's fifteen areas **plus Kitchen** (its own portal as well as inside Home and Health).
  3. **Area colors amend DEC-0023:** each area has a hue for its portal's frame, its light and its environment's
     ambient glow only. Buttons, selection and focus stay cyan; amber and red keep their meanings (needs you, errors
     and destructive) and are never an area's hue.
  4. **Style:** the 90s/2000s underground and liquid-morphing feel lives in motion (portals forming, environments
     flowing in) and the Nexus's backdrop (vapor, texture); panels and text stay Stark-clean and legible.
  5. Built as shared components (`web/spatial.css`, `web/spatial.js`), 2.5D first, every device at its own depth,
     reduced motion respected. Muse refines the art direction.
- Plan and milestones: `docs/design/NEXUS_PLAN.md`.
- Related: DEC-0023 (amended: area hues), DEC-0014, DEC-0017, DEC-0129
