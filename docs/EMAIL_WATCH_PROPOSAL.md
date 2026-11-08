# MIA watches your email (and later your payments) — DEC-0133, proposed

*claude, 2026-11-08, from Zac: "This kind of information is why I want MIA able to watch my emails and payment info
and stuff to be able to get info like that" (after Muse built the life-data pack by hand from his Gmail). Approved in
principle by Zac, 2026-11-08 ("I approve"); this is the privacy model and scope for him to greenlight before any wiring.*

**One line:** MIA reads the owner's own inbox, pulls out the real-world facts hiding in it — orders, receipts, bills,
warranties, service records, deadlines — and offers each one as a *proposal* the owner approves, so his Garage,
Budget, Real Estate and reminders fill themselves from life as it happens, instead of by hand.

This is the engine behind the life-data pack. Everything Muse found — the Lowe's mower order, the Walmart oil change,
the fridge-warranty expiry, the property-tax deadline — was in Gmail. MIA doing that continuously is the goal.

## What it reuses (not a new system)

| Need | Existing piece |
|---|---|
| Connect a source, import on approval | `core/connectors.py` (file + calendar imports already built), the Connect Apps page |
| Pull details out of a document | `core/inbox_classify.detail_proposals` (already extracts warranty/manual details from filed docs) |
| Propose → approve → execute → record → undo | `core/actions.py` |
| Where facts land | `core/maintenance_manager` (assets/service), finance (bills), real-estate, reminders |
| Keep the token safe | encryption at rest (DEC-0126) — the OAuth token is sealed |
| Keep secrets out of logs | the secrets-in-logs test (docs/SECURITY.md step 6) |

So the new parts are small: a **read-only Gmail connector** and a set of **extractors** that turn specific email
shapes into structured proposals.

## How it works

1. **A read-only Gmail connector** (OAuth, scope `gmail.readonly`). MIA can *read*; she can never send, delete, label
   or change anything. The owner grants it on the Connect Apps page and can revoke it there.
2. **Polling on a schedule** (like the weekly dependency check): new messages since the last run are fetched.
3. **Extractors decide, not the model.** Code-defined matchers recognize a few high-value shapes and emit a typed
   proposal — the model may help parse free text, but the code keeps only what fits the shape and what the message
   actually says (the same "model extracts, code decides" rule as `core/user_sync.py`):
   - **Order confirmation** → an asset + vendor + price + date (e.g. the Lowe's mower).
   - **Service receipt** → a "maintenance done at <date>" event on the matching asset (e.g. the Walmart oil change).
   - **Bill / statement** → a recurring bill record with amount + due date.
   - **Warranty notice** → a warranty-expiry reminder.
   - **Appointment / deadline** → a calendar item.
4. **Every fact is a proposal.** It arrives in the owner's queue — *"I found a John Deere order in your email — add it
   to the Garage?"* — and nothing touches his records until he says yes. Each is logged and undoable.

## The privacy model (the part that has to be right)

This is the owner's most sensitive data, so the rules are strict and built in, not optional:

- **Read-only.** The Gmail scope cannot send, delete or modify. MIA is a reader of his inbox, nothing more.
- **Local-first.** Fetching and extraction run on his PC. Raw email bodies are **not** stored — MIA keeps only the
  extracted facts plus the Gmail message-id they came from (so she can show her work and avoid re-processing). No
  email content is sent to any cloud; the local model does the parsing.
- **The token is sealed at rest** (DEC-0126) and tied to his Windows sign-in.
- **Secrets are never stored or logged** — card numbers, passwords, verification codes and account numbers are
  stripped before anything is kept, enforced by the existing secrets-in-logs test.
- **Opt-in and revocable per source**, with the granted scope shown plainly; revoke on Connect Apps removes the token.
- **Auditable and reversible** — every fact MIA pulls is a proposal in the activity/security log; reject any, undo any.
- **Payments go through Plaid, not email-scraping.** Transactions/balances come from the bank connection already in
  flight (Plaid), which is built for it; email is for orders, receipts, bills and warranties, never for reading card
  or account numbers out of messages.

## Scope for a first build

Gmail read-only + the five extractors above, each emitting proposals through `core/actions.py`. Nothing auto-applied.
A Connect Apps toggle to grant/revoke, and a "what MIA found in your email" review queue (a screen — the design
session's, flagged for them).

## Open questions for Zac

- Exact Gmail scope: `gmail.readonly` (full read) vs `gmail.metadata` (headers only — safer but misses receipt
  bodies). Proposed: `readonly`, with bodies parsed locally and never stored.
- Keep nothing but extracted facts (proposed), or let the owner opt to archive a receipt as a filed document?
- Which extractors first (orders + service receipts are the highest value for the Garage)?
- Polling cadence (daily?).
- Later sources: can extend the same connector pattern to other providers (Outlook) and to statements/receipts the
  owner forwards in.

## Related
DEC-0128 (device fabric — same connector/gate family), DEC-0126 (encryption at rest), DEC-0127 (product/subscription),
`core/connectors.py`, `core/inbox_classify.py`, `core/actions.py`, `core/user_sync.py`.
