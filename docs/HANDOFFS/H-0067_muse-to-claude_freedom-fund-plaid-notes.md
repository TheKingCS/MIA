# H-0067 · muse → claude (cc zac) · 2026-10-21

## Freedom Fund: Plaid verification + experience notes (under DEC-0038)

From: muse · To: claude (cc zac) · Date: 2026-10-21
Subject: Implementation notes on the approved Freedom app (DEC-0038): verify the Plaid path live, plus the display requirements from Zac's 2026-10-21 ask.
Context: DEC-0038 (approved by Zac, his words: "I need my finances monitored and a clear view of my daily/weekly/monthly progress in saving towards getting out of this factory ... a quick viewable display that helps me get through these shitty nights at work and even helps me estimate when I can reasonably work from home selling my homestead goods full time") already covers the Freedom app. The Plaid engine also already exists (`core/plaid_manager.py`, Sept 2026: Hosted Link in the system browser, token polling, encrypted vault for client_id/secret + access tokens, sync → FinancialSnapshot JSON → `finance_manager`, offline last-snapshot discipline; `core/web_money.py` surfaces configured/unlocked + `from_bank` items). Per its header it has never been verified against Plaid's real API — Zac had not yet created his Plaid developer account, and still hasn't as of tonight. (Muse's own Plaid connector, Rocky's side, already feeds Zac's Friday money check-in; MIA's Plaid is separate — her data stays on his devices.)
What's needed: (1) once Zac's credentials exist, verify the Plaid path end-to-end: sandbox first, production when his account allows (free tier; Fidelity holdings may need the Plaid support ticket for Investments access — see plaid_manager's header); credentials and tokens live only in the local vault, never the repo, never a handoff (DEC-0002). (2) The experience notes below for the display.
Constraints: sync stays snapshot-based — the display reads snapshots, never live-fetches. Money stays read-only on the glasses (DEC-0024). Estimates stay honest: ranges with visible inputs, never a promised date (DEC-0038 says every number says where it came from — keep that).
Acceptance criteria: Plaid sync verified against Zac's real accounts; Freedom numbers trace to snapshots; muse does the look pass before this closes.
Related IDs: DEC-0038, DEC-0037, DEC-0024, DEC-0022, DEC-0014, DEC-0002, `core/plaid_manager.py`, `core/finance_manager.py`, `core/web_money.py`.

## The display (phone-first; one card on the glasses)

- **The number:** total saved toward the build-out (accounts Zac designates as the fund — his designation, his data, no account details in code).
- **The pace:** saved today / this week / this month from snapshot deltas; green-week streak. A red week is reported plainly, never punished (DEC-0014). The Friday check-in's green/red number and this screen should agree — same snapshots, two surfaces.
- **The targets:** Greenhouse, Coop, Solar, Root Cellar (DEC-0038's Projects list) — editable, reorderable; amounts are Zac's (he sets them; we may propose estimates for his approval, never silently fill).
- **The estimate:** the range + the inputs (pace, targets total, outflow, homestead profit) as DEC-0038 specifies.
- **Shift readout** per DEC-0038 (what tonight's shift buys); **"remember why"** reasons on the same screen.
- **Glasses card (read-only):** fund total, this week +$X, next target + its bar. That's the work-night glance Zac asked for.

## Zac's step (only he can do this one)

Create the free Plaid developer account (plaid.com) and put the client_id + secret into MIA's vault via the existing setup. Muse will walk him through it at the PC, one step at a time.

## Note for the loop

Muse filed this as the spec for Zac's ask; claude's DEC-0038 already approved the direction. Split: engine + verification are claude's; the display look pass is muse's before close.
