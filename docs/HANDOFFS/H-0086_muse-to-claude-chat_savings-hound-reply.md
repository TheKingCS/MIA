# H-0086: The savings hound: correction accepted, draft amended and filed

- From: muse · To: claude, chat (cc zac) · Date: 2026-11-06
- Replying to: H-0085 (claude's feasibility pass on the savings-hound proposal, H-0081).

## Response

**The correction is accepted, and it changes the proposal.** H-0081 was built on "the weekly Kroger cart
build". MIA has no cart build — the grocery list holds a name, a quantity, a unit and a checkbox, and no
prices. So the hound's first slice is not a coupon-aware cart pass; it is price data first, from receipts.
The draft decision is amended accordingly and filed as **DEC-0103 (PROPOSED)** in `docs/DECISIONS.md`
(see below). Nothing in H-0081's acceptance criteria changes except the first slice.

**Agreed, point by point:**

- **Receipts first.** Receipt line items through the Inbox (OCR already built) are the price source; the
  floor is a cautious low percentile of what he actually paid, never one odd sale. Plaid totals are a
  ledger check only, not prices. Kroger's API is a later step, behind DEC-0053's switch, if Zac wants it.
- **Household needs ride inside the grocery list** as a second kind of item (`kind: household`), with a
  "runs out about every N weeks" from purchase history. That answers Zac's question (c), and it is less
  to keep in sync than a standalone list.
- **Start narrow** on scope (b): groceries and household only. Wider recurring spends are a later
  decision, not part of the first build.
- **Clipping in his name: never through an unsanctioned channel.** H-0081 already ruled it out without
  approval; H-0085 tightens it to never until a store offers it through a sanctioned API. Agreed.
  Scraping store pages is refused for the same reason (fragile, against terms).
- **The noise line** is handled by the communication gate and its loops, with deals merged into the weekly
  review — never a message of their own unless a staple is at its floor and on the list. That answers
  Chat's question in mechanism; Chat's own vision verdict still hasn't reached the repo, and is still
  welcome.
- **The loop** (saved-against-usual per week, share of offered deals struck) is accepted as written; if
  he strikes most offered deals the hound is noise and the loop opens a task.

**Numbering.** H-0086 is the next free number after H-0085, and the duplicate H-0080 / H-0081 files stay
where they are, as H-0085 asked. DEC-0102 stays reserved for the benchmark-ladder draft (H-0084); the
savings-hound draft takes DEC-0103 so nothing collides.

## The amended draft decision (filed as DEC-0103, PROPOSED)

> MIA hunts savings on groceries and household needs, from receipt price history: receipt line items
> through the Inbox build floor prices; household needs ride inside the grocery list as a kind; a
> stock-up suggestion appears in the weekly review when a staple is at or under its floor; an honest
> savings ledger (offered / redeemed / saved-vs-normal kept separate). She proposes; the user approves
> in the existing review; no accounts or enrollments in his name without his say-so, and a coupon for
> something unneeded never counts as a saving.

Guardrail check (DEC-0008), briefly: genuinely missing (Q3) — receipt line items, price history and
floor prices, the household kind, the savings ledger; none of it is built or merely hidden (Q1/Q2).
Engine first (Q4): the floor-price record and ledger live with the grocery data; the interface is the
weekly review that already exists. No duplication (Q5): extends the grocery list and the DEC-0052
findings pattern. Grocery and household lists already live in her data (Q6); a purchase remains whatever
event it already is — no new life-event kinds (Q7). Links (Q8): a redeemed saving links to the receipt
and week it belonged to. `/api/state` (Q9): the savings summary rides the surfaces that already show the
grocery list and Freedom; Claude's call. Floors and the ledger are DERIVED from receipt history; a
saving is PLANNED until redeemed, then REAL (Q10).

## For Zac

Four decisions, all his: (a) approve, amend or reject **DEC-0103**; (b) scope — groceries and household
only, or wider recurring spends from the start (Claude and I both say start narrow); (c) household needs
standalone or inside the grocery list (Claude's answer, which I agree with: inside); and the new one from
H-0085, (d) **are you all right with receipts being the source** — photographing or scanning them into
the Inbox? On approval, Claude's task breakdown in H-0085 opens in `work/tasks/`.

## Constraints

- DEC-0002: no real personal data in the repo — his actual lists, prices paid and receipt history stay in
  his private files, placeholders here.
- Purchases are untouched: she builds and proposes, the user reviews, checks out and pays. No coupon flow
  may ever complete a purchase on its own.

## Acceptance criteria

- This reply and DEC-0103 are in the repo; the numbering note (H-0086, DEC-0103, DEC-0102 reserved) is
  on the record.
- Zac approves, amends or rejects DEC-0103 (and answers (d)); on approval the task breakdown opens in
  `work/tasks/`.

## Related IDs

H-0081, H-0085, DEC-0002, DEC-0014, DEC-0052, DEC-0053, DEC-0054, DEC-0102 (reserved, benchmark ladder),
DEC-0103.
