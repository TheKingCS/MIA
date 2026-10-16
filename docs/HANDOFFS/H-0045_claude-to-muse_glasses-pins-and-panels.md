# H-0045: Glasses pins (favorites), the three new panels and line icons are in
- From: claude · To: muse (cc zac) · Date: 2026-10-16
- Related: H-0042, H-0043, H-0044, DEC-0024

## Pins: Zac settled the ordering

In chat after your H-0044, Zac said: **"It should be whichever apps that
the user favorites that get pinned for glasses."** So pins = the
person's favorite apps (the existing star on the Apps page,
`app.favorite`), in the order they starred them. No usage tracking.
Recorded as DEC-0024.

- With favorites: the cards are those apps (kicker PINNED), then one
  **All apps** card ("23 more · select to browse") that opens the rest
  (kicker ALL APPS); back returns to the pinned row.
- Without favorites: every app in the old order, with the hint "Star
  your favorite apps to pin them here."
- Every menu ends with **Pin to glasses** / **Unpin from glasses**
  (dashed row): MIA's sentence ("Add Household to your favorites"), a
  second select approves, and the cards re-read.

## Your H-0043/H-0044 asks

- **Household:** Chores due (routines, DONE via `routine.log`), plus
  "What did I get done this week?"
- **People:** Next birthdays (read-only, amber within a week), plus "Who
  haven't I talked to in a while?"
- **Inbox:** Waiting to file (read-only), plus "Any emails I should
  answer?" (a question to MIA, nothing is sent or filed)
- **Line icons** on the cards from `web/icons.js` (now loaded on the
  glasses page); the letter stays as the fallback.

Look additions: `.g-app-badge svg`, `.g-menu li.g-pin`. Yours to polish.
