# H-0081: The savings hound — couponing for groceries and household needs
- From: muse · To: claude, chat (cc zac) · Date: 2026-11-06
- Related: DEC-0014, DEC-0038, DEC-0052, DEC-0053, DEC-0054, DEC-0069, H-0080; the weekly Kroger cart build and the Kitchen / Grocery List surfaces. Draft decision text for DEC-0073 is in section 4 (PROPOSED — only Zac approves).

## Context

Zac's direction (2026-11-06, via muse, right after H-0080): "another
one should be couponing and helping me save on household needs and
groceries."

The pattern is already half-approved in pieces. DEC-0052 lets her
surface a cheaper insurance quote near renewal unprompted; DEC-0054
adds a "still using it?" mark on subscriptions. The weekly grocery cart
already catches digital coupons when they happen to match the list —
but nothing hunts them, nothing plans around sale cycles, and household
consumables (cleaning, paper, toiletries, pet) get bought at full price
on the week they run out. Couponing is the weekly-spending version of
the same instinct: she watches prices so the user doesn't have to.

This sits directly under Zac's money direction: stay in the green,
cover the bills on his income, grow the Freedom fund. Savings she finds
are small and weekly — which is exactly the grain his budget runs on.

## What's needed

### 1. The hunt (before each weekly cart, not during)

- Scan available and clipped store digital coupons against the planned
  list and the standing staples; where a couponed option beats the
  usual buy on true unit price, propose the swap in the cart review —
  her suggestion, his call.
- Track a floor price for shelf-stable staples (what "a good price"
  actually is, from cart history). When a staple hits or beats its
  floor, flag a stock-up quantity in that week's cart.
- Mind the stacking order she already lives with: sale price, digital
  coupon, employee discount, store brand vs name brand — compared on
  unit price, never on the size of the "% off" banner.

### 2. Household needs on a cycle, not on emergencies

- A running household-needs list (consumables, not food) kept with the
  grocery data, worked on deal weeks: bought ahead at a good price,
  not at full price the day the bottle runs dry.
- Same review surface as groceries — one glance, approve or strike —
  so household savings ride the rhythm that already exists.

### 3. Wider than one store, carefully

- Sale-cycle awareness for the household's other recurring spends
  stays at the DEC-0052 level: she notices and offers, she does not
  open accounts, enroll in programs, or clip anything in the user's
  name without his approval.
- Coupon and cashback services are proposed one at a time, with what
  they cost in data and attention stated plainly (Chat's gate, below).

### 4. Proof, kept honest (a savings ledger)

- Three numbers, never blended: **offered** (coupons she found),
  **redeemed** (coupons that actually came off at the register), and
  **saved vs normal** (redeemed savings measured against the item's
  usual price, not a fantasy reference price).
- The standing rule, in her voice everywhere this shows: *a coupon for
  something that wasn't needed is not a saving.* Buying more to "save"
  more is a failure mode, named as such.
- The weekly redeemed figure speaks the Freedom language: it is part
  of the green-week story, reported in the same breath, not a separate
  brag feed (less friction, DEC-0014 — she does not punish or nag
  about money either).

### 5. Draft decision for Zac (DEC-0073, PROPOSED)

> MIA hunts savings on groceries and household needs: coupon- and
> sale-aware cart building against recorded floor prices, a household
> consumables cycle, and an honest savings ledger (offered / redeemed /
> saved-vs-normal kept separate). She proposes; the user approves in
> the existing cart review; no accounts or enrollments in his name
> without his say-so, and a coupon for something unneeded never counts
> as a saving.

### 6. What each of us is asked for

- **Claude:** feasibility pass — where coupon and sale data can
  actually come from (store site session, public pages, receipt
  history), the floor-price record in the cart data model, where the
  household-needs list lives, and a first task breakdown.
- **Chat:** the vision check — a savings hound under the
  less-friction principle: hunting silently is MIA; surfacing every
  deal is noise. Where is the line, and which findings earn an
  unprompted word under the DEC-0052 gate?
- **Zac:** three decisions — (a) approve, amend or reject DEC-0073;
  (b) scope: groceries + household only, or wider recurring spends in
  from the start; (c) whether the household-needs list stands alone
  or rides inside the grocery list.

## Constraints

- Purchases are untouched by this proposal: she builds and proposes
  carts exactly as today; the user reviews, checks out and pays. No
  coupon flow may ever complete a purchase on its own.
- DEC-0002: no real personal data in the repo — store names and
  mechanics are fine; his actual lists, prices paid and cart history
  stay in his private files, placeholders here.
- His time is the scarcest currency (night shift): the hunt is
  automated or it does not happen. If a saving costs him ten minutes
  of clipping for forty cents, the honest answer is to skip it, and
  the ledger should be able to say she skipped it on purpose.
- Guardrail check (DEC-0008), briefly: partly supported today (Q1/Q2 —
  cart building, DEC-0052 findings, "still using it?"); genuinely
  missing are the coupon-first build order, floor prices, the
  household cycle and the savings ledger (Q3). Engine first (Q4):
  floor prices and the ledger live with the cart data; the interface
  is the cart review that already exists, plus one savings line where
  Freedom speaks. No duplication (Q5): extends the cart and the
  DEC-0052 findings pattern. Grocery and household lists already live
  in her data (Q6); a purchase remains whatever event it already is —
  this proposal adds no new life-event kinds (Q7). Links (Q8): a
  redeemed saving links to the cart and week it belonged to, nothing
  more exotic. `/api/state` (Q9): the savings summary can ride the
  surfaces that already show the cart and Freedom; Claude's call.
  Floors and ledgers are DERIVED from cart history; a saving is
  PLANNED until it is redeemed, then REAL (Q10).

## Acceptance criteria

- Claude replies with the feasibility pass and a task breakdown, or
  objections recorded in this thread.
- Chat's vision verdict reaches the repo (via Zac), including the
  noise line for deal findings.
- Zac approves, amends or rejects DEC-0073; on approval it is filed in
  `docs/DECISIONS.md` and the first slice (coupon-aware cart pass)
  becomes scheduled work.
