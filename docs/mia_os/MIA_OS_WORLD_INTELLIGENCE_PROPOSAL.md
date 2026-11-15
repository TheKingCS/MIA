# World Intelligence: how it fits MIA, and the plan

*Claude (Opus), 2026-11-15, answering the handoff "World Intelligence, Opportunity Discovery & Demonstration-Based
Browser Automation" (kept verbatim: [`prompts/18_WORLD_INTELLIGENCE_EXPANSION.md`](prompts/18_WORLD_INTELLIGENCE_EXPANSION.md)).
The handoff's section 16 asks for an investigation and an integrated proposal before anything is built. This is that
proposal. Nothing here is built or approved. DEC-0170 is the proposed decision; Q-16 to Q-20 are the questions for Zac.*

*Updated the same day with Zac's answers (DEC-0171): no fixed limit on the messages MIA starts herself, pacing learned
from what he engages with instead; MIA also makes watches herself from his life; Marketplace, Craigslist, eBay and
sites like them are read by the browser skills he demonstrates; about four finds a day to start. Section 5b lists the
starting sources, checked from the PC, and how MIA keeps improving them.*

## 1. The headline

**About two thirds of World Intelligence is already in MIA, in separate pieces.** What's missing is the part in the
middle: a standing watch that runs by itself, one store of discoveries with provenance, and a relevance score worked
out in code from MIA's real records. Building that thin middle, and connecting the pieces she already has, gives the
whole loop. A new engine would duplicate six existing systems.

| The handoff asks for | Already in MIA | Verdict |
|---|---|---|
| Reading outside sources on a schedule | Good News Radio (`core/good_news.py`): fixed feeds read once a day in a process of its own, judged in code, switched on by the person | **Reuse the pattern**; generalise it into source adapters |
| Searching the web | `core/online_lookup.py` (DEC-0053): the person's own SearXNG, search words scrubbed, offer first | **Reuse**; a watch is the "asked" |
| Research and verification | UAL Research This and Verify These Claims (`core/ual.py`, section 6g of the UAL plan): sourced reports, a verdict checked in code against the claim's own results | **Reuse** as the research step |
| A browser MIA drives | `core/browser.py` (DEC-0117): her own profile, controls picked by role and name, every step sorted by `browser_safety.classify()`, commits approved only by a person | **Reuse**; nothing new goes around the gate |
| Learning a website task by demonstration | `core/browser_routines.py`: records clicks by role and name, never a password; replays and stops where the page differs; two clean runs make it learned | **Reuse and extend** (extraction, versions, repair) |
| Reusable, inspectable skills | `core/taught_skills.py` (DEC-0123, DEC-0167): steps, practice state, gates per step; phase 2 already plans browser steps and triggers | **Extend**; browser skills are taught skills with browser steps |
| Text from outside never instructs MIA | `browser_safety.untrusted()` and `carries_outside_text()`; DEC-0122 (she types only the person's own words) | **Reuse**, mandatory for every source |
| The person's goals, projects, resources | intents (`core/intent_manager.py`), projects and missions (`core/mission_projects.py`), inventory and equipment, the budget, places, the development engine's `needs` (`core/development_engine.py`) | **Reuse**; these are the relevance inputs |
| Connecting a discovery to everything | `core/links.py` (typed `kind:id` links), `core/life_events.py` (the history) | **Reuse**; a discovery becomes a new kind |
| Bringing worthwhile things up | the communication gate (`core/communication_gate.py`: five a day, repeats dropped, every decision logged) | **Reuse**; nothing new pushes |
| Durable "MIA noticed X" records | `core/insight_manager.py` (insight and recommendation, deduplicated, resolved later) | **Reuse** for what a discovery recommends |
| Turning a discovery into action | missions, projects, `path.draft` (learning paths), the lab (`core/dev_lab.py`), capability gaps (`core/capability_gaps.py`), the action contract with undo (`core/actions.py`) | **Reuse** |
| Self-development monitoring | Night School, the development lab, `core/model_bench.py` (a model scored on MIA's own golden set), capability awareness (`core/capabilities.py`) | **Reuse**; add the outside half (what's been released) |
| Permissions per source and action | DEC-0156 (grants with tiers), **proposed, not built**; the UAL's read/prepare/act tiers | **Gap**: World Intelligence is the first real user of grants |

**Not in MIA at all:** a standing watch (`Watch`), a discovery store with provenance and change history, source
adapters beyond the news feeds, the relevance score, extraction rules in a browser skill, and a page for it.

## 2. Conflicts with decisions already made, and how this resolves them

1. **DEC-0053: online only when asked.** World Intelligence goes online by itself. **Resolution:** switching World
   Intelligence on is the asking, once, as Good News Radio is switched on once (DEC-0096). Every watch, whether Zac
   set it or MIA made it (section 3), says exactly what goes out (its search words, the sources it reads) and how
   often, and can be paused or deleted. The search words follow DEC-0053's scrub, and never include MIA's records
   about the person: a watch MIA makes is worded from the *kind* of thing a project needs ("polycarbonate panels"),
   never from the record itself.
2. **DEC-0122: she types only the person's own words.** A watch's search words are the person's words, kept with the
   watch, so an approved watch may type them. Words from a listing or a page are never typed anywhere.
3. **The communication gate's five a day: changed by Zac (DEC-0171).** On MIA OS there's no fixed daily limit on
   what she starts herself. The gate learns instead: what he opens, acts on or answers raises that kind of message,
   what he dismisses or ignores lowers it, per kind (it already pauses a kind he keeps dismissing). The spacing,
   the "nothing new" rule and the busy check stay. World Intelligence starts at about **four finds a day** and moves
   with what he does with them. Everything kept is on the World page whatever is offered. Each candidate has a
   fingerprint per listing and change, so an unchanged listing is never offered twice.
4. **Facts in code, the model only phrases** (CLAUDE.md, DEC-0144). On a 3B model, "is this relevant to my life?"
   can't be the model's call. The relevance score is computed in code from the records (section 4). The model may
   phrase why something matters, from the reasons the code produced, and it may help pull fields out of free text.
   Any price or specification it reads is checked against the page's own text before it's kept.
5. **Website terms against the Marketplace example: decided by Zac (DEC-0171).** Claude raised that Facebook's and
   Craigslist's terms appear to forbid automated collection. Zac's answer: MIA only repeats steps he showed her and
   could do himself, taking down public information, so Marketplace, Craigslist, eBay and sites like them are read
   by his demonstrated browser skills. What stays from the handoff's 5.4, in code: a person's pace (a few pages a
   minute, a run a few times a day at most); never past a CAPTCHA, a block or an "unusual traffic" page (the run
   stops and the source waits for him); never anything that commits. The one risk to know: Marketplace needs a
   Facebook sign-in, so it's his account the site sees, and a site that objects can restrict that account. Where a
   site offers an official API (eBay's Browse API), it's used instead of its pages.
6. **DEC-0156 grants are only proposed.** An unattended browser run is the first thing in MIA that acts with nobody
   watching. It needs grants built first, at least for this subsystem (section 10).
7. **DEC-0168: MIA OS first; new features only in the engine and the web.** World Intelligence is engine and web
   only, so it fits. Its watches run in the MIA Runtime's scheduler (`core/background_jobs.py`), so they work the
   same headless on Fedora and the Pi. On Linux the browser is Playwright's Chromium, not Edge; `core/browser.py`
   should name the browser by setting, not assume Edge.

## 3. World Intelligence architecture (deliverable 1)

One loop, each stage an existing system where one exists:

```
 Watch (what to look for, where, how often, who asked)          core/world_watch.py (new, small)
   │  run by the runtime's schedule                              core/background_jobs.py
   ▼
 Source adapter (feed / API / search / browser skill / capture)  core/world_sources.py (new) + existing readers
   │  returns raw items, each with source, URL, time fetched
   ▼
 Normalise + extract (fields read in code; model only for prose)  per adapter
   │
   ▼
 Discovery store (dedupe, change history, provenance)            core/discoveries.py (new store)
   │
   ▼
 Relevance score (in code, from her records)                     core/relevance.py (new, pure)
   │
   ├─▶ World page (everything kept, sorted by score)              web/world.html + core/web_world.py
   ├─▶ communication gate (only the top few)                      core/communication_gate.py
   └─▶ actions: research it, save to a project, make a mission,   core/actions.py, links.py,
       purchase consideration, learning path, lab proposal        missions, paths, dev_lab, insights
```

- **A watch** (`Watch`): id, a name in the person's words, the kind of thing (listings, news, releases, research,
  prices), the sources it may use, search words (the person's own), criteria (price ceiling, distance, condition,
  categories), what it's for (links to intents, projects or missions), how often, whether the gate may offer its
  finds, and its permission (the grant it runs under). Made by voice ("watch for cheap greenhouse panels within an
  hour") or on the page; the parsing of the sentence into fields is shown back for a yes before it's saved.
- **A discovery** (`Discovery`): one thing found, kept once however often it's seen (section 11).
- **Where it runs:** the runtime's scheduler starts due watches; each run is a job with a time limit, like the
  daily checks. A run that needs the network and finds none waits for the next.
- **Whose it is:** a person's watches and discoveries live in their own folder (personal stores). A household watch
  is out of scope (DEC-0119: MIA is for Zac).

**Watches MIA makes herself (Zac, DEC-0171: "automate watching for things, not just ones I set").** Each week, and
whenever a project, intent or plan changes, MIA works out watches from the records, in code:
- a project's materials still needed (`plan_library`, `build_calcs`) become listing watches with the project's budget
  as the ceiling;
- the development engine's next steps and their `needs` become watches for those needs, in the season they're due;
- open intents and learning paths become topic watches (news, research, courses);
- equipment and machines become watches for their parts, recalls and manuals, and for newer models when one is old;
- what MIA is built on becomes the self-development watch (section 14).

Each one is marked "made by MIA" with the record it came from, shown on the Watches tab, and stops by itself when its
reason does (the project finished, the material bought). Zac can stop or change any of them; one he stops isn't made
again for that reason. Which ones he engages with shapes which kinds she makes next.

## 4. Personal Relevance Engine (deliverable 2)

`core/relevance.py`, pure functions, every point traceable to a record. It scores a discovery against the person's
**context**, assembled once per run from the stores (the same way `context_assembler.py` does), never a copy kept
aside:

| The handoff's factor | What it's read from | How it scores |
|---|---|---|
| 1. goals | intents (open, primary weighted higher) | words and tags of the intent in the item |
| 2. missions and projects | active projects, their tasks and plan material lists (`plan_library`, `build_calcs`), missions | a match to a material a project still needs scores high; to a finished one, nothing |
| 3. expressed interests | learning paths, the watch itself, past "useful"/"not for me" feedback on discoveries | feedback moves the weights for that watch, counted, not learned by a model |
| 4. resources and equipment | inventory, equipment, the development engine's `have` | already owned lowers the score; a part that fits what's owned raises it |
| 5. money | the budget (a project's budget left, the watch's ceiling) | over the ceiling scores zero; under it, the saving against comparables |
| 6. place | places and the person's region; the listing's stated location | distance in code (`places.distance_m`) when a location is given; unknown distance is said, never guessed |
| 7. compatibility | equipment records (model, size, voltage when kept) | only stated facts compared; unknown is "check" |
| 8. long-term value | `development_engine` `needs` and `compounding_value` | a find that provides what the next step on a path requires scores highest of all |
| 9. urgency | listing age, an end date, a seasonal window from the development engine | sooner and in-season score higher |
| 10. reliability | the source's standing (official API, known outlet, classified ad), the extraction's confidence | a low-confidence field caps the score and is shown as uncertain |

- **The output** is a score with its **reasons** (each a sentence and the record it came from, like "the walipini
  project still needs 12 polycarbonate panels"), the **life areas** it touches (more than one when it does), and a
  **class** from the handoff's section 7: interesting, possibly useful, verified opportunity, recommended action, or
  needs more research. A recommendation is only made from reasons, never from the model's opinion.
- **Dynamic by construction:** the context is read fresh each run, so a finished project stops pulling finds and a
  new intent starts.
- **The development engine is the key input.** It already knows what each next step needs and what's already on hand
  (DEC-0144). "This listing provides what your next step needs" is the single most valuable reason World
  Intelligence can give, and it's computed, not guessed.

## 5. Source adapters and monitoring (deliverable 3)

A source adapter is a small class with one contract, registered in a table, so a new source is a new adapter and
nothing else changes (the handoff's first acceptance criterion):

```
class Source:
    id, name, kind            # "feed" | "api" | "search" | "browser_skill" | "capture"
    allowed: terms_checked, needs_account, rate (max runs a day), online (True)
    def fetch(watch, since) -> list[RawItem]      # RawItem: source id, URL, fetched_at, fields, raw text
    def verify(discovery) -> Status               # still there? price now? (for listings)
```

The first adapters, in the order they're safest:
1. **Feeds** (RSS and Atom): the reader Good News Radio already has, generalised. Covers news outlets, many
   government and research announcements, and GitHub releases (each repository publishes an Atom feed of releases).
2. **Official APIs**, each with its key kept sealed: eBay's Browse API (needs a free developer key), GitHub's
   releases API, arXiv's API, others as Zac chooses. Which ones is Q-18.
3. **Search** through the person's SearXNG (`online_lookup.search`), for "news about X".
4. **Browser skills** (section 6), only for sites whose terms allow automated reading, and only under a grant.
5. **Capture** (no network of MIA's own): the page Zac is looking at, sent through the UAL ("Track this listing",
   "Is this a good deal?"), or a listing URL he pastes. This is how Marketplace and Craigslist work (section 7).

**Monitoring rules, in code:** each source has a rate limit and a backoff on errors; a run never retries a page
that refused it; a CAPTCHA, a sign-in wall or an "unusual traffic" page stops the run, marks the source as needing
Zac, and is never worked around (handoff 5.4). Each run is logged (watch, source, items found, new, changed, time).
The feed reader uses `certifi`'s certificates: on the PC's Python, arXiv and Grants.gov fail certificate checks
without it (found in the check below).

## 5b. Starting sources, and how MIA keeps improving them

**Checked from the PC on 2026-11-15** (each address answered with a feed, and its newest item was recent). Addresses
that failed are listed too, so nobody adds them again without a fix.

| Area | Sources that work | Kind |
|---|---|---|
| MIA's own stack (self-development) | releases of Ollama, llama.cpp, Playwright for Python, Home Assistant (GitHub's `releases.atom` for each repository); GitHub's advisory API for pip packages; CISA's Known Exploited Vulnerabilities (JSON) | Atom, JSON API |
| AI and local models | Hugging Face blog; OpenAI news; Mistral news; Simon Willison's weblog; Hacker News filtered (hnrss.org, by words and points); arXiv cs.AI and cs.CL | RSS, Atom |
| Linux, hardware, boards | Phoronix (AMD GPUs, ROCm, Linux); LWN headlines; Fedora Magazine; Raspberry Pi news; CNX Software; Tom's Hardware; Hackaday | RSS |
| Smart home and IoT | Home Assistant blog; Home Assistant releases | Atom |
| Homestead, farming, building | USDA Agricultural Research Service news; Modern Farmer; Mother Earth News; Hobby Farms; ScienceDaily agriculture and food; Fine Homebuilding; Family Handyman; Make: | RSS |
| Energy and solar | pv magazine USA; Electrek; Canary Media; CleanTechnica | RSS |
| Grants, programs, rules | Grants.gov new opportunities (by agency and by category; filter USDA by its program numbers, which start with 10); the Federal Register (RSS and a keyless JSON API, filtered by agency, here the USDA); SBA news | RSS, JSON API |
| Money and property | Freddie Mac's weekly mortgage survey (its history CSV); Calculated Risk (housing); FRED's API (needs a free key) for rates and prices | CSV, Atom, API |
| Science | ScienceDaily top science; Phys.org | RSS |
| General news | NPR; BBC World; Ars Technica; The Verge (Good News Radio's outlets stay as they are) | RSS, Atom |
| Listings | eBay's Browse API (local pickup by postal code and radius; needs a free developer key); Marketplace and Craigslist by browser skill | API, browser |
| Auctions (Zac, 2026-11-15: "It should watch auction sites too") | **GSA Auctions** (federal surplus: vehicles, tools, equipment) through GSA's official JSON API, with a free api.data.gov key; **by browser skill:** GovDeals and Public Surplus (city, county and school surplus), Purple Wave, BigIron and Machinery Pete (farm and heavy equipment), IronPlanet, Proxibid and BidCal (equipment and local auction houses), EstateSales.net (estate sales near home), Copart (vehicles); Bring a Trailer by its feed | API, browser, RSS |

| Building materials and home stores (Zac, 2026-11-15) | **by browser skill:** Lowe's, Menards, 84 Lumber, Walmart; Home Depot, Ace Hardware, Harbor Freight and Tractor Supply refused or timed out on a plain request, so they're tried in her browser and fall back to "track this" if blocked there too; **Habitat for Humanity ReStores** near home (donated, discounted building materials, a strong fit for the homestead); local lumber yards and salvage yards Zac names | browser |
| Import marketplaces (Zac, 2026-11-15) | **by browser skill:** Alibaba (bulk, from manufacturers), AliExpress, Temu, Wish; Amazon | browser |

**Auction sites that refused a plain request** (HTTP 403, checked the same day): HiBid, K-BID, AuctionTime, Ritchie
Bros, MaxSold, AuctionZip and Liquidation.com. They block automated readers, so they're browser-skill sources at
most; each one that shows a block or a CAPTCHA to her browser too is left to Zac's own visits and "track this". None
of the auction sites checked advertises a feed.

**Didn't work as tried** (403, 404 or no feed): USDA Rural Development's feed, CISA's advisories feed, AP, Reuters,
the IRS newsroom, EurekAlert, ATTRA, SARE, Permaculture News, This Old House, Google DeepMind's blog (a page, not a
feed), GovDeals' feed. Each may have a feed at another address; MIA's source loop (below) looks.

These are US sources for a US person; the list follows the person's region (`core/region.py`) where an agency is
national. None of this is personal: it lives in the code as the starting catalog (`world_sources.py`).

**The source loop (a continuing self-improvement process, DEC-0094's loops):** a loop `world.sources` in
`core/loops.py`, Observe → Measure → Evaluate → Improve → Verify:
- **Observe:** every item a source gives, and what Zac does with it (opened, saved, acted on, "not for me", ignored).
- **Measure, per source:** how often it answers, how fresh it is, how many of its items scored, how many he used, how
  many were repeats of another source, and how many were wrong (a price or claim later contradicted).
- **Evaluate, monthly:** a source that's dead, stale, mostly repeats or never used is proposed for retirement; one
  whose items keep being used is read more often.
- **Improve:** MIA finds candidates: sites her best finds keep citing, a site's own feed link (its page's
  `<link rel="alternate">`), and searches for feeds on the topics of open watches. Each candidate is checked the way
  this table was (it answers, it's a feed, it's recent, it isn't a copy of one she has) and tried for a month on a
  trial footing before it counts.
- **Verify:** a trial source stays only if its items were used at least as often as the median source's.
- The loop's reports go to the World page's Sources tab and to Night School's notes. Adding a source that needs an
  account or a key, or one that's a browser skill, is proposed to Zac, never done alone.

## 6. Browser observation, demonstration learning, and reusable browser skills (deliverables 4 and 5)

This extends what's built; it doesn't replace it. Today `browser_routines` records a demonstration as steps by role
and name, and `taught_skills` holds skills with a practice state. The plan joins them: **a browser skill is a taught
skill whose steps include browser steps**, as DEC-0123 phase 2 already plans.

**What a demonstration adds:**
- **Parameters.** Typed words that came from the person become slots ("greenhouse" in the search box becomes
  `{search}`), so one demonstration serves every watch that uses it. Shown back for a yes: "When you searched
  'greenhouse', should I put a watch's own words there?"
- **Extraction rules.** During the demonstration the person points at what matters ("this is the price", "this is
  where it says the location"), or MIA proposes fields from the page's structure and asks. A rule is the element's
  role, name and its label nearby, plus a check on the value (a price looks like money, a date like a date). A value
  that fails its check is kept as "couldn't read", never invented.
- **A list step.** "For each result on this page, open it, read these fields, come back", with a maximum per run.
- **Starting conditions** (signed in, on this page), **failure steps** (what to do when a control is missing: stop
  and say where), and **the expected output** (the fields a discovery gets).

**The skill record** carries every item in the handoff's 5.1: purpose, site, starting conditions, steps, parameters,
elements, extraction rules, validation, recovery, permission (its grant), output, known limits. It's **versioned**:
each re-teach or edit is a new version, the old one kept; a run records which version it used. It's shown on the
Taught Skills screen as readable steps and can be edited there.

**Recognising change and repair:** a run compares each step's page title and the controls it expected. A renamed
control is found again by role and nearby label where only one matches (a test pins this); anything else stops the
run and marks the skill "needs repair", with the step and a screenshot. Repair is a new demonstration of only the
broken step. The `browser.runs` loop already counts clean finishes; it gains "needs repair".

**Interaction methods (5.2):** semantic first. `core/browser.py` already reads the accessibility roles and names
through Playwright; that stays primary. The skill format names elements by role, name and label, not by
Playwright selectors, so another driver (a WebExtension over native messaging, as the UAL plan lists for MIA OS, or
a screenshot-based computer-use model for a canvas-drawn site) can run the same skill. Visual interaction is a
fallback a step must ask for, and it's never used to get past a CAPTCHA.

**The lifecycle (5.3)** maps onto taught skills as they work today: demonstrate → MIA shows her understanding (steps,
parameters, fields) → Zac approves → practising (every change asks) → two clean runs: learned → runs under its
grant → each run logged → repair when it stops. **A demonstration grants nothing**: the skill's grant is set
separately, and a commit step inside it still asks every time (DEC-0117).

## 7. Marketplace Intelligence reference workflow (deliverable 6)

"Watch Marketplace for inexpensive greenhouse supplies and equipment that could help me build my homestead."

1. **Understanding the ask (in code, shown back):** what (greenhouse supplies and equipment), the categories (from
   the homestead projects' material lists and the development engine's needs: panels, framing, irrigation, shelving,
   heaters, fans), a price ceiling (asked if none; the projects' budgets suggest one), a distance (asked; the places
   store gives the home point), and what it's for (linked to the homestead intent and its projects).
2. **Choosing sources** (Zac, DEC-0171): eBay through its API with a local-pickup filter; Marketplace, Craigslist and
   local classified or auction sites through browser skills he demonstrates.
3. **Marketplace by his demonstration:** Zac does one search in her browser while she watches: Marketplace, the
   search box, the location and price filters, opening a listing, pointing at the price, the location and the
   description. She proposes the skill with `{search}`, `{max_price}` and `{radius}` slots and the fields to read;
   he approves it; after two clean runs with him watching it's learned. Then each Marketplace watch runs it a few
   times a day at a person's pace, signed in as him in her own browser profile, reading only the result pages and
   the listings it opens. **Capture** stays as well: "MIA, track this" on a listing he found himself, from the phone
   or the UAL's selection menu, keeps it the same way.
4. **Each listing kept** has every field in the handoff's section 6 list. A field not on the page is empty and shown
   as unknown. Photos are kept as their addresses, plus a thumbnail if Zac saves the listing.
5. **Evaluation (in code):** asking price; comparables from MIA's own record of similar finds and, where an API gives
   them, sold prices; the drive there and back (distance × the person's cost per mile, an estimate, labelled); total
   acquisition cost (price + travel + stated repairs); savings against new (from a price Zac or a search gave, with
   its source); the project it serves; concerns found in code (no photos, price far below comparables, "shipping
   only" from a private seller, payment asked off the site): each named, with why.
6. **Deduplication and change:** the same listing (by the site's own listing id, else its address) is one discovery;
   a price drop or a "pending"/"sold" is a change, recorded in its history. A new change can be offered once; an
   unchanged one never again. A listing that's gone is marked gone, not deleted.
7. **Telling Zac:** the World page holds every find, best first. The gate offers at most the top one or two a day,
   and only those scoring "verified opportunity" or higher, each with its reasons.
8. **What MIA never does here:** message a seller, make an offer, buy, share Zac's location or details. Each of those
   is an action he takes himself, or a `browser.commit` he approves on the spot, one at a time.

## 7b. Auctions: what's different from a listing

An auction is a listing with a clock, and its real price isn't the number shown. Everything else in section 7 holds;
these are added, in code:
- **Fields:** current bid, number of bids, reserve (met, not met, none), buyer's premium, sales tax, the end time
  (and whether it extends on late bids), the inspection days, and the **pickup window and place**: many surplus and
  farm auctions give a few days to remove the item, on site, with your own loading.
- **Total cost** = the bid + the buyer's premium + tax + any lot or loading fee + the trip there (with a trailer for
  big items: the distance by the Q-20 defaults) + stated repairs. Shown as a range for a bid still rising: "at
  today's bid about $640 all in; it usually closes higher".
- **A ceiling worked out, not guessed:** from what similar lots sold for. MIA keeps closing prices of every auction
  she's watched (GSA's API and most sites show them after the end), so her comparables grow each month; until there
  are enough, she says so and gives the new price for reference.
- **The clock drives the offers:** a find worth his time is offered when it's found, and again a day before and an
  hour before it ends, each once, through the gate. One ending in the next hour counts as timely.
- **Removal checks:** a pickup window that clashes with his calendar, or a lot too big for what he has to haul it,
  is a named concern.
- **Never a bid.** Bidding is a commitment: MIA can open the lot in her browser with the amount ready, and the press
  stays his (a `browser.commit` he approves, one bid at a time), like every other buy. An auto-bid or a "max bid"
  left on a site is never set by her.

## 7c. Building materials: pricing a whole build

Zac wants this for home-building materials too. The development engine and `core/build_calcs.py` already turn a
plan into a material and cut list (DEC-0118). World Intelligence adds the prices:
- **Price this build:** for a plan's material list, MIA looks up each line at the stores he uses (Lowe's, Menards,
  84 Lumber, Home Depot, Walmart, a local yard, a ReStore) and shows each line's price **per store, with the store
  named**, the cheapest mix (counting a second trip or delivery as a cost), and the single-store total for
  comparison. The quantities come from `build_calcs` in code, never the model; a price is matched to a line only
  when the product's size and grade match (a 2x6x8 #2 SPF, not "lumber").
- **Watching it:** a project's material list becomes a standing watch (section 3, watches MIA makes herself), so a
  sale, a clearance, a ReStore donation or a cheaper used lot is offered with what it saves on that build.
- **Local stock** where the store's page shows it for the nearest store, with the date it was read.
- **Import marketplaces for building and electrical parts** (Alibaba, Temu, Wish, AliExpress) carry extra checks,
  shown as concerns, in code:
  - **Code and safety:** wiring, breakers, panels, outlets, gas parts, structural fasteners and anything for a
    permitted build must carry a recognised listing mark (UL, ETL, CSA); an item whose listing doesn't name one is
    flagged "not for a permitted build without checking", the same professional note `build_calcs` ends with.
  - **Real cost and time:** shipping, import duty where it applies, the minimum order (Alibaba's MOQ) and the
    delivery estimate are part of the total; a three-week wait is weighed against the project's schedule.
  - **Seller standing:** rating, years, number of orders where the page shows them; a new seller with a price far
    below the rest is a named concern.

## Every find names its source

Zac, 2026-11-15: "It should just always list the source." A rule in code, not a style: **every find, everywhere it
appears, shows where it came from** (the site or outlet by name, and a link to the page): on the World page and a
find's sheet, in a message from the gate, on the phone and the glasses cards, and spoken ("from Lowe's, $8.47 a
board, read this morning"). A comparison names each line's store. A summary across sources lists them all. A
discovery can't be stored without a source, and a test fails if any view, card or spoken template can show a find
without it.

## 8. Research and opportunity evaluation (deliverable 7)

"Research it" on a discovery starts a **dossier**, made from steps MIA already has:
1. Identify it (the discovery's own fields).
2. Find its documentation (a search for the product's name and maker; the result's source kept).
3. Independent evaluations (Research This over the top results, each fact numbered to its source).
4. Alternatives (a search for "alternatives to X"; each one a discovery of its own, linked).
5. Compatibility (compared in code against equipment records; unknowns listed as questions).
6. Integration effort (for hardware and software: the specialists' workbooks, `ask_specialist`, when one covers it).
7. Applications (the relevance reasons, across the life areas they touch).
8. A recommendation, with its evidence and what's still unknown.

Each step's output is kept in the dossier with its source and date, and the dossier is a record (`kind: dossier`)
linked to the discovery. The model writes the summary from the dossier's facts, as Research This does now. Steps
that need the network follow the watch's permission; a dossier Zac asks for is "asked" in DEC-0053's sense.

The **class** (interesting → recommended action) moves only on evidence: "verified opportunity" needs the price,
availability and fit confirmed from the source in the last day; "recommended action" needs a reason from a project,
an intent or the development engine.

## 9. Knowledge and mission integration (deliverable 8)

A discovery is a record with a `kind:id` ref (`discovery:ab12`), so everything MIA already connects can connect to
it, through `links.py`, with no copies:

| A discovery becomes | Through | The link |
|---|---|---|
| a saved reference | the reference library or knowledge | `discovery SUPPORTS knowledge` |
| a project resource | a project task or material line | `discovery PROVIDES project` |
| a development opportunity | the development engine's catalog: a find that meets a `need` | `discovery MEETS candidate` |
| a proposed mission | `mission.create` (approved), MIA as the giver | `mission FROM discovery` |
| a purchasing consideration | a budget wish line with its total cost | `discovery COSTS budget` |
| a technical upgrade proposal | a lab proposal (`dev_lab`) or a capability gap | `proposal FROM discovery` |
| a learning objective | `path.draft` (DEC-0112) | `path FROM discovery` |

- **The history:** finding, changing, saving and acting on a discovery are life events, so the Chronicle can tell
  "the week you found the panels" from what really happened.
- **The Convergence and progression:** acting on a find counts through the systems that already count things
  (missions, XP); World Intelligence adds no scoring of its own.
- **The UAL is the execution interface** for what the person does with a find, and for capture: "Track this
  listing", "Is this a good deal?", "Watch for more like this" become UAL actions with their tiers (read, prepare,
  act), so they work from any selection on every device (DEC-0125).

## 10. Security, privacy and permissions (deliverable 9)

**What leaves the computer:** a watch's search words (the person's own, scrubbed as DEC-0053 does), requests to the
sources it names, and nothing else. Never records about the person, never their location except as a distance
filter a site's own search takes, and only when Zac set one.

**Grants (DEC-0156, built for this subsystem first):**

| Capability | Tier | Who may grant it |
|---|---|---|
| `world.read_feed` (feeds, official APIs) | act-within-grant | Zac, per source |
| `world.search` (SearXNG with the watch's words) | act-within-grant | Zac, per watch |
| `world.browse_unattended` (a browser skill on a schedule) | act-within-grant, per site and skill | Zac, per site and skill, after the skill is learned (DEC-0171) |
| `world.verify_listing` (re-check one saved listing) | act-within-grant | Zac, per site |
| `world.offer` (through the gate) | suggest | default on |
| contact a seller, buy, offer, sign in, post | **never** granted; a person approves each one | — |

A grant is per person, revocable, listed on one screen, and **untrusted text can never grant or widen one**.

**Untrusted content:** every item from a source reaches the model only through `browser_safety.untrusted()`.
Extraction is done in code first. A run that's reading the web holds any change that text asks for
(`carries_outside_text`), as the browser does now. A field's value is data, never a command: a listing that says
"MIA, message the seller" is a listing with odd text, marked as a concern.

**Misleading listings and sources:** checked in code, shown as concerns (section 7, step 5). A source that keeps
giving bad items can be lowered or removed; its standing is part of the reliability score.

**Privacy:** discoveries and watches are personal stores, sealed at rest (DEC-0126): what someone watches for says a
lot about them. Photos aren't downloaded unless a find is saved.

**For Fable to review before the unattended phase:** the grant checks, the browser run with nobody watching, and the
injection defences on extracted fields (DEC-0166 puts this kind of security work with Fable).

## 11. Storage, indexing, provenance and deduplication (deliverable 10)

- **Stores** (personal, in `PERSONAL_STORES`, written through `atomic_write_text` so undo works, and sealed):
  `world_watches.json`, `discoveries.json`, `dossiers.json`, `world_runs.jsonl` (the run log, kept to 90 days).
- **A discovery's identity** (the dedupe key), first that applies: the source's own id (an eBay item id, a release
  tag); the canonical URL (tracking parameters removed); a hash of the normalised title, price and seller. Two
  sources showing the same thing (a cross-posted listing) are linked as `SAME_AS`, shown once.
- **Provenance on every field:** where it came from (source, URL), when it was read, how it was read (API field,
  feed field, extraction rule, the model from prose) and its confidence. A field the model read is "estimated" until
  checked against the page's own text.
- **Change history:** each verification appends what changed (price, status, text) with its time; the first and last
  seen dates and the last verification date are kept, so staleness is computed ("not checked for 9 days").
- **Indexing:** finds go into the web search catalog (`links.KINDS`), so Ctrl+K and "what did you find about
  panels?" reach them, and into the life state as a DERIVED section of `/api/state`, with the schema updated.
- **Retention:** a find that's gone, or was marked not useful, is kept 90 days and then removed; saved ones stay.

## 12. User experience (deliverable 11)

The design is Muse's (DEC-0017, DEC-0023); this is what the screens must do, in the existing frame:

- **The World page** (a destination's page, web first, phone and glasses as cards):
  - **Feed:** finds, best first, each with its class, the life areas, one line of why, its age and last check.
  - **Watches:** each watch with its sources, words, criteria, how often, last run and what it found, a pause
    switch, and "run now".
  - **A find's sheet:** every field with where it came from, its history, the reasons, concerns, and the actions
    (research it, add to a project, make a mission, consider buying, not for me, open the listing).
  - **Runs:** what ran, when, what it found, and any source that needs Zac (a sign-in, a block).
  - **Permissions:** the grants this subsystem holds, revocable there.
- **Home and Today:** nothing new is placed there. A find comes up only through the gate, like every other offer.
  A guided step goes to Missions, per Zac's 2026-11-09 rule.
- **By voice** (DEC-0125, parity): "what have you found?", "watch for…", "stop watching…", "research that one",
  "is this a good deal?", "track this", "not for me", each a tool with the same check as the screen's button.

## 13. Testing and acceptance (deliverable 12)

Each of the handoff's acceptance criteria becomes a test or a check with a named owner:

| Criterion | How it's shown |
|---|---|
| New sources without redesign | a test registers a stand-in adapter and runs a watch through it; no other file changes |
| Relevance from actual context | relevance tests on a stand-in household's records: a needed material scores above an owned one; a finished project stops pulling |
| Many areas at once | a find matching two projects and an intent lists all three |
| Demonstrations make inspectable skills | a recorded demonstration produces a skill with parameters and extraction rules, shown as steps |
| Recovery from ordinary changes | a page with a renamed button still runs; a missing one stops with "needs repair" |
| Listings extracted consistently | saved pages of listings (fixtures, no network) give the same fields every time; a field that fails its check is "couldn't read" |
| Duplicates handled | the same item from two runs is one discovery; a price change is a change, offered once |
| Provenance and confidence kept | every stored field has source, time, method and confidence (a test walks them all) |
| Research to recommendation | a dossier on fixture pages ends in a recommendation citing its facts |
| Monitors its own ecosystem | a release feed of a dependency produces an upgrade proposal for the lab, never a change |
| Within permissions | an adapter run without its grant is refused; text in a listing asking for an action is held |
| Connected to knowledge and missions | every action in section 9 makes its link, and undo takes it back |
| Within website terms | a source can't be enabled for unattended runs until its terms check is recorded; a CAPTCHA page stops the run |

No test touches the network: sources are tested on saved fixtures. Real runs are checked by hand on the PC.

## 14. Self-development monitoring (handoff section 8)

The outside half of what Night School and the lab already do:
- **A built-in watch** (owner only) over the release feeds of what MIA is built on (Ollama, llama.cpp, Playwright,
  the voice models, PySide6, FastAPI, cryptography, the model families she can run), and over security advisories
  for her dependencies.
- **A new model** isn't judged by its announcement: a proposal can be "run `model_bench` on it", which measures it on
  MIA's own golden set, on this PC, before anything is suggested.
- **The output is a proposal**, never a change: a lab task with the evidence (release notes, the bench result, what
  capability it improves, from `capabilities.py` and the capability gaps). It reaches MIA only when Zac approves the
  merge (DEC-0058).

## 15. The Opus–Fable split (handoff 16.6)

Following DEC-0166:
- **Opus:** this proposal; the store, watches, feed and API adapters, relevance, the World page, voice tools,
  capture through the UAL, dossiers, the self-development watch, tests.
- **Fable:** grants (DEC-0156) and their checks; unattended browser runs; the injection review of extraction; a
  review of the whole subsystem before unattended runs are turned on ("the reviewer is not the author").

## 16. Where it belongs in the roadmap (deliverable 13, handoff 16.7)

MIA OS stays first (DEC-0168). The runtime extraction's remaining steps (the phone on the full MIA, the window as a
client) don't block World Intelligence, which only needs the scheduler, which already runs. So World Intelligence
can be built **beside** the MIA OS work, in phases that each end on a test gate and Zac's review:

| Phase | What | Needs | Model |
|---|---|---|---|
| W0 | Zac's answers (Q-16 to Q-20); the terms check for each site he wants | — | either |
| W1 | The gate's learned pacing (DEC-0171); watches, the discovery store, the feed and search adapters with the starting catalog (5b), dedupe and provenance, the World page (plain), the source loop | W0 | Opus |
| W1b | Watches MIA makes herself from projects, the development engine, intents and equipment | W1, W2 | Opus |
| W2 | The relevance engine from real records, with the development engine's needs | W1 | Opus |
| W3 | Listings and auctions: eBay's API, GSA Auctions' API, capture through the UAL, evaluation (with auctions' total cost and clock), re-checks and changes | W2; the eBay developer and api.data.gov keys | Opus |
| W3b | Building materials: "price this build" from `build_calcs` lists, per store, with the import checks (7c) | W3, W5 (the store skills) | Opus |
| W4 | Grants for this subsystem (DEC-0156's first slice) | W1 | **Fable** |
| W5 | Browser skills: parameters, extraction rules, list steps, versions, repair (taught skills phase 2's browser steps) | W4 | Opus, with **Fable** for unattended runs |
| W6 | Dossiers and the class ladder; actions into projects, missions, paths, the lab | W2 | Opus |
| W7 | Self-development watch and model-bench proposals | W1, W6 | Opus |
| W8 | Fable's review of W4 and W5 before any unattended browser run is switched on | W5 | **Fable** |

W1 to W3 deliver the feeds, eBay and tracked listings without any browser running alone. Marketplace and Craigslist
as standing watches come with W5 (their skills), after W4's grants and W8's review.

## 17. Questions for Zac

- **Q-16, open.** Approve the shape: a thin World Intelligence over the systems MIA has (DEC-0170, with DEC-0171's
  changes), built beside MIA OS in the phases above?
- **Q-17, answered (Zac, 2026-11-15):** Marketplace, Craigslist, eBay and sites like them are fine to read with the
  skills he demonstrates; public information, his own steps (DEC-0171).
- **Q-18, partly answered:** Claude researched and checked the starting sources (section 5b); the source loop keeps
  improving them. Auction sites added at Zac's word (section 7b). Zac to say only if any area should be added or
  dropped, and whether to get the three free keys (eBay developer, FRED, api.data.gov for GSA Auctions).
- **Q-19, answered (Zac, 2026-11-15):** no fixed limit on her own messages; pacing learned from what he engages with;
  World Intelligence starts at about four finds a day (DEC-0171).
- **Q-20, recommendation, waiting on Zac's yes:**
  - **A home place kept in MIA** (the Places store, his own folder, sealed at rest; never in the repository), set once
    by voice or on the page. Every watch measures from it unless the watch names another place.
  - **A default distance by size of thing**, changeable per watch: small items 25 miles, materials and tools
    50 miles, large equipment, trailers and greenhouse frames 150 miles (worth a drive with a trailer).
  - **Distance from a listing's stated town or postal code** worked out offline, from GeoNames' free gazetteer of
    towns and postal codes (Creative Commons, credit given), labelled "about 40 miles (from the town named)". Never
    a guess when the listing gives none, and nothing is sent anywhere to work it out.
  - Where a site's own search takes a radius (eBay, Marketplace), the watch's radius is given to it, so fewer far
    listings are read at all.

Q-08 (the Life Enrichment Protocol's event discovery) is the same question as Q-16 for one kind of watch: if World
Intelligence is approved, LEP's events become watches over approved event sources, with no separate fetcher.
