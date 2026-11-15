# Procurement & Opportunity Intelligence: how it fits World Intelligence, and the plan

*Claude (Opus), 2026-11-15, answering the handoff "Procurement & Opportunity Intelligence System" (kept verbatim:
[`prompts/19_PROCUREMENT_OPPORTUNITY_INTELLIGENCE.md`](prompts/19_PROCUREMENT_OPPORTUNITY_INTELLIGENCE.md)). The
handoff's section 16 asks for an investigation and an integrated proposal before any scraper or app is built. This is
that proposal. World Intelligence itself is approved (DEC-0170, Zac, 2026-11-15); this part is proposed as DEC-0172.
Nothing here is built.*

## 1. The headline

**Procurement is World Intelligence pointed at one question: what does Zac need, and where is it cheapest and
best?** It adds no new pipeline. It adds four things the World Intelligence plan didn't have:
1. **Requirements:** what each project needs, line by line, with specifications and a status, made in code from the
   plans MIA already calculates.
2. **Specifications:** what a product actually is (a pump's flow at a given head, a board's size and grade), read in
   code, so "the same" and "good enough" are decided by numbers, not titles.
3. **Price observations:** every price MIA reads, kept, so a "sale" can be checked against what she has seen.
4. **An acquisition plan:** a project's missing pieces gathered into one list, priced per store, grouped into trips,
   against its budget.

Everything else is the World Intelligence loop as approved: watches, sources, the discovery store, the relevance
score, the gate, links, the UAL.

## 2. What already exists, and what's new (16: components, interfaces, new infrastructure)

| The handoff asks for | Already in MIA | Verdict |
|---|---|---|
| What a project needs | `core/plan_library.py` (plans) and `core/build_calcs.py` (quantities and cuts, in code, DEC-0118); the development engine's `needs` per step (DEC-0144) | **Reuse**: requirements are generated from these |
| Projects, budgets, progress | `core/project_manager.py` (`budget`, tasks), `core/mission_projects.py` (missions toward a project, progress derived) | **Reuse**; requirements name a project the way missions do |
| What he owns | `core/inventory_manager.py` (name, quantity, category, location, notes), `core/maintenance_manager.py` assets (maker, model, serial, purchase date and price, warranty, documents), `core/asset_parts.py` (parts for a machine), the kitchen's pantry | **Extend**: inventory gains specifications, condition, consumable, last confirmed |
| Groceries | `core/kitchen_manager.py` (pantry, the grocery list, recipes' missing ingredients), `core/meal_plan.py` | **Reuse**: the grocery list is a requirement list for the week |
| Spending | `core/budget_manager.py` (expenses, the budget), Plaid's transactions | **Reuse**: a purchase he makes is recorded through it |
| Discovery, sources, watches, relevance, the gate, the World page | World Intelligence (approved) | **Reuse**: procurement is its listings half |
| Browser skills on retail sites | DEC-0123 phase 2 browser steps, World Intelligence section 6 | **Reuse** |
| Never buying alone | `browser_safety` (every buy, pay, order, bid is a commit a person approves, DEC-0117) | **Reuse**, unchanged |

**New infrastructure:** the requirement store, product specifications and their comparison, the price-observation
log, the acquisition plan, and a Procurement view on the World page.

## 3. Architecture (deliverable 1)

```
 plans, build_calcs, development engine, grocery list, his own words
        │  (in code)
        ▼
 Requirements (per project: item, qty, specs, alternatives, ceiling, condition, priority, by-date, status)
        │                         ▲ inventory and equipment mark lines owned / partly owned
        ▼                         │
 Watches made from open requirements (World Intelligence: watches MIA makes herself)
        ▼
 Sources (feeds, APIs, browser skills, capture) → discoveries, each with specs read in code
        ▼
 Comparison (identical / equivalent / similar / not suitable) + price observations
        ▼
 Opportunity score (World Intelligence's relevance + procurement's dimensions), with reasons
        ▼
 World page › Procurement; briefings through the gate; acquisition plan per project
        ▼
 He buys (his press, always) → "I bought it": inventory, requirement acquired, budget expense, mission objective
```

## 4. Marketplace source adapters (deliverable 2)

The World Intelligence `Source` contract, unchanged, with one more method for stores:

```
def price(product_ref, place) -> PriceObservation   # a store's price (and stock, when shown) for one product, at one store
```

Sources by kind (the full list with what answered is World Intelligence section 5b):
- **Official APIs:** eBay Browse, GSA Auctions, Kroger's Products API (prices and stock by store), the Walmart
  affiliate API. Each needs a free key; **Zac: skip the keys for now (2026-11-15)**, so these wait and the same stores
  are read by browser skill meanwhile.
- **Browser skills he demonstrates:** Lowe's, Home Depot, Menards, Walmart, Target, Kroger, Aldi, Amazon, Alibaba,
  Temu, Wish, AliExpress, Marketplace, Craigslist, the auction sites, Tractor Supply, local stores' own sites.
- **Capture:** "track this" on any product page, from the phone or the UAL.
- **Local places that have no website worth reading** (a sawmill, a salvage yard, a small auction house): kept as
  places with what they carry, so a requirement can say "call the sawmill" as an option, with no automated reading.

## 5. Cross-market comparison (deliverable 3)

**Specifications, in code.** Each product category has a small schema (`core/product_specs.py`, new) of the
specifications that decide whether it does the job, with units:
- a water pump: flow (gallons per hour) **at a stated head**, maximum head, watts, volts, submersible or inline,
  inlet and outlet size, rated for continuous use;
- a board: nominal size, length, species, grade, treatment (and rated for ground contact);
- PVC pipe: diameter, schedule, length, pressure rating;
- greenhouse film or panel: material, thickness, width, UV rating and years;
- a fan: airflow (CFM), size, volts, thermostat;
- a sensor: what it measures, range, accuracy, interface (I2C, 1-Wire, analog), supply voltage;
- grocery items: size and unit, so a price per ounce or per pound is computed.

Values are read from the listing's own specification table or text by rules (numbers with units, normalised), never
by the model's guess. A value not found is unknown.

**The four verdicts:**
- **Identical:** the same maker and model, or the same UPC/GTIN.
- **Equivalent:** every specification the requirement states is met (the pump moves at least the flow needed at the
  system's head, at the right voltage, rated continuous).
- **Similar:** same category, but a stated specification is unknown or short; shown with what's missing.
- **Not suitable:** a stated specification fails.
A comparison only ranks identical and equivalent products by total cost; similar ones are listed apart. Two pumps
with the same watts and different flow at head are never "the same".

**Total cost:** price + shipping + sales tax (the region's rate) + import duty where it applies + the trip (distance
and his cost per mile) or delivery fee + any core charge, deposit or minimum order. Each part names where it came from;
an unknown part is shown as unknown, not as zero.

**Quality and reputation:** the seller's rating and age, the product's review count and average where the page shows
them, warranty and return terms, and the comparison's own concerns (section 9). Reviews are counted, not summarised by
the model into a verdict.

**Price history:** `price_observations.jsonl` (personal, sealed), one line per price read: product identity, source,
store, price, unit price, in stock, time. From it, in code: a **genuine discount** is a price below the lowest MIA has
seen in the last 90 days (or below the median of at least five sources' prices today); an **inflated "was" price**
is a "was" higher than any price she has seen; **recurring sales** are seen after a few cycles. Before enough
observations exist she says "I've watched this for 12 days", never a history she doesn't have. Outside price-history
sites aren't used to invent a past.

## 6. Project-aware procurement (deliverable 4)

**A requirement** (`core/requirements.py`, new, personal store `requirements.json`, a `kind:id` ref
`requirement:ab12`):

| Field | Notes |
|---|---|
| project | the project it belongs to (or the week's groceries) |
| item, category | in the category's words ("greenhouse film", "2x4x8 stud") |
| quantity, unit | from `build_calcs` when it came from a plan |
| specs | the category schema's fields that matter, with the needed values |
| alternatives | other items that do the job ("6 mil poly or twin-wall polycarbonate") |
| compatibility | with an owned asset (`asset:...`): "fits the 1 inch inlet of the pump" |
| ceiling | the most it should cost, from the project's budget, or his |
| condition | new, used, any |
| priority | needed first, later, nice to have |
| needed by | a date, or a season from the development engine |
| status | needed, partly owned, owned, found (an opportunity linked), ordered, acquired |

**Where they come from, in code:** a plan's material list (`build_calcs`), the development engine's next step's needs,
the grocery list, or his words ("for the greenhouse I need four fans"). Owned lines are marked from inventory and
equipment, so the greenhouse example's table (covering needed, pump owned, lumber partly available) is worked out, not
typed in.

**Requirements drive discovery:** every open requirement becomes a watch (World Intelligence's watches MIA makes
herself); a match links the discovery to the requirement (`discovery MEETS requirement`), so the project's page shows
progress: "7 of 12 lines found or owned; $340 of $500 budget planned".

## 7. Inventory intelligence (deliverable 5)

Inventory is extended, not replaced:
- **New fields on an inventory item:** specs (the same category schema), condition, consumable or reusable,
  purchase (date, price, where: a link to the budget expense), the projects it's for (links), and **last confirmed**
  (when he last said it's still there).
- **Equipment** stays in the maintenance assets (they already have maker, model, purchase and warranty); a
  requirement's compatibility check reads them.
- **The six questions** (the handoff's section 5) become checks, in code, before any purchase is suggested: owned?
  an owned equivalent (same specs)? can owned materials do it (a requirement's alternatives)? replacement or extra
  (an owned one marked broken or worn)? does it complete a requirement? and would the same money finish more of the
  project elsewhere (the acquisition plan's view)?
- **Never assumed still there:** an item not confirmed for six months counts as "probably have, check", and a
  requirement that relies on it says so. "Do I still have the PVC?" is a question in the weekly report, not a guess.
- **Filling inventory:** by voice, on the page, from a receipt in the document inbox (it already reads receipts), and
  from "I bought it" on a found opportunity.

Inventory connects to personal knowledge the way every store does: through links, the history and the life state.

## 8. Opportunity scoring and ranking (deliverable 6)

The World Intelligence relevance score, with the handoff's dimensions named on every opportunity:

| Dimension | How it's computed |
|---|---|
| Project relevance | the requirement it meets and that requirement's priority |
| Price advantage | total cost against the best identical or equivalent seen (a number only when compared; else "not yet verified") |
| Compatibility | the requirement's specs and compatibility checks: met / unknown / failed |
| Quality | seller and product standing, warranty, the concerns found |
| Urgency | auction end, listing age, stock shown, a needed-by date |
| Geographic accessibility | distance from home (default up to 360 miles, Zac's answer to Q-20), the trip's cost |
| Total cost | section 5 |
| Strategic value | the development engine's compounding value of what it unlocks |
| Confidence | the extraction's confidence and the source's standing |

**The recommendation** is one of: *buy when ready* (equivalent or identical, a verified saving, within budget),
*investigate* (attractive but something unverified), *wait* (a better window seen in the price history, or not needed
yet), *skip* (not suitable, or already owned). The handoff's example reads exactly as it shows: asking price $60,
relevance high, compatibility potentially suitable, condition to verify, local pickup, savings not yet verified:
**investigate**. "Bargain" is never said without a verified saving.

## 9. Watchlists and monitoring (deliverable 7)

A procurement watchlist is a World Intelligence watch with a requirement behind it (or a category he names: "CNC
machines under $1,500"). It carries every field in the handoff's list: criteria, ceiling, area, preferred sources,
specs, condition, notification threshold, projects, frequency. Watchlists made from requirements stay in step with
them: buy the fans and the fans' watch stops. The handoff's example lists (Homestead, Workshop, MIA Development,
Property Development) are offered as starting watchlists, each drafted from his real projects and assets and started
on his yes.

**Many sources at once:** each watch's run goes to all its sources in turn, each at its own pace and limits (World
Intelligence section 5); the runtime's scheduler spreads runs so no site is read in a burst.

## 10. International suppliers (deliverable 8)

World Intelligence section 7c's checks, extended to the handoff's list, each a named concern in code:
- **Shipping, duty, delivery time, minimum order** in the total cost; Alibaba's bulk price shown apart from a retail
  price and only compared per unit at the minimum order.
- **Certification:** electrical, gas, structural or safety-critical items need a listing mark (UL, ETL, CSA) named on
  the page, or they're "not for this use without checking".
- **Electrical compatibility:** voltage and frequency (120 V, 60 Hz here) and plug type, read from the specs; a 220 V
  or EU-plug item is flagged.
- **Warranty and returns:** shown as stated; "returns to the seller abroad" is a concern.
- **Counterfeit and misleading risk:** a famous brand far below its usual price, a title naming several brands,
  specifications that contradict each other, photos of a different product than the title: each a concern.
- **Inexpensive is not reliable:** the score's quality dimension weighs these; a cheap item with concerns can't be
  "buy when ready".

## 11. Acquisition planning (deliverable 9)

**An acquisition plan** (`core/acquisition.py`, new) per project, worked out in code:
- the open requirements, each with its best option (or options), its total cost and its source named;
- the project's total against its budget, and what's left;
- **trips:** options grouped by place, so one drive to the nearest city covers three stores, with the drive's cost once;
- priorities and the needed-by order;
- alternatives for each line;
- **what's still hard to find**, carried to the weekly report.

It becomes missions through what exists: "Get the greenhouse materials" as a mission with one objective per trip or
line, toward the project (DEC-0152), MIA as the giver, on his yes. A purchase can be a project milestone (a task done).
Nothing is bought by the plan: each line's "buy" opens the store's page for him, and a buy in her browser is a commit
he presses.

**After he buys** ("I bought the fans", a receipt in the inbox, or a Plaid transaction matched to a found item): the
requirement is acquired, inventory gains the item with its price and place, the budget gets the expense (if it wasn't
already there from the bank), and the price joins the observations. One action, with undo.

## 12. Groceries and everyday deals (Zac, 2026-11-15: Amazon, Walmart, Target, Kroger, "grocery shopping and deal buying")

The same machinery, at the week's scale:
- **The grocery list is the week's requirements** (the kitchen's list, with recipes' missing ingredients already
  added), each line with a size so unit prices compare.
- **Priced at his stores** (Kroger, Walmart, Aldi, Target, Amazon), per store, each named; the cheapest whole basket,
  and the cheapest split counting the second stop.
- **Deals:** weekly ads and digital coupons read by browser skill where the store's site shows them; a staple he buys
  often (from the meal log and pantry) gets a price watch, and a real low (by the observations) on one that keeps is
  offered as "stock up".
- **Everyday wants:** a product he names ("a good cordless drill") is a watch with the same comparison and the same
  "never confuse the asking price with a bargain".

## 13. The Procurement view (deliverable 10)

A section of the World page (the design is Muse's), on every device, with voice parity:
- **Opportunities:** found items ranked, each with its source named, recommendation and reasons.
- **Watchlists:** his and hers, with what each found.
- **Projects:** each project's requirements table with status, the acquisition plan, budget used and left.
- **Compare:** a product's identical and equivalent options across sources, total cost each, specs side by side.
- **Inventory:** what he owns, filterable by project, with "check" on stale lines (it opens the existing inventory and
  equipment screens rather than duplicating them).
- **Saved:** opportunities kept for later.
- **History:** what he bought, where, for what, and the price against what was seen.
- **Reports:** the weekly report and past briefings.

By voice: "what do I still need for the greenhouse?", "find me the cheapest reliable pump for the aquaponics",
"price the grocery list", "I bought the fans", "do I have PVC?", "add four fans to the greenhouse".

## 14. Notifications and briefings (deliverable 11)

Through the communication gate only, with its learned pacing (DEC-0171):
- **Right away:** an opportunity that's *buy when ready* or an auction worth it ending soon, for a high-priority
  requirement, near home. Whether this kind truly deserves interrupting him is learned from what he does with them.
- **Daily briefing:** one consolidated message (the gate already consolidates) of the day's best finds, if any.
- **Weekly report:** best opportunities, notable price changes, requirements newly findable, savings so far,
  what's still hard to find, and inventory lines to confirm.
Each is a kind of message to the gate, so each learns its own pace.

## 15. Security and permissions (deliverable 12)

World Intelligence's model (section 10), with procurement's lines:
- **May do within a grant:** search, read listings and store pages, compare, save, watch prices, prepare plans,
  propose requirements (a proposed requirement is shown for his yes; it doesn't change a project by itself).
- **Never without his own press, every time:** buy, order, add to a cart that checks out, bid, offer, message a seller,
  negotiate, accept terms, share his address or details, any payment. These are commits (`browser_safety`) and outward
  actions (DEC-0156: never granted). A learned skill doesn't change that.
- **Listings are untrusted** (World Intelligence section 10): extracted in code, reaching the model only as
  `untrusted()` text.
- **Privacy:** requirements, observations, plans and purchase history are personal and sealed at rest. His home place
  is a record in his own folder, never in the repository.

## 16. Data models and API contracts (deliverable 13)

**Stores** (personal, `PERSONAL_STORES`, atomic writes with undo, sealed):

| Store | Holds | Ref |
|---|---|---|
| `requirements.json` | section 6's fields | `requirement:id` |
| `price_observations.jsonl` | product identity, source, store, price, unit price, stock, time | — |
| `acquisition_plans.json` | per project: chosen options, trips, totals (derived, cached, rebuilt on change) | `acquisition:id` |
| inventory (extended) | section 7's new fields, defaulted for old records | `inventory:id` |
| discoveries (World Intelligence) | gains `specs`, `product_identity`, `total_cost` parts | `discovery:id` |

**Action kinds** (`core/actions.py`, each with undo, each also a voice tool, DEC-0125): `requirement.add`,
`requirement.update`, `requirement.remove`, `requirements.from_plan`, `inventory.confirm`, `discovery.link_requirement`,
`acquisition.plan`, `acquisition.to_mission`, `purchase.record` (the "I bought it" action), `watchlist.add` (a watch).

**Endpoints** (`server/app.py`, the signed-in person's own view): `GET /api/procurement` (the view's data, assembled
in `core/web_world.py`), `GET /api/procurement/project/{id}` (requirements and plan), `GET /api/procurement/compare/{requirement}`,
`GET /api/procurement/history`; changes go through `/api/actions` as every screen's do.

**UAL actions:** "Track this", "Is this a good deal?", "Compare this", "Add to a project's needs" on any selection or
product page.

## 17. Testing and acceptance (deliverable 14)

| Criterion | Test |
|---|---|
| New marketplaces by adapter | a stand-in store adapter added with no other change |
| Many marketplaces at once | one watch run over three stand-in sources, paced and logged |
| Connected to requirements | a fixture listing links to the right requirement; its project's progress moves |
| Equivalent compared | two pumps with the same watts and different flow at head are not equivalent; same model is identical |
| Total cost | each part named; an unknown part is unknown, not zero |
| Inventory influences | an owned item is never suggested; a requirement owned in part shows only the rest |
| Fewer duplicate purchases | a product he bought last month is flagged if found again for the same requirement |
| Explainable ranking | every opportunity's dimensions and recommendation come with reasons and their records |
| Price history kept | observations accumulate; "genuine discount" needs them; no history before the first one |
| International risks | a 220 V item, an unlisted breaker, an MOQ and a long delivery each produce their concern |
| Continuous watchlists | a requirement's watch runs on schedule and stops when it's acquired |
| Proposed milestones | an acquisition plan becomes a mission on his yes, linked to the project |
| Governed purchasing | no action, tool or skill step can buy, bid or message; a test sweeps the registry |
| Scales | categories and sources are tables; adding one needs no change elsewhere |

Fixtures are saved pages; nothing touches the network in tests.

## 18. Roadmap (deliverable 15)

Procurement's phases slot into World Intelligence's (proposal section 16), after the pieces they need:

| Phase | What | After | Model |
|---|---|---|---|
| P1 | Requirements from plans, the grocery list and his words; inventory's new fields; owned-line marking | W1 | Opus |
| P2 | Product specs (the first categories: pumps, lumber, PVC, film, fans, sensors, groceries), verdicts, total cost, price observations | W2, P1 | Opus |
| P3 | Requirements drive watches; opportunity score and recommendations; the Procurement view | W1b, P2 | Opus |
| P4 | Store skills (Lowe's, Walmart, Kroger, Target, Amazon first), groceries priced per store | W5 | Opus (Fable for unattended runs) |
| P5 | Acquisition plans, trips, missions, "I bought it" | P3 | Opus |
| P6 | International checks; briefings and the weekly report | P3, W1 | Opus |

The official APIs (eBay, Kroger, Walmart, GSA) wait for the keys Zac skipped for now.

## 19. Questions

- **Q-21.** Approve procurement as World Intelligence's listings half (DEC-0172), in phases P1 to P6?
- **Q-22.** His cost per mile for trips (for total cost): use the IRS standard rate as a default, or his own figure?
- **Q-23.** For groceries, which stores does he actually shop at, and does he want pickup or delivery prices too?
