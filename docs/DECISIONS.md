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
- Status: APPROVED (zac, 2026-10-06, in chat with claude)
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
     keeps the sidebar.
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
