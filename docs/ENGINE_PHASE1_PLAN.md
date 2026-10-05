# MIA Engine Phase 1: response to the kickoff spec

*Claude Code, 2026-10-05. Replies to "MIA Engine Kickoff Spec" (drafted
by Rocky/Muse, 2026-10-05). For the owner, Muse and ChatGPT.*

> **Status (2026-10-05): approved and built.** The owner said yes to all
> three questions (section 6), and steps 1–4 are built and tested. See
> section 8 for what exists now and how the acceptance criteria came
> out, and section 9 for the checklist every new proposal goes through.

## 1. The short version

The spec's direction is right: services, not pages; deterministic code
for facts and money; the model reasons over structured state and never
*is* the state; read, propose, approve. That has been MIA's rule since
the start (CLAUDE.md, `docs/ARCHITECTURE.md`).

The spec was written from the design side, though, so it misses that
**most of the engine already exists in this repo**: about 175 core
services, 37 modules, ~180 Assistant tools, a phone server, and 4,100
passing tests. The desktop artifact is a mock-up. The real MIA is the
PySide6 app in this repo plus the phone web app and Android app, and
they already run on real stored data.

So Phase 1 is smaller than the spec suggests: fill four real gaps
(section 3), and don't rebuild what's working. Three parts of the spec
conflict with how MIA is built and need the owner's call first (section 4).

## 2. Already built (REAL, in this repo)

| Spec asks for | What exists today |
|---|---|
| Life State v1 | `core/context_assembler.py` (missions, streaks, skills growing/declining, insights, overdue maintenance, projects) |
| Typed entities | Every domain has typed records with ids and its own store: people and pets (`relationships_manager`), properties (`real_estate_manager`), vehicles/tools/appliances (`maintenance_manager`), bills, income, expenses, debts, business entities (`budget_manager`), projects/tasks, missions, skills, intents, memories, observations, recipes/pantry, workouts, calendar events |
| Some relationships | OWNS: `owner_profile_id` on assets (`core/ownership.py`). COSTS: expenses tagged to builds and tools. EVIDENCE_FOR: mission → skill XP. SUPPORTS: intents serve bigger intents with reasons (`core/why_graph.py`). Business tagging of transactions. |
| Mission → skill accrual | Completing a mission writes skill XP (`mission_manager.py`) to an append-only `skill_xp_log.json` with timestamps |
| Derived "due" views | `core/today.py` (overdue/today/soon across bills, maintenance, tasks, calendar, birthdays, pantry), `core/finance_summary.py` (net worth, debts ranked, cash flow, builds) |
| JSON for other surfaces | The phone server (`server/app.py`): `/api/today`, `/api/finance/summary`, chat, voice, email drafts. Signed-in, per person. |
| Facts vs intentions | Intents (`intent_manager`) are separate from memories, observations and facts; the why-graph keeps reasons separate from the things they explain |
| Propose, then approve | "Propose-you-confirm" updates from passing mentions; email is drafted only, never sent without a person pressing Send; undo for every Assistant change (`core/undo_log.py`) |
| **Spec calls these Phase 2, but they're built** | The communication gate (`core/communication_gate.py`: rate limits, merging, "why did you tell me that?"), the safety floor, cross-module Today, households and per-person data, child accounts, starter sets |

The spec also mentions `generate_missions()` and a "mia-wearables
exporter". Neither exists in this repo. They're from another
conversation or the artifact, so they'd be new work.

## 3. The real gaps (what Phase 1 should build)

1. **One activity log (EventStore).** Today, history is scattered: XP
   log, mission completions, bill "paid" dates, workout sessions, the
   communication log, undo (in memory only). Build
   `core/activity_log.py`: an append-only, per-household JSONL log with
   `{at, type, refs, payload, source}`, where `source` is one of user,
   manual, import, inferred or assistant. Existing managers record their
   meaningful changes into it (bill paid, mission completed, workout
   logged, expense added, maintenance done, imports). Queries: "what
   changed this week?", "what did I get done this month?".
2. **Cross-store relationships.** An index of typed links between
   existing records, `kind:id → kind:id`, using the spec's relationship
   names (OWNS, LOCATED_AT, PART_OF, COSTS, FUNDS, GENERATES_INCOME,
   DEPENDS_ON, BLOCKED_BY, EVIDENCE_FOR, SUPPORTS, RELATED_TO). For
   example, a debt FUNDS a property, rental income comes from a
   property, a project DEPENDS_ON a sale. The records themselves stay
   where they are; the index only holds the links.
3. **Life State v2.** Extend `context_assembler.py`, don't fork it. Add
   finances (from `finance_summary`), properties, what's due (from
   `today`), recent wins (from the activity log), friction (overdue,
   blocked, a monthly gap) and active questlines (intents and their
   chains). All of it is computed, with no prose in the path.
4. **State export and schema.** `python -m tools.export_state` (and a
   `/api/state` endpoint for the phone, artifact and glasses) writes
   Life State v2 and the domain views as JSON. It validates against a
   published `docs/schema/life_state.schema.json`. Every section
   carries a status label: REAL, DERIVED, SIMULATED, STATIC or PLANNED.

Phase 1 acceptance criteria, adapted:

1. One command prints Life State JSON computed from stored data.
2. Marking a bill paid (through MIA, the phone or the Assistant)
   removes it from the "due" view and adds a `bill_paid` entry to the
   activity log. The first half already works today.
3. Completing a mission logs evidence for each linked skill. This
   already works; Phase 1 adds the activity-log entry and exposes it in
   the export.
4. Every section of the export has its status label.
5. The export validates against the schema, and the artifact renders
   from it.

## 4. Where the spec conflicts with MIA (the owner decides)

**a. The seed data must not go into the code or the repo.** MIA is
built for anyone, and each person's data is their own (CLAUDE.md:
"Never hardcode the owner's names, places or things in code or
prompts"). Real addresses, loan amounts, lenders and family names in
a spec, a seed script or a test would ship to every MIA. They'd also
sit in git history forever, even in a private repo.
*Proposal:* the owner enters it the way any user would: in Budget, Real
Estate, Maintenance and People & Pets, or by telling MIA ("the mower
payment is $30 a month"). An optional one-time
`data/seed.json` that the owner fills in locally also works. `data/` is
already kept out of git. MIA itself then holds the facts, and so does
the export.

**b. "Events are the ONLY way state changes" means rewriting every
store.** True event sourcing would mean replacing ~30 working stores and
their 4,000+ tests. That contradicts the spec's own "extend, don't
rebuild."
*Proposal:* the activity log sits *alongside* the stores. Every
meaningful change is recorded there with its source, but the stores
stay the source of truth for current state. You still get "what
changed?" and "why did my finances improve?", with a fraction of the
risk.

**c. "What's going on with [the owner]" becomes "with whoever is signed in."**
MIA has accounts, households, private budgets and child accounts now.
Life State and the export are per person and per household, served
only to the signed-in person, like the phone API is today.

Smaller notes:

- **A copy of every entity in a new store** would be a second source of
  truth that drifts. The relationship index (gap 2) gets the same
  queries without copying.
- **The artifact is the shell, not "the living spec."** The real UI
  already exists and works. Treat the artifact as a design reference
  and as one more consumer of `/api/state`, labeled SIMULATED wherever
  it shows something the engine doesn't have.
- **Glasses (Meta Display) are a surface, so Phase 2.** They need
  exactly what the phone already gets: short glanceable cards (Today,
  next mission, what's due) and a voice turn. Once `/api/state` exists,
  a glasses app is a thin client over it plus the existing
  `/api/voice` and chat endpoints.
- **Missed-daily penalty style** is still open. Today MIA does
  streak-loss only.

## 5. Build order

1. Activity log, plus recording from the managers that matter most:
   budget, missions, workouts, maintenance, imports. Tests.
2. Relationship index, plus links that already exist implicitly
   (ownership, expense→build, mission→skill, intent→intent). Assistant
   tools: "link the land loan to the rental", "what depends on
   selling it?". Tests.
3. Life State v2 in `context_assembler.py`, with status labels. Tests.
4. Export command, `/api/state` and the JSON schema. Schema-validation
   test.
5. The owner enters their real data through MIA (section 4a). Then the export
   shows his real state, computed, with nothing hand-written.

Each step is its own commit with tests, like everything else in this
repo.

## 6. Questions for the owner

1. Seed data: enter it through MIA (or a local `data/seed.json`), not
   in the repo. OK?
2. Activity log alongside the stores, not full event sourcing. OK?
3. Start building steps 1–4 now?

## 7. For Muse and ChatGPT: how to work with this repo

- Design new screens against services that exist. Section 2 lists them;
  `docs/ASSISTANT_CAPABILITIES.md` lists every Assistant tool.
- If a design needs data the engine doesn't have, say so in the
  handoff, and mark it PLANNED in the mock-up.
- Don't put real personal data in specs, mock-ups or seed files. Use
  placeholders ("Home", "Rental", "Lender A").
- `docs/NEXT_SESSION.md` is the running to-do list, and
  `docs/ROADMAP.md` records what was built and why.

## 8. Built (2026-10-05)

The model the owner approved:

```
CURRENT STATE   the existing stores (unchanged; the source of truth)
HISTORY         core/life_events.py      what happened
RELATIONSHIPS   core/links.py            how things relate
DERIVED         Life State v2            core/context_assembler.py
READ MODEL      /api/state, python -m tools.export_state,
                docs/schema/life_state.schema.json
```

| Piece | Status | Where |
|---|---|---|
| Life events: bill paid, income, expense, debt payment, mission completed, skill evidence, workout, meal, maintenance done, rent, property expense, task done, project finished, import, starter set, undo. Each has refs, payload, source (manual, assistant, import...) and who. | REAL | `core/life_events.py`, recorded by the stores themselves |
| Links: stated (per household, undoable) and derived from fields the stores already have (ownership, task in project, maintenance task on asset, things in a business, project or goal supporting a goal, mission as evidence for a skill, a property's upkeep record) | REAL / DERIVED | `core/links.py` |
| Life State v2: finances and a monthly plan, properties, projects (what they support and wait on), due, missions and skills, recent wins, friction, goals and waiting chains, links, opportunities | DERIVED (opportunities: PLANNED) | `core/context_assembler.py` |
| Read model | DERIVED | `/api/state` (signed-in, per person), `python -m tools.export_state`, `docs/schema/life_state.schema.json` |
| Assistant | REAL | "what did I get done this week?" (`get_life_events`), "the greenhouse depends on selling the lot", "what depends on selling the lot?" (`link_things`, `get_links`, `unlink_things`), "what's going on with me?" now answers from v2 |

The acceptance criteria:

1. **One command dumps Life State JSON:** `python -m tools.export_state`
   (add `--out file.state.json` to save it; those files are git-ignored).
   Done.
2. **Paying a bill clears it from "due":** marking it paid records
   `bill_paid` and drops it from `due` and `friction`. Tested in
   `tests/test_life_state_v2.py`.
3. **A mission logs skill evidence:** completing it logs
   `mission_completed`, plus a `skill_evidence` entry for each skill that
   really gained XP. It also appears as an EVIDENCE_FOR link. Tested.
4. **Every section is labeled:** each one carries `status` and `source`.
   Done.
5. **The export matches the schema:** checked in
   `tests/test_state_export.py` (full, child and empty states, and the
   phone's `/api/state`). The mock-up can render from it.

Kept as decided: the stores stay the source of truth, and the history
sits beside them. Undo adds an `undone` entry instead of erasing
anything. The history follows the data (a household's events go in its
folder, a person's own in theirs, a private budget's stays private). A
child never sees money in the history or in Life State. No personal data
went into the repo: the tests use placeholders.

**Next, when the owner wants it:** enter the real data through MIA
(section 4a), then look at `python -m tools.export_state`. After that,
Phase 2: the mock-up and the glasses read `/api/state`, and
"opportunities" gets MIA's reasoning over this state.

## 9. The guardrail: every new proposal goes through this

Agreed with the owner and ChatGPT (2026-10-05), so the design and the
engine don't drift apart. For each proposed screen or feature:

1. Does MIA already support it?
2. If so, where (file, service, `/api/...`)?
3. If not, is it really missing, or just not shown yet?
4. If it's missing, does it belong in the engine or only in the UI?
5. Can it be added without duplicating an existing system?
6. Does it need to be part of Life State?
7. Does it create a life event?
8. Does it create or use links?
9. Should `/api/state` expose it (and the schema describe it)?
10. What is its status: REAL, DERIVED, SIMULATED, STATIC or PLANNED?

Surfaces (desktop, phone, Android, mock-ups, glasses, voice) consume
MIA. None of them is a second implementation of it. A surface shows a
capability MIA doesn't have only when it's marked PLANNED.
