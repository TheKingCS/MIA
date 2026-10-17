# Expansion audit: the real-life RPG, homestead businesses, contextual AI

*Claude, 2026-10-17. ChatGPT sent Zac a handoff called "MIA Expansion
Audit". It asks to check MIA's code against nine areas before building
anything. Zac passed it on together with his approval of the Project
ALICE picks (DEC-0029). This audit maps each request to what exists,
classifies it, and proposes a phased plan that reuses existing code.
The phase order is a proposal (DEC-0030, waiting for Zac).*

**Status words:** ✅ **Built** (works today) · 🟡 **Partial** (the
pieces exist, but they aren't joined up or some are missing) ·
📐 **Designed** (written down, no code) · ⬜ **Missing** ·
⛔ **Blocked** (hardware, a platform or a policy limits it).

## 1. The big vision: a real-life OASIS

| Capability | Status | What exists |
|---|---|---|
| One connected life system (projects, skills, property, hobbies, money, health, memories, trips) | ✅ | ~40 stores behind one engine. Life State v2 (`core/context_assembler.py`), life events and links (`core/life_events.py`, `core/links.py`) |
| RPG layer over real life | ✅ | XP, levels, skills, missions, group quests, Character, Reward Shop, gear condition, boss battles, real stats, buffs, the Chronicle (`docs/GAME_LAYER.md`) |
| Never punishing | ✅ | DEC-0014. Buffs only, no lost points, a quiet week is "A Quiet Week" |
| Private and useful offline | ✅ | On-device model on the phone, desktop engine, no cloud by default |
| World map, questlines, crafting, party, sound, watch, location | ⬜ / 📐 | `docs/GAME_LAYER.md` ideas 6–13. Crafting is covered under §4 below |

## 2. ALICE-style contextual AI

| Capability | Status | What exists / what's missing |
|---|---|---|
| **Persistent memory** | 🟡 | `core/user_memory_manager.py` keeps memories. `core/assistant_chat.py` puts the **20 most recent** into every turn, whether they're relevant or not, and the person never sees which. Fix: ALICE pick 1, "What I Used" |
| **Context-aware conversation** | 🟡 | Life State, Today, `why_graph`, and a domain-scoped tool set per turn (`core/assistant_actions.py`). Missing: picking memories by relevance, and the current screen/item as context |
| **Proactive help** | ✅ engine, 🟡 content | The communication gate (`core/communication_gate.py`) rate-limits and merges notes, learns from what you ignore, and gives a reason for each. Missing: memory callbacks (ALICE pick 3) |
| **Situational help** (cooking, woodworking, repairs, equipment) | 🟡 | Recipe steps and the practice timer; asset pages with upkeep; textbook tutor; the glasses' quick menus. Missing: build steps for workshop recipes (§4), "what am I looking at" |
| **Visual context** | 🟡 / ⛔ | OCR for photos and receipts (`core/ocr.py`), Share to MIA from the phone (`Share.kt`), the inbox reading photos. No vision model is used yet. **Glasses:** see below |
| **Model routing** (PC for hard work, phone for fast and offline) | 📐 approved | DEC-0022 "supercharged online" is next in the queue. Backends are already swappable (`core/llm_manager.py`: Ollama, llama.cpp). Facts and actions stay deterministic in code, so a model upgrade rewrites nothing |
| **One conversation across devices** | 🟡 | Phone conversations show in the desktop History (built). Missing: one running thread that the glasses continue (ALICE pick 2) |
| **One personality** | 🟡 | There's a companion personality from the 2026-07 aesthetic pass and the gate's wording rules. No single guide yet (ALICE pick 7) |

**What the Meta Ray-Ban Display allows (researched 2026-10-17; the
official pages block this cloud computer, so confirm on hardware):**

- **The glasses' web apps** (how MIA's glasses view runs today) render
  HTML on the lens. They have **no camera and no microphone**: the
  browser's `getUserMedia` fails on hardware.
- **The Wearables Device Access Toolkit** is an Android/iOS SDK used by
  a phone app. It gives the glasses' camera (video stream and **photo
  capture**, about 1080×1440 JPEG in 1–2 s), the microphones and the
  speakers. Ray-Ban Display is listed as supported. It's still a
  developer preview, and **publishing to the public is closed**.
  Personal side-loaded use on Zac's own phone works.
- **So MIA's design:** no continuous camera. "Look" is an explicit
  capture: a glasses tap (or the phone camera, or Share to MIA) → a photo
  to the phone app → the engine (OCR now, a vision model on the PC
  later) → an answer on the lens. Each frame is used for that one
  question and kept only if the person saves it.

**Keeping the layers separate (as asked).** Engine and stores are
deterministic code. Model access goes through `LLMBackend`. A vision
model would be one more backend with a `describe(image)` method. Memory
retrieval would be a pure ranking function in core. Any of them can be
swapped without touching the others.

## 3. Personal memory vault and phone storage offloading

| Capability | Status | What exists |
|---|---|---|
| Uploads from the phone (photos, videos, files) | ✅ | Expedition media (`core/expedition_media.py`, up to 200 MB a file), My Files (`core/my_files.py`, kept inside the person's MIA folder), music uploads, Share to MIA |
| Attach media to life history | 🟡 | Expedition galleries, recipe photos, trip photos. No general "photo ↔ life event" link yet (`core/links.py` can hold it) |
| Automatic transfer to the PC, resume, no duplicates | ⬜ | Needs the phone↔PC link from DEC-0022 first. Design: content-hash (SHA-256) records, so resuming and re-sending are no-ops |
| **Verify before offering to delete from the phone** | ⬜ | Hash checked on the PC before the phone may offer removal. It's always an offer the person confirms, never automatic |
| Exact duplicates | ⬜ | SHA-256 (cheap; same pass as above) |
| Near-identical shots, bursts | ⬜ | Perceptual hash + capture-time window (pure Python on thumbnails) |
| Quality ranking (focus, light, composition) | ⬜ | Sharpness and exposure measures are cheap. Composition needs the vision model on the PC (later). **Never auto-deletes**; it only suggests "best of the group" |
| Organize by date, event, expedition, project, place | 🟡 | EXIF date and GPS need reading. Expeditions, projects and life events already exist to file into |
| Search, natural language | ⬜ | Metadata search first; captions from the vision model later |
| Previews on the phone, originals on demand | ⬜ | Thumbnails are generated on the PC and the original is fetched when opened |
| Large videos, storage-heavy content | ⬜ | The size report is easy once the archive exists |
| Second backup destination | 📐 | `core/backup_manager.py` exists for data. The vault would add a mirror target |

**Blocked by:** the phone↔PC connection (DEC-0022 / Tailscale) and the PC
being set up as MIA's server. Android background upload needs a
foreground service and the person's permission for each folder.

## 4. Crafting recipes and workshop inventory

| Step | Status | What exists |
|---|---|---|
| Materials inventory (on hand, unit cost, reorder level) | ✅ | `core/material_manager.py`, Workshop web screen, `material.*` actions |
| Jobs consume materials, produce products, labor hours | ✅ | `core/job_manager.py` (`consume_material`, `produce_product`, cost functions, `workshop.labor_rate_per_hour`) |
| Products, listings, sales, profit | ✅ | `core/product_manager.py` (listings per platform), `core/ledger_manager.py` (`record_sale` takes stock out, `net_profit`) |
| Receipt line items | ✅ | Inbox reads receipts into line items (`inbox_classify.receipt_items`), stored on Budget expenses |
| **Recipe** (reusable BOM, dimensions, cut list, tools, hardware, steps, time, cost) | ✅ 2026-10-17 | `core/craft_recipes.py` (household store), Workshop → Recipes |
| Check inventory → shopping list for what's missing | ✅ 2026-10-17 | `check()`: have / need / short per line, the shopping list with estimated cost, Copy List |
| Receive purchases into inventory after confirming | ✅ 2026-10-17 | **Bought It** (`craft.receive`): quantities and what you paid, average cost, one workshop expense, undoable. From a scanned receipt: later |
| Track a build: consumption, progress, labor, expenses, finished goods | ✅ 2026-10-17 | `craft.start` / `craft.step` / `craft.finish` / `craft.cost`: a Job with the recipe, steps ticked, materials used at their cost then, hours, product made |
| Refine the recipe from actual costs | 🟡 2026-10-17 | The recipe shows how it's gone (built, sold, average cost and profit, per hour) beside its estimate; editing stays the person's |
| Portfolio entry, before/after photos | 🟡 2026-10-17 | Before / progress / after photos on every build (`core/build_media.py`). A portfolio page: phase C |
| Profitability per build | ✅ 2026-10-17 | `build_result()`: sold − materials used − costs tagged to the build, per hour, after paying yourself when a labor rate is set |

## 5. Greenhouse, aquaponics and food production

| Capability | Status | What exists |
|---|---|---|
| Equipment (pumps, tanks, plumbing) with upkeep and condition | ✅ | Maintenance assets (Garden/Plant), Greenhouse screens, condition bars |
| Measurements (pH, ammonia, temperature) | 🟡 | `core/data_logger_manager.py` (any series, manual entry, the Lab). No greenhouse screen or safe ranges yet |
| Sensors | ⛔ | No hardware yet. A sensor is just another `add_reading()` caller |
| Seeds, feed, media, packaging inventory | 🟡 | Materials fits (any unit). Household Inventory too. No "grow supplies" view |
| Planting, transplanting, harvest schedules | 🟡 | Recurring missions and maintenance tasks can schedule. There are no crop records |
| Batches, harvests, yields, losses | ⬜ | New: a batch record (planted → harvested, yield, loss) |
| Experiments (varieties, conditions, yields) | ⬜ | New: an experiment groups batches + readings + a conclusion. The Lab is the home for it |
| Costs, revenue | 🟡 | Budget entities + ledger + homestead costs (`core/homestead_costs.py`) |
| Troubleshooting from readings | ⬜ | Range checks in code with the person's own limits. It warns and never controls equipment (human oversight for animals, water and controls) |

## 6. Roadside stand and connected businesses

| Capability | Status | What exists |
|---|---|---|
| Separate businesses, shared costs | ✅ | Budget `BusinessEntity` (LLCs, sole props), expense/income per entity, auto-tagging, Business Report (per entity and consolidated), business-use share of equipment |
| Product catalog and stock | ✅ | Products + listings (platforms) |
| Production batches, finished goods | 🟡 | Jobs make products. Food batches don't exist (§5) |
| Purchasing | 🟡 | Expenses, receipts, line items. No purchase order |
| Customer orders, sales | 🟡 | Sales (`sale.add`, `product.sell`). No customers or orders |
| Quotes and estimates for custom builds | ⬜ | Would come from a recipe's cost + labor + margin (§4) |
| Customer history (private) | ⬜ | People & Pets is personal. Customers would be a business store in the household, never shown to children |
| Portfolio, case studies | ⬜ | Same as §4 |
| Legal/safety limits (cottage food, licensing) | ⛔ policy | MIA can hold the person's own notes on their rules. It doesn't give legal advice |

## 7. The business flywheel

🟡 The pieces exist separately: build costs (homestead costs), jobs and
sales (workshop), per-entity reports. What's missing is the one loop
**recipe → build → actual cost → sale → profit → refine recipe →
portfolio → quote**. Phase B below builds its core. "Profitable or
not" stays the measure. XP never stands in for profit (a recipe that
loses money says so plainly, without guilt).

## 8. Shared household progression

| Capability | Status | What exists |
|---|---|---|
| Shared stores within a household | ✅ | `HOUSEHOLD_STORES` (materials, products, jobs, ledger, maintenance, budget...) |
| Group quests, individual contributions | ✅ | Missions' group quests: individual vs. group progress, group rewards for each participant |
| Individual skills | ✅ | Each person's own skills and XP |
| Approved actions credited to who did them | ✅ | `crediting` (DEC-0013) |
| Joint business milestones | 🟡 | Missions can be shared. No business milestones yet |
| Celebrate without competing | ✅ | Leaderboards are not built. GAME_LAYER idea 10 says opt-in only |

## 9. Proposed phases (DEC-0030, for Zac)

**A. Contextual AI (approved, DEC-0029), now:** ALICE pick 1 "What I
Used" (memories ranked by relevance and shown) → pick 3 memory callbacks
→ pick 2 one conversation → pick 7 personality guide. Then DEC-0022
(the PC's model from the phone), already approved.

**B. Crafting, the smallest real end-to-end workflow, now:** a workshop
**recipe** (materials with quantities, cut list, tools, hardware, steps,
time, price) → **check inventory** → **shopping list** of what's
missing → **receive** purchases into materials (from the list, after
confirming) → **start a build** (a job from the recipe) → finish it
(materials used, product made) → **photos** → **actual profit**, with
the recipe showing actual vs. estimated cost. All on the existing
Materials/Jobs/Products/Ledger stores and the action contract.

**C. Business loop:** quotes from a recipe (cost + labor + margin),
customers and orders (household store, private), a portfolio page
from builds with photos.

**D. Grow lab:** crop batches (planted → harvest, yield, loss, cost),
greenhouse readings on the data logger with the person's own safe
ranges (warn only), experiments that compare batches.

**E. Memory vault:** after DEC-0022's phone↔PC link. Content-hash
transfer with resume, verify-then-offer-removal, duplicate and burst
grouping, sharpness/exposure "best shot" suggestions (never auto-delete),
EXIF date/place, linking to life events, the Chronicle and expeditions.
Then a vision model on the PC for captions and "what am I looking at".

**F. Glasses camera:** a side-loaded Device Access Toolkit build of the
phone app for "look" photos (explicit capture only). This waits on the
Display arriving (~Nov 16) and on Meta's publishing rules.

**Smallest real-world test (Phase B):** make a recipe for a piece of
furniture, see what's short, take the shopping list to the store,
receive what you bought, build it, add before/after photos, sell it,
and read the profit.

**Tests required throughout:** inventory accounting (receiving and
consuming add up, undo restores them), no duplicate records on retry,
destructive steps (delete, remove-from-phone) always confirmed and
undoable where possible.
