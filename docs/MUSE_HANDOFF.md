# Handoff for Muse: where MIA is and how we work

*From Claude Code (the engine side), 2026-10-05, for Muse (the design
side). The owner (Zac) carries files between us, so this is written to
stand on its own. Real personal data never goes in shared files:
everything below uses placeholders.*

## 1. The team

| Who | Role |
|---|---|
| **Zac** (owner) | Decides scope and priorities. Approves every phase. Relays files between us. |
| **Claude Code** | Builds and maintains the engine in the repo (`github.com/TheKingCS/MIA`, private): data, logic, the Assistant's tools, the phone server, tests. Checks whether a design matches what the engine can really do. |
| **Muse** | Designs the surfaces: the desktop look, the phone, and the Meta Display glasses. Owns how MIA looks and feels. |
| **ChatGPT** | Architecture review. Its Oct 2026 handoff set the direction we're on now. |

## 2. What MIA is

MIA (Multifunctional Intelligent Assistant) is an offline-first
personal and household assistant. It runs on the person's own computer
(the target is a Raspberry Pi 5 kiosk) with a small local AI model. It
is **built for anyone**, not just Zac: people sign in with an email,
each person's data is their own, and a household shares only what its
members agree to. Child accounts are looked after by a parent.

Core principles. These don't change, and designs need to respect them:

- **Facts come from code, not the model.** Totals, dates, what's due
  and what's overdue are all calculated in code. The AI only phrases
  facts and proposes things; it is never where the facts are stored.
- **Read, propose, approve.** MIA suggests and the person decides.
  Nothing happens silently. Emails are only drafted, never sent without
  the person pressing Send. Every change MIA makes can be undone
  ("undo that").
- **Local-first and private.** Data lives on the device. The phone talks
  to the person's own MIA, not a cloud.
- **MIA speaks up rarely.** Unprompted messages go through a
  "communication gate": a limit per day, no repeats, and "why did you
  tell me that?" always works.
- **Safety never depends on the AI.** Crisis replies are fixed text in
  code, with the person's country's numbers.

## 3. The most important thing: the repo is MIA, the mock-up is a design

Your desktop artifact (`mia-desktop`) is a **design surface**. It's
static and simulated. The real MIA already exists and works in the
repo: 37 apps, about 180 Assistant tools, a phone web app and an
Android app, all on real data, with 4,100+ automated tests.

So the gap isn't "MIA is missing features". It's that **the designed
interface and the real engine haven't been connected yet.** Zac and
ChatGPT agreed on this model:

```
                    MIA ENGINE (the repo)
        CURRENT STATE    HISTORY    RELATIONSHIPS
                    \      |      /
                     LIFE STATE V2
                           |
                  MIA REASONING (Phase 2)
                           |
            MISSIONS · SKILLS · PRIORITIES
                           |
              PROPOSALS → COMMUNICATION GATE
                           |
   DESKTOP · PHONE · ANDROID · MOCK-UPS · GLASSES   ← all consumers
```

Every screen is a consumer of MIA, not a separate version of it. Before
designing a screen, ask: **"What does MIA already expose that this can
show?"** Ask that before "what should I put on this screen?".

## 4. What exists today (all real, all in the repo)

**The desktop app** (PySide6). These are its apps:

- **Home:** Dashboard, with a Today card and widgets.
- **The Assistant:** chat and voice, with a character panel.
- **Life:** Missions, Skills, Character, Household (chores), Workout,
  Kitchen, Notes, Memories, People & Pets, Classroom, Knowledge, Music.
- **Money and property:** Budget (bills, income, debts, business
  entities), Real Estate, Inbox (documents filed from email and photos).
- **Upkeep and making:** Maintenance (vehicles, tools, appliances), Garage, Property, Greenhouse,
  Workshop & Electronics, The Lab.
- **Outdoors:** Maps, Navigation, Expeditions, Field Kit.
- **Device:** Power, Diagnostics, Files, Toolbox, Observations,
  Settings, Modules.

**The phone:** a web app (tabs: Talk, Today, Money) and an Android app.
Both sign in with the person's own account and talk to their own MIA.

**Engine services the designs can rely on:**

- Today: overdue, today, waiting and soon, across every app.
- The finance summary: the month, bills due, debts ranked, net worth,
  build costs.
- Missions with XP and per-skill progress.
- Recurring routines with streaks.
- Goals ("intents") with the reasons behind them.
- Ownership ("whose truck is it").
- Undo, quick capture, imports (calendar, contacts, bank files),
  starter sets, accessibility (text size, high contrast, read aloud).
- Households, private budgets, child accounts.

## 5. What we just built: Engine Phase 1 (approved by Zac, 2026-10-05)

This is the connective tissue the kickoff spec asked for, added beside
what exists instead of rebuilding it:

1. **History.** MIA now records what happens: bills paid, missions
   completed (and which skills they trained), workouts, meals,
   maintenance, rent, tasks and projects finished, imports, undos. Each
   entry notes who did it and how (by hand, by MIA, by import). You can
   ask "what did I get done this week?".
2. **Links.** How things relate: a loan FUNDS a property, a project
   DEPENDS_ON a sale, a mission is EVIDENCE_FOR a skill. Someone can
   say "the greenhouse depends on selling the lot" and then ask "what
   depends on selling the lot?".
3. **Life State v2.** One computed picture of the person's life (see
   section 6).
4. **The read model.** That picture, served to every surface (section 6).

Full details: `docs/ENGINE_PHASE1_PLAN.md` (sections 8–9).

## 6. The contract between design and engine: Life State v2

**Where it comes from:**

- **Phone, mock-up or glasses:** call `GET /api/state` on the person's
  own MIA, signed in with a token from `POST /api/login`.
- **A file on the device:** `python -m tools.export_state` writes one.
- **The shape:** `docs/schema/life_state.schema.json` (JSON Schema
  2020-12). The tests enforce it, so it can't silently change.
- **A full sample to design with (placeholder data):**
  `docs/schema/life_state.example.json`. Please render the mock-up from
  this file instead of hardcoded content.

**The sections.** Every section carries `status` and `source`:

| Section | What's in it | Design notes |
|---|---|---|
| `person` | name, household, whether it's a child account | Child accounts never get money or property. Design a child variant. |
| `finances` | the month (in/out/net), bills due, expected income, budget targets, debts ranked, net worth, build and tool costs, **monthly plan** (income vs. bills + debt minimums → gap) | Use `currency_symbol`, never a hardcoded "$". |
| `properties` | each property: type, value, mortgage, equity | |
| `projects` | open projects: tasks open/done, the goal each one supports, what it's **waiting on** | |
| `due` | items marked `overdue` / `today` / `waiting` / `soon`, each with a title, detail, time, icon and the app to open | This is the glanceable core for the phone and glasses. |
| `missions_and_skills` | active missions, streaks, skills growing / declining / dormant, MIA's open observations | |
| `recent_wins` | last 7 days: counts by type plus the latest entries (each with a one-line summary) | Celebratory, not noisy. |
| `friction` | what's in the way: overdue things, waiting projects, a negative money gap, over-budget categories | Honest, calm, never alarming. |
| `goals` | active goals, what serves each one, and **chains** like `["Vacant lot", "Greenhouse", "Solar"]` | A natural "questline" visual. |
| `links` | how many links there are | |
| `opportunities` | **PLANNED**: MIA's reasoning over this state comes in Phase 2 | Show as "coming", or leave it out. Never fake it. |

**What the statuses mean for design:**

- **REAL / DERIVED:** show normally. These are true, computed facts.
- **STATIC:** fixed text, such as a child account's "money isn't shown
  here".
- **SIMULATED:** must be visibly marked if it's ever shown.
- **PLANNED:** greyed out with a "coming" tag, or not shown at all.
  Never present a PLANNED capability as working.

## 7. Design rules (do and don't)

**Do:**

- Design every screen from the fields in section 6. If a field isn't in
  the schema, it doesn't exist yet.
- Mark anything the engine doesn't have as PLANNED, and send it to
  Claude as a proposal (section 9).
- Design for anyone: placeholder names ("Robin", "Rental A", "Lender
  A"), any currency, a child variant, and accessibility (large text and
  high contrast are real settings).
- Keep MIA's voice: warm, brief, calm. She proposes and the person
  decides, so give every MIA suggestion an approve or dismiss control.
- For the glasses: short glanceable cards (what's due, the next
  mission, a win, one friction item) and voice. The engine side
  already exists: `/api/state` for the cards, plus the phone's voice
  endpoints.

**Don't:**

- Hardcode real personal data (names, addresses, loans, lenders,
  amounts) in a mock-up, spec or prompt. Zac's real data enters through
  MIA itself and stays on his device.
- Invent numbers, totals or "insights" in a screen. Numbers come from
  the state, and insights come from MIA (Phase 2).
- Design a button that acts without the person's approval: no silent
  actions and no auto-sending.
- Rebuild something because the mock-up doesn't show it. Check section 4
  first; it probably exists.

## 8. The guardrail: ask this before every new proposal

This was agreed with Zac and ChatGPT. Claude runs every proposal
through it, and it helps if Muse does too:

1. Does MIA already support it?
2. If so, where?
3. If not, is it really missing, or just not shown yet?
4. If it's missing, does it belong in the engine or only in the UI?
5. Can it be added without duplicating an existing system?
6. Does it need to be part of Life State?
7. Does it create a history entry?
8. Does it create or use links?
9. Should `/api/state` expose it?
10. What is its status: REAL, DERIVED, SIMULATED, STATIC or PLANNED?

## 9. What to send back to Claude (via Zac)

For each screen or card, a short handoff like this:

```
Screen: Glasses – morning card
Shows:  due.items (first 3, overdue first), missions_and_skills.active_missions,
        recent_wins.counts
Actions: "done" on a due item → (engine: mark bill paid / task done, needs approve)
Missing from the engine: none   |   or: "weather line" → PLANNED, proposal attached
Statuses shown: DERIVED
```

Claude will then wire it up, or say exactly what's missing and propose
how the engine should provide it.

## 10. What would help most next (Muse)

1. **Point the desktop artifact at real data:** render its domain views
   from `docs/schema/life_state.example.json`, and mark anything not in
   the schema as PLANNED.
2. **Meta Display glasses cards:** a small set of glanceable cards built
   from `due`, `missions_and_skills`, `recent_wins`, `friction` and
   `goals.chains`, plus a voice flow. Engine support for the glasses
   comes in Phase 2. Before Claude builds that client, Zac needs to
   confirm developer access to the glasses platform and what it
   supports.
3. **A "questline" view:** `goals.chains` and `projects.waiting_on` show
   what has to happen in what order.
4. **A child-account variant** of whichever screens a child would see.

## 11. Open questions (Zac decides, no rush)

- Missed-daily penalty style: harsher penalties, or streak-loss only?
  (Today MIA does streak-loss only.)
- When a child triggers the crisis reply, should MIA also tell their
  parent? (Today it doesn't; it tells the child to talk to an adult
  right away.)
- The glasses: which developer platform, and what it allows (display,
  voice, notifications).

## 12. Where things live (for reference)

| What | Where in the repo |
|---|---|
| The plan and decisions for this phase | `docs/ENGINE_PHASE1_PLAN.md` |
| The state's shape and a sample | `docs/schema/life_state.schema.json`, `docs/schema/life_state.example.json` |
| Everything the Assistant can do | `docs/ASSISTANT_CAPABILITIES.md` |
| The running to-do list between sessions | `docs/NEXT_SESSION.md` |
| What was built and why | `docs/ROADMAP.md` |
| The long-term vision | `docs/VISION.md` |
| User-facing help | `docs/user_help/` |
