# MIA Business OS: audit and plan

*Claude, 2026-10-21, on Zac's PC. The spec is `docs/specs/BUSINESS_OS.md`
(Zac's handoff, "MIA Business OS — Finance, Tax, Compliance & Operations").
It asks for this audit first, then the first approved increment.
Nothing below is built yet except where it says **exists**.*

**Status words:** ✅ exists and works · 🟡 partly there · ❌ missing ·
⚠ unsafe or wrong as it stands.

## 1. What already exists, and where

| Area | Status | What's there |
|---|---|---|
| Entities (LLCs, sole props) | 🟡 | `core/budget_manager.py` `BusinessEntity` (name, type, notes); income, expenses, bills, debts and properties carry `entity_id`. Business Report per entity and consolidated (`core/business_report.py`). Missing: EIN reference, tax classification, accounting method, tax year, registrations, contacts, accounts/cards per entity |
| Activities / cost centres | 🟡 | Builds are Projects with budgets (`core/homestead_costs.py`); expenses tag `project_id` and `asset_id`; workshop jobs; Grow Lab batches; the flock. No single "activity" registry separate from legal entities (the spec's key distinction) |
| Ledger | 🟡 ⚠ | **Two ledgers**: the Budget (household + entity tags; Plaid import with `plaid_transaction_id` de-duplication; CSV import `core/imports.py`) and the workshop ledger (`core/ledger_manager.py`, sales and costs of things made). They don't reconcile with each other: a market day's cash, deposited, would show as Budget income *and* ledger revenue. Missing: transaction type (transfer / loan payment / owner contribution / reimbursement), posting date, reconciliation status, adjustment history (edits overwrite; the undo log keeps a copy but not an audit trail) |
| Transfers between own accounts | ⚠ | Plaid categories are mapped (`map_plaid_category`), but nothing guarantees a transfer is never counted as income. Must be fixed before tax figures are trusted |
| Mortgage principal vs. interest | ✅ | `core/real_estate_manager.py` `amortization_schedule()` (rate, term, start); Schedule E interest line in the Business Report |
| Rental depreciation | ✅ 🟡 | `annual_depreciation()` / `accumulated_depreciation()` (27.5-year residential, land excluded, placed-in-service date). Missing: improvements as their own depreciable assets, adjusted basis, sale reporting |
| Fixed-asset register | 🟡 | Maintenance assets with purchase price (`core/homestead_costs.py` tool cost of ownership, cost per hour, business-use share `core/business_use.py`). Missing: placed-in-service date, class/useful life, depreciation per asset, Section 179 / bonus flags for review |
| Receipts and documents | ✅ 🟡 | The Inbox (`core/inbox_manager.py`): files, photos (OCR), receipt line items (`inbox_classify.receipt_items`), receipt ↔ recipe matching (`core/receipt_match.py`), email intake over IMAP with an app password, encrypted (`core/inbox_mail.py`). Missing: receipt ↔ bank transaction matching, duplicate-receipt detection, the evidence link kept on the deduction |
| Deduction review | 🟡 | `tax_relevant` flag on income/expenses; auto-tagging charges to a business with a review queue (`core/business_tagging.py`); 1099 payee threshold report. Missing: the deduction candidate record (amount, business-use %, evidence, tax year, rule reference, confidence, open questions, review state) |
| Mileage / business use | ✅ | `core/business_use.py`: equipment hours and vehicle miles, standard mileage worksheet with PDF |
| Farm, greenhouse, aquaponics | ✅ 🟡 | Grow Lab batches, harvests, losses, readings and ranges, experiments; harvest into stock with its cost; the flock (eggs, feed cost per dozen); homestead goods with cost per piece, market days (DEC-0036/0037). Missing: fish batches, utilities allocated to production, sales channel fees |
| Compliance (permits, licences, registrations) | ❌ | Nothing. The closest: insurance renewals with a 45-day heads-up (`core/insurance.py`) and MIA's own notes on Kentucky rules (`docs/HOMESTEAD_GOODS.md`) |
| Tax calendar and estimates | ❌ | Nothing: no obligations, no quarterly estimates, no withholding, no reserve |
| Email monitoring | 🟡 | IMAP intake of one dedicated mailbox, files every message into the Inbox (`core/inbox_mail.py`). Missing: OAuth (Gmail API, read-only), classification of tax/permit/bill notices, phishing checks, sync-health status, backfill |
| Reminders and automation | ✅ | Daily checks in `core/application.py`; every unprompted message through the communication gate (`core/communication_gate.py`: merges, rate-limits, logs why); notifications; the calendar (`core/calendar_manager.py`, upkeep and bills by day) |
| Approval and audit | ✅ | The action contract (`core/actions.py`: propose → approve → execute → record → undo); life events as history (`core/life_events.py`); "why did you tell me that?" (`core/message_reasons.py`). Emails can't trigger anything: MIA only drafts, a person presses Send |
| Security | ✅ 🟡 | Encrypted vaults (`core/secrets_manager.py`: Plaid, inbox mail; the password vault DEC-0035); per-person data; child accounts never see money. Missing: an EIN/SSN field kept encrypted (no tax IDs are stored today, which is right until the vault holds them) |
| Reports and exports | ✅ 🟡 | Business Report (HTML/PDF; Schedule E lines; 1099 payees; net worth), `python -m tools.export_state`, account data export. Missing: accountant CSV exports, fixed-asset schedule, tax-prep packet, open-questions list |
| Backups | ✅ | `core/backup_manager.py`; undo log; atomic writes |

## 2. What's missing, incomplete or unsafe (the gaps that matter)

1. ⚠ **Transfers and two ledgers.** Until own-account transfers are
   recognised and the workshop ledger reconciles with the bank, no tax or
   profit figure is trustworthy. This comes first.
2. ❌ **Compliance and tax obligations** don't exist at all: the
   spec's two "required" features.
3. 🟡 **Entities vs. activities**: MIA has legal entities and cost
   centres, but not the line between them the spec asks for.
4. 🟡 **Deduction candidates with evidence and review states.**
5. 🟡 **Email**: IMAP with an app password works today; the spec asks
   for OAuth, read-only, with health and backfill.
6. ❌ **Regulatory sources**: no catalogue, no verification dates, no
   change detection.

## 3. What gets reused (never rebuilt)

The action contract for every change; the communication gate for every
reminder; the calendar for deadlines; the Inbox and OCR for evidence;
Plaid for transactions; life events for the audit trail; the undo log;
the vaults for anything secret; `core/region.py` money formatting;
Projects as builds; maintenance assets as the fixed-asset base; the
Business Report as the report frame.

## 4. Data changes (backward compatible, every store already loads unknown-field-tolerant)

- `BusinessEntity`: + `tax_classification`, `accounting_method`,
  `tax_year_end`, `ein_ref` (a reference to the vault, never the number in
  plain JSON), `registrations` (ids), `contacts`.
- New **activity** records: name, entity (legal owner), type (rental,
  farm, workshop, household, project), properties and assets.
- Budget entries: + `kind` (income / expense / transfer / loan payment /
  owner contribution / reimbursement), `activity_id`, `evidence_ids`,
  `reconciled`, `source` (plaid / csv / receipt / manual), `history`
  (original value kept on every edit).
- New stores: **obligations** (tax and compliance, one shape), **rules**
  (a requirement or a deadline rule: jurisdiction, authority, official
  URL, verified date, version, status, confidence), **deduction
  candidates**, **fixed assets** (on maintenance assets).
- Migration: none destructive; old entries read as `kind` "income" or
  "expense", `source` from `plaid_transaction_id`.

## 5. Integrations that need your permission

- **Plaid** (have it; linking at the PC is the next session's job).
- **Gmail, read-only, by OAuth**: a Google Cloud project with the Gmail
  API and a consent screen in your name (testing mode is fine for one
  user). Or keep the current IMAP mailbox: works today, no Google setup.
- **Official sources** (IRS, Kentucky Department of Revenue, Secretary of
  State, your county and city): read-only web checks on a schedule, when
  online. Nothing is ever filed or paid by MIA.

## 6. Security and privacy

Tax IDs only ever in the encrypted vault; email bodies stay on the PC,
classified by MIA's local model, never sent out; emails are untrusted
input (they create a proposed task at most; nothing in an email can
change settings, approve, pay or file); every classification keeps why
and from what; consequential actions (pay, file, sign, send) stay
impossible for MIA by design, as email sending already is.

## 7. Plan, in increments (each its own approval)

**P0-1 (proposed first): the obligations calendar.** One store for tax
and compliance obligations (authority, what, entity/activity, period,
due date, the rule it came from and its source URL with a verified date,
status from projected to paid or overdue, proof of filing/payment, next
action). Reminders at 90 / 60 / 30 / 14 / 7 days, on the day, then
overdue, through the communication gate and on the Calendar, with
per-obligation lead times. A "Compliance" screen: upcoming, overdue,
**unverified**, fees, documents needed, the official link. Starts empty:
you and MIA add obligations; a starter list of *candidates to verify*
(federal estimated tax quarters, Kentucky income tax, sales and use tax,
the local occupational licence, the home-based processor registration,
egg rules) is offered as **unverified** tasks, each with its official
source to check, never as confirmed law.
*Tests:* deadline math (weekends, holidays by year, extensions to file
vs. to pay), reminder schedule, no duplicate reminders, status changes,
unverified never shown as confirmed.

**P0-2: transfers, kinds and the ledger bridge.** Transaction kinds;
own-account transfers detected (Plaid's transfer categories plus
matching amounts between your own accounts) and never income; workshop
sales matched to their deposit so they count once; edit history kept.
*Tests:* transfers never income, a deposited market day counts once,
originals kept on edit.

**P0-3: entities vs. activities.** The registry the spec describes,
seeded from what exists (entities, properties, the homestead, the
workshop), with your confirmation.

**P1:** deduction candidates with evidence and review states; receipt ↔
transaction matching; email classification of notices (on the existing
intake first, OAuth Gmail if you want it); accountant CSV exports.

**P2:** fixed-asset register with depreciation per asset and Section 179
/ bonus flags *for review*; tax projection and quarterly estimates
(planning estimates, labelled); per-property NOI and cash-on-cash;
production cost accounting per crop/batch; regulatory source change
checks.

**P3:** scenarios, cash allocation, predictive inventory.

## 8. What I need from you

1. Approve **P0-1 (the obligations calendar)** as the first increment,
   or pick another.
2. The real addresses: where the homestead and each rental are (the
   county and city decide local licences and taxes). They go into MIA's
   data on the PC, never into the repo.
3. How each activity is owned today (in your name, your wife's, joint,
   an LLC?) and whether you file jointly. That decides which federal and
   Kentucky obligations apply at all.
4. Email: keep the IMAP mailbox, or set up read-only Gmail OAuth?
