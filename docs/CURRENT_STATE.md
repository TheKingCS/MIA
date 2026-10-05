# MIA: Current State

*The two-minute "where are we right now?" for every collaborator
(`docs/COLLABORATION.md`). Claude rewrites it at the end of each
session. Last updated: 2026-10-05 (Phase 2 foundation), by claude.*

## Phase

**Phase 2, "Experience" (DEC-0012, DEC-0013 approved).** The foundation
is built, and the vertical slice runs end to end in a browser and inside
the desktop app: engine → `/api/state` → web Home → an action
(Propose → Approve → Execute → Record → Undo) → live update. **Next:
Muse builds the real Home on it (H-0007); Zac runs the check on his new
computer and phone.** MIA's devices, in order (DEC-0015): the new
computer, the phone, the Meta Display glasses (soon), then Pi devices
(eventually).

## Where things stand

| Area | Status |
|---|---|
| Desktop app (PySide6, 37 apps) | REAL, in daily development |
| Phone web app (Talk, Today, Money) and Android app | REAL |
| Assistant (local model, ~185 tools, voice) | REAL |
| Life events (history), links, Life State v2 (now with assets, kitchen, workout), `/api/state`, schema | REAL / DERIVED, built 2026-10-05 |
| Web front end (`web/`, served at `/web/`; desktop "Home (preview)") | REAL foundation: engine client, tokens, a working Home scaffold. Muse's real Home next |
| Action API (`/api/actions`) and live updates (`/api/live`) | REAL, built 2026-10-05 |
| Muse's desktop design artifact | Design surface, SIMULATED. Superseded by `web/` for real screens |
| Meta Display glasses | PLANNED, priority 3 (DEC-0015), waiting on Q-0003 |
| Raspberry Pi devices | Supported but parked: priority 4 (DEC-0015) |
| MIA's reasoning over Life State ("opportunities") | PLANNED (Phase 2) |
| Collaboration hub (these files) | REAL, started 2026-10-05 (DEC-0010) |

## Who's doing what

- **Zac:** run the check on the new computer (`python -m tools.web_check`,
  steps in `docs/NEXT_SESSION.md`), open the new Home on the phone, answer
  Q-0010 (what the new computer is) and Q-0003 (the glasses, now urgent) and paste the result into the hub. Enter real
  data through MIA. Decide DEC-0014 (Muse's Witness Principle). Open: Q-0001, Q-0002, Q-0003 (Muse listed what the glasses
  answer needs), Q-0005.
- **Muse:** H-0007, the real Home and presence in `web/` (guide:
  `web/README.md`), under DEC-0014.
- **ChatGPT:** review H-0007's milestone against the vision when Muse's
  Home lands; think ahead on Phase 2 reasoning (MIA proposing missions).
- **Claude:** support Muse's Home (any missing Life State fields or
  action kinds, via `QUESTIONS.md`). Next engine work: Talk in the web
  front end (voice and chat endpoints for `web/`), then MIA's own
  proposals (`proposed_by: "mia"`, through the communication gate).

## Blocked

- Broad migration of screens: on the check on the new computer and the
  phone (DEC-0013, DEC-0015).
- The glasses client: on Q-0003 (platform and access).

## Recent changes (newest first)

- 2026-10-05 · claude · Phone sign-in for `web/` (`MIA.signIn()`, the same email and password as the phone app), tested in a phone-sized browser: the same Home works on the phone.
- 2026-10-05 · zac · DEC-0011 done: the repo is public, so ChatGPT can read the hub directly. Q-0005's three small choices (placeholder names in tests, hiding the email, a license) are still open.
- 2026-10-05 · zac · DEC-0015: MIA runs on the new computer first, then the phone, the glasses (soon) and Pi devices (eventually). The Pi is not the main target; the docs are corrected.
- 2026-10-05 · muse · H-0006 review (supports DEC-0012/0013 with conditions), answered Q-0007 and Q-0009, proposed DEC-0014 (the Witness Principle), and the design half of Q-0003 (what the glasses answer must include).
- 2026-10-05 · claude · Phase 2 foundation: the action API, live updates, `web/` with the engine client and a working Home scaffold, desktop "Home (preview)", the Pi check tool. H-0007 to Muse.
- 2026-10-05 · chatgpt (via zac) · Approved DEC-0012/0013 with refinements (Q-0008).
- 2026-10-05 · claude · H-0005: where MIA is and the Phase 2 proposal (DEC-0012, DEC-0013, Q-0007 to Q-0009).
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

- DEC-0014 (PROPOSED by muse): the Witness Principle.
- Q-0010: what the new computer is (OS, hardware).
- Q-0001, Q-0002, Q-0003, Q-0005, Q-0006: see `docs/QUESTIONS.md`.

## Constraints everyone works within

No real personal data in the repo (DEC-0002). Facts in code, the model
only phrases (DEC-0004). Surfaces consume `/api/state` and mark
anything else PLANNED (DEC-0005, DEC-0007). The guardrail before every
proposal (DEC-0008). Read, propose, approve (DEC-0009). Only Zac
approves decisions.
