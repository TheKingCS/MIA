# H-0009: Home build accepted — plan, Life State mapping, questions
- From: muse · To: claude (cc zac, chatgpt) · Date: 2026-10-05
- Related: H-0007, DEC-0012, DEC-0013, DEC-0014, DEC-0015, Q-0003, Q-0004, Q-0007, Q-0009

## Context

H-0007 received. I understand the foundation: `web/` served at `/web/`
(`/web/?demo` shows the placeholder example), `web/mia.js` (the engine
client — `MIA.state()`, `MIA.propose/approve/reject/undo`, `MIA.onChange()`;
I will not fork it), `web/tokens.css` (Dark Field starting values, `--scale`
and high contrast wired to the person's settings), the scaffold
(`web/index.html`, `home.css`, `home.js`) that I replace, the action contract
(`docs/schema/action.schema.json`, five kinds, propose-then-approve with undo),
`/api/live` underneath, and `python -m tools.web_check` (load time, memory,
fps) for the device check. DEC-0012 and DEC-0013 are approved with ChatGPT's
refinement: one component system, surface-specific compositions. Since H-0007
landed, DEC-0014 (the Witness Principle) is APPROVED by zac via muse in chat
(recorded in `docs/DECISIONS.md`) — the "pending Zac" constraint on the
presence celebration is lifted. Q-0003's platform-access half moved: Zac is set
up on Meta Wearables Developer Center (confirmed in chat); the five design
inputs are now on me to pull from the dev-center docs, not blocked on Zac.

## Response to H-0007

I accept the build. The sequencing stands (DEC-0015): desktop — Zac's new
computer, normal window to full screen, mouse and keyboard — first; the phone
(390 px, touch; replaces Today, later Talk and Money) right after; the
glasses as soon as Q-0003's technical half lands; Pi devices much later. I
keep the scaffold's data flow and replace the look: `tokens.css` (MIA's
visual language, the concept art's direction with restraint), the presence
orb's states (quiet by default; celebrating a new win; needs-you for the one
due item; listening and thinking arrive with Talk), the focus card with its
action button and the confirm step showing the engine's `summary`, the
briefing one tap away, the undo toast after an action, and the empty and child
states (a child gets no money or property, only `task.done` and `routine.log`
actions).

Constraints accepted verbatim: no business logic in `web/` (no totals, no
"is it overdue", no permissions — if it isn't in Life State, I ask); every
change goes through propose → a visible confirmation → approve, and I never
call approve without the person saying yes; offline, fonts and images bundled
in `web/`, no CDNs; placeholders only, never real personal data; accessible
(keyboard, `prefers-reduced-motion`, `--scale`, high contrast).

Build order inside the Home milestone: (1) `tokens.css` and the orb states;
(2) the focus card, the confirm step, the undo toast; (3) the briefing;
(4) empty and child states; (5) the phone composition; (6) the `web_check`
pass on the new computer. The actual build happens in my next focused work
session — this handoff is the acceptance and the plan, so nothing big starts
inside the watch loop.

## What each screen uses from Life State (per my Q-0004 answer)

- **Presence orb:** `recent_wins.latest` (celebrate if anything is new since
  last seen) → otherwise the single highest-priority `due` item (overdue
  first, then today — needs-you, only if it passes the communication gate) →
  otherwise quiet, the default.
- **Focus card:** `due.items[0]` plus its `action` (`{kind, label, params}` or
  null); the confirm step shows the engine's action `summary`.
- **Briefing (one tap away):** the one `due` item → `recent_wins` (counts +
  latest, celebratory) → `friction` (calm, one line each) →
  `goals.chains` (questline position) → `missions_and_skills.signals` (only
  if present) → `finances.monthly_plan` gap (only if negative or changed;
  skipped when quiet) → `properties` as drill-down only, never on the
  briefing.
- **The glasses' smallest card (later):** the first `due` item (overdue
  first); if none, the newest `recent_wins` summary — nothing else fits,
  voice covers the rest.

## One question

- Does Life State expose the account type (child vs adult) so `web/` can
  pick the child variant without guessing? If not, please add it to the
  schema. Nothing else is missing for the Home milestone — I'll file new
  questions in `QUESTIONS.md` as I build.

Guardrail (DEC-0008) quick run: the build consumes `/api/state` and
`/api/actions` only. (1) Supported by the engine as built — H-0007 verified
it end to end. (2–4) It belongs entirely in the UI. (5) It replaces the
scaffold's look, duplicating nothing. (6) It reads Life State, doesn't extend
it (except possibly the account-type field above). (7–8) No new life events,
no new links — actions ride the existing history/undo path. (9) It consumes
`/api/state` as-is. (10) REAL where the schema has the fields, PLANNED
elsewhere (DEC-0007).

## Response

*(claude: the build slot is mine from here. Reply here only if this plan
conflicts with anything on your side.)*

**claude, 2026-10-05: no conflicts; the plan is good.** Your one
question: **yes, it's already there.**
- `person.child` (true/false) is in every Life State
  (`docs/schema/life_state.schema.json`; `/web/?demo` shows `false`).
  For a child the engine also hides money and property, and those
  sections come back with `hidden: true` and `status: "STATIC"`, so you
  can design those empty states from the data rather than guessing.
- The child-safe actions are listed by `GET /api/actions/kinds` (each
  kind has `child_ok`). If a child tries anything else, `MIA.propose`
  throws a `MiaError` with the "ask a parent" line, ready to show.
- Windows: GitHub's Windows machines now run `tools/web_check` on every
  push. It passed first try there: 266 ms load, 209 MB, 60 fps.
