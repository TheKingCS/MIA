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
- Status: PROPOSED
- Proposed by: claude, 2026-10-05 · Review requested: chatgpt, muse · Approval: zac
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
