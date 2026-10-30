# H-0070 · muse → claude (cc zac) · 2026-10-21

## Freedom screen look pass (reply to H-0068), rest queued

From: muse · To: claude (cc zac) · Date: 2026-10-21
Subject: Look pass on the Freedom screen (`web/freedom.*`, `core/glasses.py` _freedom_glance) against H-0067 and DEC-0038. The rest of H-0068's screens (Presence, the frame, hubs, Compliance, Chickens, Goods/labels) are queued — Presence + frame next, since DEC-0044's navigation reshapes everything.
Context: Reviewed `web/freedom.html`, `web/freedom.js` (195 lines), and `core/glasses.py::_freedom_glance` against H-0067's points and DEC-0038's wording clauses. Placeholder-free review; `?demo` data not inspected.
What's needed: notes 1–2 are wording/color worth applying; 3–6 are suggestions. Muse does the look pass on the remaining screens next.
Constraints: DEC-0038 wording stays exact (range as estimate, every number's source); DEC-0014 (no punishment); DEC-0024 (Money read-only on glasses); DEC-0002.
Acceptance criteria: notes applied or answered; the remaining screens' pass in a follow-up handoff.
Related IDs: H-0068, H-0067, DEC-0038, DEC-0044, DEC-0024, DEC-0014, DEC-0002.

## What's working (no notes)

- The full H-0067 set is present and honest: the range reads "Between … and … at your pace (… a month). An estimate, not a promise." Every breakdown line carries its source (`src.needs`, `src.homestead`, `src.saved`, `src.pace`); unset values say "not set" or "no sales yet" instead of guessing.
- The red-week wording ("Last week went red. It happens; this week is a fresh one.") is DEC-0014-clean; the streak squares are aria-hidden with the text carrying the information.
- The levers ("+X → N days sooner") answer "what moves the day" directly.
- The shift card is the work-night glance Zac asked for: pay → days of living → "% of the fund. Every shift is a step out." Its empty state tells him exactly what to put in.
- Plaid on-ramp when no bank is connected ("the numbers fill in by themselves once it is (Money → Bank). Until then, Your Plan takes your own.").
- Accounts show bank · name ····mask only; the grown-ups gate is on both surfaces.
- The glasses card matches the spec: fund of goal + %, this week + streak, the range ("an estimate at your pace"), "Tonight buys N days". Read-only.
- Title Case on all section headers; "You're there." / "The fund is full. Time to plan the jump." lands.

## Notes

1. **Amber on "Add A Build"** (`buildsSection`): amber is the attention color in the Stark language; adding a build is a constructive action. Suggest the default/cyan treatment or btn-ghost so amber keeps meaning "look here".
2. **"and later" range wording**: "Between October 2028 and later at your pace" (and the glasses card's "Free between 2028-10 and later") reads awkward when there's no latest date. Suggest "October 2028 at your pace — later if the pace slips" on web, "Free from 2028-10 at your pace" on the card.
3. Suggestion: the accounts kind label reads "fund" / "not" — "not in the fund" would read better at a glance.
4. Suggestion: the `whySection` empty-state example is fine as his own words; consider pulling his actual first "why" from the existing Friday check-in notes rather than the placeholder sentence.
5. Suggestion: `periodTiles` marks a negative tile "bad" — check the class reads as plain red, not alarming, next to the streak's gentle red-week line.
6. Suggestion: hero "big" shows "~N days" — the day count is the hero; consider making the month-year range the dim line and keeping the day count, as built. No change needed, just confirming the hierarchy.

## Next

Muse's pass on Presence (`index.html`), the frame (`shell.js`), and the hubs (`path/world/system.html`, `hubs.js`) follows — those carry DEC-0044's new navigation and everything later builds on them. Compliance, Chickens, and Goods/labels after.
