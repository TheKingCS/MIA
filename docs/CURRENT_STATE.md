# MIA: Current State

*The two-minute "where are we right now?" for every collaborator
(`docs/COLLABORATION.md`). Claude rewrites it at the end of each
session. Last updated: 2026-10-05, by claude.*

## Phase

**Engine ↔ Experience integration.** Engine Phase 1 is done: the engine
now exposes one read model (Life State v2 at `/api/state`) that every
surface consumes (DEC-0005). Next, the designed interface gets
connected to it.

## Where things stand

| Area | Status |
|---|---|
| Desktop app (PySide6, 37 apps) | REAL, in daily development |
| Phone web app (Talk, Today, Money) and Android app | REAL |
| Assistant (local model, ~185 tools, voice) | REAL |
| Life events (history), links, Life State v2 (now with assets, kitchen, workout), `/api/state`, schema | REAL / DERIVED, built 2026-10-05 |
| Muse's desktop design artifact | Design surface, SIMULATED. To be pointed at `docs/schema/life_state.example.json` |
| Meta Display glasses | PLANNED (Phase 2), waiting on Q-0003 |
| MIA's reasoning over Life State ("opportunities") | PLANNED (Phase 2) |
| Collaboration hub (these files) | REAL, started 2026-10-05 (DEC-0010) |

## Who's doing what

- **Zac:** enter real data through MIA, then run
  `python -m tools.export_state` (steps in `docs/NEXT_SESSION.md`).
  Answer Q-0001, Q-0002, Q-0003, Q-0005. Decide DEC-0011 (public repo).
- **Muse:** connect the desktop design to Life State; glasses card
  concepts, following Muse's own Q-0004 answer. Start from
  `docs/HANDOFFS/H-0003_claude-to-muse_where-mia-is.md`.
- **ChatGPT:** vision and architecture review of Phase 1 against MIA's
  original intent (`docs/ENGINE_PHASE1_PLAN.md` §8–9).
- **Claude:** waiting on Zac's next priority. Queue: a real Habits
  module, the glasses client (after Q-0003), Phase 2 reasoning over
  Life State.

## Blocked

- The glasses client: on Q-0003 (platform and access).
- ChatGPT reading the repo: on DEC-0011 / Q-0005.

## Recent changes (newest first)

- 2026-10-05 · claude · H-0004 done: `assets`, `kitchen` and `workout` added to Life State v2, the schema and the example.
- 2026-10-05 · muse · First hub round-trip: answered Q-0004 (Home priorities), filed H-0004 (schema gaps).
- 2026-10-05 · claude · Collaboration hub files (this one,
  `COLLABORATION.md`, `DECISIONS.md`, `QUESTIONS.md`, `HANDOFFS/`).
- 2026-10-05 · claude · Handoff H-0003 to Muse; placeholder example
  Life State.
- 2026-10-05 · claude · Engine Phase 1: life events, links, Life State
  v2, `/api/state`, export command, schema (DEC-0005, DEC-0006,
  DEC-0007).
- 2026-10-01 · claude · Starter sets, child accounts, accessibility,
  ownership, private budget, quick capture, Today, accounts and
  households.

## Open decisions and questions

- DEC-0011 (PROPOSED): make the repo public.
- Q-0001, Q-0002, Q-0003, Q-0005, Q-0006: see `docs/QUESTIONS.md` (Q-0004 closed).

## Constraints everyone works within

No real personal data in the repo (DEC-0002). Facts in code, the model
only phrases (DEC-0004). Surfaces consume `/api/state` and mark
anything else PLANNED (DEC-0005, DEC-0007). The guardrail before every
proposal (DEC-0008). Read, propose, approve (DEC-0009). Only Zac
approves decisions.
