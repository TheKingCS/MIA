# H-0068: H-0067 applied; today's new screens, ready for a look

- From: claude · To: muse (cc zac) · Date: 2026-10-21
- Related: H-0067, DEC-0036, DEC-0037, DEC-0038, DEC-0040, DEC-0044, `docs/UX_SYSTEM_AUDIT.md`

## Context

H-0067's display notes for Freedom are built. Today also brought several
new screens and a new navigation (DEC-0044, Chat's "one system, not a
collection of apps"): all function-first on the shared frame and tokens,
waiting for your look pass. Placeholder data for each is in
`docs/schema/*.example.json` (open any page with `?demo`).

## H-0067, point by point

- **The number**: saved = the accounts Zac picks as the fund (Freedom →
  "Which Accounts Are The Fund", `freedom.fund_account`); until he picks,
  all checking and savings. Account ids live in his settings, never code.
- **The pace**: today / this week / this month from the fund's own balance
  changes, logged once a day (`FreedomLog`, his own `freedom_log.json`);
  until the log has history, income minus spending, and each period says
  which (`periods[].source`). **Green-week streak** under the tiles (eight
  squares, the run in words); a red week reads "It happens; this week is a
  fresh one." The Friday check-in and this screen read the same snapshots.
- **The targets**: builds in Zac's order (↑ ↓, `freedom.build_move`), the
  first unfinished one marked **Next**; amounts are his.
- **The estimate**: a **range** ("Between October 2028 and January 2029 at
  your pace … An estimate, not a promise"), from the best and the slowest of
  the last three months; no latest day when a month saved nothing.
- **Shift readout** and **Remember why**: unchanged, on the same screen.
- **Glasses (read-only)**: a Freedom card with **Tonight** (fund of goal,
  this week and the streak, the range, what tonight buys) and **Next
  Build** (its bar as a percent). Zac pins it to put it first.
- **Plaid verification**: waits on Zac at the PC; it's the top of
  `docs/NEXT_SESSION.md`.

## Screens built today, for your look pass

| Screen | What it is | Decision |
|---|---|---|
| Presence (`index.html`) | Home leads with **Now**: what matters across every app, each with why and its kind (deadline, fact, suggestion, progress), the next one marked; then **On Your Path** | DEC-0044 |
| The frame (`shell.js`) | Sidebar and phone bar: Presence · Conversation · My Hero's Path · World · System, then pinned apps | DEC-0044 |
| My Hero's Path, World, System (`path.html`, `world.html`, `system.html`, `hubs.js`) | The hubs: World shows every app with its live status and a ★ to pin | DEC-0044 |
| Freedom (`freedom.html`) | The ring, the range, the tiles, the streak, the breakdown, builds, accounts, history, why | DEC-0038, H-0067 |
| Compliance (`compliance.html`) | Deadlines by urgency; unverified always marked | DEC-0040 |
| Chickens (`flock.html`) | One-tap egg counts, two weeks of bars, cartons | DEC-0037 |
| Workshop → Goods, labels (`workshop.html#goods`, `label.html`) | Goods on hand by batch, market day taps, printable labels (ink on paper tokens: `--label-paper`, `--label-ink`) | DEC-0036 |

New classes are in `concept.css` under their decision's comment
(`pres-*`, `hub-*`, `free-*`, `ob-*`, `goods-*`, `market-*`, `egg-*`).

## Still open on my side

H-0066 (your Insurance look pass) isn't applied yet; it's next after this.

## Acceptance

Your look notes on the screens above, in a reply handoff; I apply them.
