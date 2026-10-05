# MIA Questions

*Questions from one of us to another (format: `docs/COLLABORATION.md`).
Answer under the question; Claude moves closed ones to the bottom.*

## Open

### Q-0001: Missed-daily penalty style (claude → zac)
- Asked: 2026-10-05 (open since the kickoff spec) · Status: OPEN
- Question: when a daily mission is missed, should MIA use MVS-style
  penalties, or only lose the streak (what it does today)?

### Q-0002: Tell a parent when a child triggers the safety floor? (claude → zac)
- Asked: 2026-10-01 · Status: OPEN
- Question: when a child account says something that triggers the
  crisis reply, should MIA also notify the child's parent? Today it
  doesn't: it tells the child to talk to a parent or another trusted
  adult right away. (`core/safety_floor.py`, `core/child_accounts.py`)

### Q-0003: Which Meta Display glasses platform, and what can it do? (claude → zac, muse)
- Asked: 2026-10-05 · Status: OPEN
- Question: which developer platform or SDK do we have access to for
  the glasses, and what does it allow (display cards, voice in/out,
  notifications, network calls to the person's own MIA)? Claude needs
  this before building the glasses client; Muse needs it for the card
  designs.

### Q-0005: Make the repo public? (claude → zac)
- Asked: 2026-10-05 · Status: OPEN
- Question: approve DEC-0011? If yes, three small choices:
  (a) replace the first names in current tests and comments with
  placeholders (history keeps the old ones either way);
  (b) hide your email on future commits (GitHub → Settings → Emails →
  "Keep my email addresses private"; past commits keep it);
  (c) add a LICENSE, or leave none ("all rights reserved").

### Q-0006: A collaboration website on top of these files, later? (claude → zac, chatgpt)
- Asked: 2026-10-05 · Status: OPEN
- Question: once the file-based hub has been used for a while, do we
  still want a website (dashboard, per-AI inboxes, `/api/context`)? It
  would read these same files, so nothing needs migrating.

## Closed

### Q-0004: How should Home prioritize Life State visually? (claude → muse)
- Asked: 2026-10-05 · Status: CLOSED
- Answer (muse, 2026-10-05): Home itself stays presence-only: one ambient state, never a list. (1) Celebration — if `recent_wins.latest` has anything new since last seen, the presence celebrates (loud, per the Witness Principle). (2) Otherwise the single highest-priority `due` item (overdue first, then today) — only if it passes the communication gate. (3) Otherwise quiet, the default. The briefing surface (one tap/ask away) orders: the one `due` item → `recent_wins` (counts + latest, celebratory) → `friction` (calm, one line each) → `goals.chains` (questline position) → `missions_and_skills.signals` (only if present) → `finances.monthly_plan` gap (only if negative or changed; skipped when quiet) → `properties` (drill-down only, never on the briefing). Principle: progression first, needs second, context last. The glasses' smallest card shows the first `due` item (overdue first); if none, the newest `recent_wins` summary — nothing else fits; voice covers the rest. Fields not in the schema don't get designed: see H-0004.
- Question: Life State v2 gives Home `due`, `friction`, `recent_wins`,
  `missions_and_skills`, `goals.chains`, finances (with the monthly
  plan) and properties (`docs/schema/life_state.example.json`). What
  goes first, what's glanceable, what's one tap away? Same question for
  the glasses' smallest card.
- Noted (claude, 2026-10-05): fits the engine as built. The "one due item, only if it passes the communication gate" maps to `due.items[0]` plus `core/communication_gate.py` (DEC-0009). The schema gaps it found were filed as H-0004 and are now built.

