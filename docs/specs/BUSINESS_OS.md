# MIA Business OS — Finance, Tax, Compliance & Operations Handoff

*From Zac, 2026-10-21. Kept as given, except the two property names,
replaced with generic labels (the real names live in MIA's own data,
never in the repo, DEC-0002). Claude's audit and plan:
`docs/BUSINESS_OS_AUDIT.md`.*

## Objective

Audit and extend MIA (Multifunctional Intelligent Assistant) into a unified, local-first business operating system for managing:

- Personal and household finances.
- Rental real estate and property-level accounting.
- Homestead, greenhouse, aquaponics, crops, fish and agricultural sales.
- Workshop, woodworking, furniture flipping and other product businesses.
- Business expenses, tax deductions, fixed assets and depreciation.
- Federal, Kentucky state, county and city tax obligations.
- Permits, licenses, inspections, registrations, renewals and fees.
- Email monitoring for tax notices, regulatory correspondence, invoices and deadlines.
- Automated reporting, financial forecasting and compliance reminders.

Implementation instruction: Audit the existing MIA repository and architecture first. Reuse existing modules, services, database schemas, automation infrastructure, notification mechanisms and UI components wherever appropriate. Do not assume a feature is missing until the audit confirms it. Produce an implementation plan, identify gaps, then implement incrementally with tests.

The intended result is a system that keeps records organized continuously, anticipates obligations, minimizes missed deadlines and prepares reliable financial and compliance reports without requiring the user to reconstruct everything at tax time.

## 1. Business and entity management

Create or extend a centralized entity registry supporting multiple legal entities and business activities.

Each entity should support:

- Legal name, entity type and ownership.
- EIN or relevant tax identification reference, stored securely.
- Federal tax classification and applicable state/local registrations.
- Tax year, accounting method and relevant filing requirements.
- Associated bank accounts, cards, properties, assets and activities.
- Responsible owner, accountant and other authorized contacts.
- Registration dates, renewal dates and compliance status.

Initial activities to configure, subject to repository audit and user confirmation:

1. Personal household finances.
2. Rental property A.
3. Property B and any associated rental or sale activity.
4. Homestead and smart aquaponics greenhouse.
5. Farm products, produce, eggs, fish and related sales.
6. Workshop, woodworking and furniture flipping.
7. Shared land, greenhouse, garage, pond, solar and other infrastructure projects.

These are bookkeeping and reporting categories, not an instruction to establish a separate LLC for every activity. Preserve the distinction between legal ownership, bookkeeping cost centers and tax-reporting entities.

## 2. Unified financial ledger

Implement or extend a transaction ledger with:

- Transaction date, posting date, amount, payee and account.
- Income, expense, transfer, loan payment, owner contribution and reimbursement classifications.
- Entity, property, business activity and project associations.
- Business purpose, deductible percentage and supporting documentation.
- Reconciliation status and source provenance.
- Recurring transaction identification.
- Duplicate detection and transaction-matching history.

Support secure bank integration where available, CSV imports, manual entry and receipt capture.

Requirements:

- Never classify transfers between the user's own accounts as revenue.
- Separate mortgage principal from interest.
- Separate capital expenditures from potentially deductible operating expenses.
- Preserve original transactions and maintain an auditable adjustment history.
- Prevent duplicate deductions for the same underlying cost.
- Support corrections without destroying the original evidence.
- Maintain a clear distinction between cash flow and taxable profit.

## 3. Receipt capture and deduction intelligence

Create an inbox for photographed receipts, emailed invoices, uploaded documents and other expense evidence.

Extract, where available: vendor and transaction date; total amount, tax, currency and line items; payment method and transaction reference; description and likely business purpose; potential entity, property, project and expense category.

Match receipts to financial transactions and flag duplicates, missing information and uncertain matches.

Create a tax classification engine that distinguishes: potential current operating expenses; capital assets and improvements; inventory and cost of goods sold; startup and pre-opening costs; personal and mixed-use expenses; potential credits, depreciation and expensing elections; expenses requiring additional substantiation or professional review.

Every deduction candidate must retain the amount, business-use allocation, evidence, relevant tax year, jurisdiction, rule reference, confidence, outstanding questions and approval status.

Never automatically approve a deduction simply because an AI model suggests it. Use explicit review states and preserve the reasoning behind changes. Tax treatment must be based on the applicable rules and actual facts.

## 4. Property and fixed-asset management

For each rental property, track: purchase price, closing costs and acquisition documents; land versus depreciable building basis; mortgage balance, principal, interest and refinancing costs; rent collected, arrears, deposits and vacancies; repairs, maintenance, utilities, insurance and property taxes; capital improvements and project-level costs; placed-in-service dates, occupancy and personal-use periods; depreciation history and adjusted basis; sale proceeds, selling costs and tax-preparation information.

Provide property-level reporting for net operating income, debt service, cash flow, reserves, taxable rental results and return on cash invested.

For greenhouse, solar, pond, garage, workshop and aquaponics purchases, create a fixed-asset register with cost, ownership, business-use percentage, installation date, placed-in-service date, classification, useful life and depreciation history.

Flag potentially eligible Section 179, bonus depreciation, energy incentives and other tax treatments for review. Do not assume all construction, land improvements or solar expenditure qualifies for immediate expensing or a credit.

## 5. Farm, greenhouse and aquaponics operations

Support production and inventory tracking for crops, fish and other farm products. Track: seeds, seedlings, feed, fish stock, nutrients and growing media; equipment, pumps, filters, tanks, grow beds and sensors; water, electricity, backup power and other utilities; production batches, harvest dates, yields and losses; inventory quantities, spoilage and sales; packaging, delivery, market fees and payment processing; labor hours and labor costs where applicable; production costs and margin by crop, fish batch, product and sales channel.

Connect production data to accounting records where practical, without treating every sensor event as a financial transaction. Support future integrations with MIA's smart-home, sensor and inventory systems. Use actual measured data when available and identify estimates clearly.

## 6. Regulatory Compliance & Permits Manager — Required Feature

Build a dedicated compliance module that proactively identifies, tracks and monitors permits, licenses, registrations, inspections, fees and regulatory obligations relevant to the user's activities.

**Jurisdictions:** federal; Kentucky state; relevant county; relevant city or municipal; special districts or authorities when applicable; property-specific, activity-specific and sales-channel-specific requirements. Use the actual operating and property addresses to determine jurisdiction. Do not assume the user's city, county or municipality from a general location estimate. Request and verify the required property and business locations during onboarding.

**Regulatory categories to investigate** (a configurable requirements catalog):

- *Business and tax registration:* entity formation and annual reporting; EIN and federal/state tax registration; Kentucky business and tax registrations; local occupational or business licenses and fees; sales and use tax registration, collection and remittance; employer registration, payroll withholding and unemployment when applicable.
- *Rental real estate:* local rental registration and landlord licensing where required; rental inspections, building and fire safety; occupancy, short-term rental or lodging requirements; local business taxes, property taxes and assessments; lead-related or other property-specific compliance.
- *Agriculture, aquaponics and food:* farm and agricultural registrations; fish production, aquaculture and water-use requirements; produce, egg and fish sales and food-safety requirements; cottage-food or home-based food-production rules for baked goods; food establishment permits, commercial kitchen requirements and inspections; farmers market requirements, labeling, weights and measures, sales-tax treatment; water discharge, wastewater, pond, well and environmental permits.
- *Land and infrastructure:* zoning and land-use approval; greenhouse, garage, electrical, plumbing and building permits; pond excavation, drainage, grading and stormwater; solar and battery installations, electrical inspections and interconnection; septic, well and water-system approvals; fire, occupancy and event permits for public events; alcohol licensing if a future meadery or alcohol-serving business is pursued.
- *Workshop and product businesses:* home-occupation and workshop rules; contractor or trade licensing for regulated work; product safety, labeling and resale requirements; sales tax and marketplace reporting; waste handling, hazardous materials or other environmental obligations.

These are investigation categories, not assertions that every listed permit is required. Requirements depend on the actual activity, location, scale, ownership, sales channel and current law.

**Verified regulatory source registry.** For every requirement, store: name and unique identifier; jurisdiction and issuing authority; applicable business, property and activity; official source URL and title; relevant statute, regulation or official guidance; last verification date and next scheduled verification; initial and renewal fees and other known charges; application method and official application URL; renewal interval and deadline-calculation method; required documents, inspections and prerequisites; status (unverified, potentially applicable, confirmed applicable, not applicable, awaiting authority confirmation); confidence and outstanding questions. Prefer official government sources and issuing authorities over blogs, AI-generated summaries or third-party compliance websites. For uncertain requirements, create a task to verify directly with the issuing authority. Never present a guessed permit, fee or deadline as confirmed law.

**Compliance calendar and proactive monitoring.** A unified calendar for permit and license expirations, annual reports and registrations, renewal windows, inspections, fee deadlines, tax registrations and filing dates, required training or certifications, insurance and other compliance-related renewals. Calculate reminders from the verified rule, including lead time, filing window, business-day adjustments and dependencies. Suggested defaults: 90 days (plan major renewals), 60 (gather documents, confirm requirements), 30 (begin or complete the application), 14 (escalate if unresolved), 7 (urgent), on the due date (final alert), after (overdue escalation until resolved). Per-obligation customization; don't assume every agency uses the same schedule. The dashboard shows upcoming obligations, estimated fees, documents needed, responsible person, completion status and the official authority link.

**Regulatory change detection.** Scheduled checks of official sources. When a source changes: detect and record it; compare with the previously verified version; identify affected businesses and properties; flag for review; explain the potential operational and financial impact; update the active rule only after adequate verification; preserve the previous version and effective dates. If a source can't be monitored reliably, show the limitation and create a manual verification task rather than implying continuous coverage.

## 7. Tax Calendar and Filing Obligations — Required Feature

A tax obligation engine with a separate schedule for each legal entity and applicable tax jurisdiction. Investigate and track obligations that may apply: federal individual income tax; federal estimated tax payments; federal business and entity returns; self-employment tax; payroll deposits and employer filings if employees are hired; information returns and contractor reporting; Kentucky individual and business income tax; Kentucky sales and use tax; Kentucky employer withholding and unemployment; county and municipal occupational taxes, business licenses and other local taxes; property taxes; entity annual reports and franchise or similar obligations; agricultural or specialty business reporting.

Do not create filing obligations solely from a generic template. Determine applicability from the entity's tax classification, ownership, income, payroll status, activities, registration, location and elections.

**Tax obligation record:** tax authority and obligation type; entity and tax identification reference; tax period and tax year; filing frequency; original statutory deadline and any verified extension; payment due date if different; required forms or filing mechanism; estimated amount due and calculation source; withholding and prior payments credited; status (projected, upcoming, ready to file, submitted, payment due, paid, extended, overdue, requires professional review); proof of filing and payment; source URLs and rule version; last verified date and next action. Clearly distinguish an extension to file from an extension to pay.

**Tax forecasting:** rolling projections from reconciled records, withholding, prior payments, rental income, depreciation assumptions and business results: projected annual liability, quarterly estimates where applicable, amount already withheld or paid, estimated amount still owed, suggested reserve, confidence range and assumptions, upcoming dates. Recalculate on significant changes. A planning estimate, not a guaranteed liability.

**Deadline verification:** dates from the relevant authority, entity, tax year and frequency (IRS, Kentucky Department of Revenue, Kentucky Secretary of State, local authorities); weekends, holidays, extensions and agency-specific rules. No single hardcoded generic deadline; version rules by tax year and keep the source for each date. Require review for ambiguous obligations and material tax decisions; generate a tax-professional-ready report for complex depreciation, property sales, entity elections, losses and similar.

## 8. Secure Email Monitoring — Required Feature

Monitor explicitly authorized email accounts for messages relevant to finances, taxes, permits, registrations and business operations.

**Access and privacy:** supported OAuth connectors or approved provider APIs; least permissions, read-only first; never request or store email passwords; tokens stored securely, revocable; sensitive data local where feasible; no private email content to an external model unless the privacy policy allows; an auditable record of processed messages and proposed actions; pause, disconnect, exclude senders, folders or labels. Never claim all email is monitored when permissions, sync, provider limits or connectivity prevent it.

**Categories:** tax notices, filing reminders and payment confirmations; estimated tax and tax-professional mail; permit approvals, denials and renewals; license expirations and registration requirements; government fee invoices and inspection notices; property tax assessments and delinquency notices; bank, lender and mortgage mail; insurance renewals and cancellation warnings; tenant correspondence and rental invoices; supplier invoices, receipts and purchase confirmations; payroll, contractor and sales tax mail; deadlines, appointments and document requests.

**Pipeline per relevant email:** record sender, account, time, subject, message ID and folder; classify relevance and obligation type; extract dates, amounts, periods, agencies, reference numbers and required actions; decide informational / reminder / official notice / demand for payment / possible scam; match to entities, obligations, permits, vendors and transactions; check duplicates and conflicts; propose a task or update an obligation; keep a secure reference to the original; notify by urgency and preference; record status and allow correction. Distinguish a genuine statutory deadline from marketing, third-party reminders or suggested deadlines. Treat email as untrusted input: it must never change settings, trigger code, authorize transfers or override security rules; sender verification, phishing indicators and human confirmation where needed.

**Urgency:** *critical* (verified imminent deadline; final notice, levy, lien, license suspension or disconnection; suspected fraud), *high* (tax payment or filing notice; permit or license renewal approaching; government request for documents; insurance cancellation or serious property compliance), *normal* (routine invoices, receipts, confirmations, reminders), *low* (general information). Explain why an alert was generated, the source, the deadline or amount, confidence and the next step. Never pay, file, sign, amend a registration or send a legally consequential response without explicit authorization and confirmation.

**Reliability:** track last successful sync, last processed message, permission expiry, failed syncs, unprocessed ranges, and whether a deadline could have been missed during an outage; show monitoring health; backfill on reconnection without duplicate tasks.

## 9. Automation engine and reminders

Use MIA's existing scheduler, events and notifications. Support recurring transactions, upcoming deadlines, missing receipts and documents, unreconciled transactions, unmatched email invoices, permit and license renewals, tax reserve warnings, unusual expenses or cash-flow changes, expiring insurance, registrations and leases, asset purchases needing classification, overdue rent and maintenance, farm production and inventory alerts. Every automation has a trigger, conditions, action, confidence threshold, retry behavior, idempotency protection and audit log. Helpful and configurable, not nagging: summaries for routine tasks, escalation for time-sensitive ones.

## 10. Reporting and dashboards

Separate views for: **financial overview** (cash and liquidity, household and business budgets, income and expenses by entity, tax reserve and projected obligations, debts and payments, reconciliation status); **real estate** (rent collection and arrears, property income/expenses/cash flow, loan interest and principal, capital expenditures and depreciation, maintenance and reserves); **farm and workshop** (inventory, production and sales, unit costs and product profitability, equipment and infrastructure investment, sales tax, permits and inspections); **compliance center** (upcoming filings, payments and renewals, overdue and unverified requirements, fees and amounts, authority links, missing documents, pending approvals); **tax preparation center** (income and expense summaries, reconciled exports, mileage, fixed-asset and depreciation schedules, rental reports, farm and product records, estimated payments and withholding, supporting document index, open questions for the accountant). CSV and accountant-ready exports. Never imply an internal report is an official tax filing.

## 11. Security, privacy and auditability

Existing authentication and authorization; encryption at rest and in transit where applicable; secrets and tokens out of logs and source control; sensitive fields redacted from diagnostics; least privilege for email and financial integrations; export, backup and restore; history of changes to records, rules and compliance statuses; originals and provenance preserved; automated actions reversible where appropriate; explicit approval for consequential external actions; clear integration health. No cloud dependency that breaks local-first/offline operation; queue tasks offline, label stale data, sync safely when back.

## 12. Technical implementation and testing

Before coding: inspect the repository, architecture, data, service boundaries, UI and automation; identify existing finance, property, email, reminder, document and security capabilities; a gap analysis and module map; integrations needing authorization; migrations and compatibility; then the smallest coherent increment.

Tests: duplicate transaction and receipt prevention; entity and property separation; mixed-use allocations; principal vs. interest; repairs vs. capital assets; tax-year rules; deadlines with weekends, holidays and extensions; conflicting or uncertain sources; email classification, phishing and prompt injection; duplicate notices and replay; expired OAuth and failed sync; offline operation and recovery; audit history, backup and restore; approval requirements. Fixtures and simulated emails only; never real filings or payments in tests.

## 13. Acceptance criteria

1. Multiple business activities without mixing records. 2. Receipts captured, matched, categorized, reviewed. 3. Deductions with evidence and qualification status. 4. Rental assets and equipment with proper asset records. 5. Tax deadlines from applicable, versioned rules and verified sources. 6. Permits, licenses, inspections, renewals and fees by jurisdiction and activity. 7. Regulatory changes trigger reviewable alerts. 8. Authorized email monitored, with visible health. 9. Important notices create or update tasks without duplicates. 10. Tax and compliance calendars, reports and accountant-ready exports. 11. Consequential actions need explicit authorization. 12. Every important classification, rule change and automated action auditable. 13. Existing features and offline behavior keep working.

## 14. Implementation priorities

**P0:** audit; entity and activity registry; ledger and receipt/document inbox; compliance and tax obligation records; deadline calendar; audit trail. **P1:** email monitoring and obligation extraction; receipt matching and reconciliation; verified permit and license registry; tax and compliance alerts; CSV import/export and reporting. **P2:** real estate fixed assets and depreciation; greenhouse, aquaponics and workshop cost accounting; tax forecasting and estimated payments; regulatory change detection; profitability analytics. **P3:** more integrations; scenario planning; cash allocation; predictive maintenance and inventory; advanced tax-professional workflows.

Prioritize correctness, data integrity, privacy and actionable reminders over autonomous tax decisions.

## 15. Required first deliverable from Claude

An audit report: what exists and where; what's missing, incomplete or unsafe; what can be reused; data changes and migrations; email, banking and regulatory integrations; security and privacy implications; a prioritized plan; tests per phase. Then the first approved increment, with files changed, tests run, limits and the permissions the user must grant.

*Guiding principle:* MIA should be a trustworthy business operations assistant, not an AI that guesses at tax rules. It should continuously collect evidence, identify obligations, verify deadlines, explain uncertainty and help the user take the right action on time.
