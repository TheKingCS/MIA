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

### Q-0004: How should Home prioritize Life State visually? (claude → muse)
- Asked: 2026-10-05 · Status: OPEN
- Question: Life State v2 gives Home `due`, `friction`, `recent_wins`,
  `missions_and_skills`, `goals.chains`, finances (with the monthly
  plan) and properties (`docs/schema/life_state.example.json`). What
  goes first, what's glanceable, what's one tap away? Same question for
  the glasses' smallest card.

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

*(none yet)*
