# Woodworking Studio — audit, structure and the smallest useful first version

*claude (engine), 2026-11-08, from ChatGPT's "MIA Development Handoff: Woodworking Studio", pasted by Zac. Its own
sections 7 and 8 ask for an architecture audit, a module structure, a data model, an interface spec, an MVP plan,
risks and a testing strategy before anything is built, and not all five phases at once. This is that. A proposal
only (DEC-0147, proposed): nothing here is built, and only Zac approves it.*

## Headline

**About two thirds of the Studio already exists, spread across the Workshop, the plans shelf and the business
tools.** What's missing is the thing that ties them into one place to design a build: a *design* made of real parts
with real (not nominal) dimensions, from which the cut list, the bill of materials, the stock check, the cost, the
drawings and the steps all come, so they can never disagree. Build that one core piece, reuse everything else, and
the Studio is a screen over it.

Zac's addition makes it bigger and simpler at once: **the same shape serves woodworking, the kitchen and bakery,
garden produce and the flock.** A recipe or design → what it takes → what's on hand → make it (a build or a batch) →
what it made → use it or sell it. MIA already runs most of that loop for the workshop and for homestead goods.

## 1. Audit: what exists and is reused

| The handoff asks for | Already in MIA | Verdict |
|---|---|---|
| Projects you design and keep | `core/craft_recipes.py` (workshop recipes: materials one per line, cut list, tools, steps, hours, price, its product) | **Reuse: the design record** |
| Material lists, cut lists, waste | `core/build_calcs.py` (15 calculators, plus `custom_cuts()` for your own parts, `buy_boards()` first-fit packing with ⅛" kerf choosing the least-waste stock length, `sheets_for()` 4×8 sheets, ~10% miscut allowance, a codes-and-span-tables note on every list) | **Reuse** |
| Built-in plans, any size | `core/plan_library.py` (15 built-in plans sized to you, kept plans, plan PDFs read with OCR) | **Reuse: the inspiration/plans shelf** |
| Inventory, shopping list, purchases | `core/material_manager.py` (on hand, unit cost, reorder), `craft_recipes.check()` (needed vs on hand vs short, its cost), receiving at the price paid, receipts that stock materials (DEC-0120) | **Reuse** |
| Builds, progress, tasks, budget | `core/project_manager.py` (budget, status, tasks, skills it trains), `core/job_manager.py` (a production run of a recipe) | **Reuse** |
| Costs, pricing, margins, sold products | `core/business_book.suggested_price()` (materials + hours × rate + extras + margin), `core/product_manager.py`, `core/ledger_manager.py`, `core/goods.py` (goods on hand, batch by batch) | **Reuse** |
| "What's this and how is it built?" from a photo | `core/sight.py` (a local vision model on the PC, Qwen2.5-VL; nothing leaves it) | **Reuse, labelled as a guess** |
| Pictures of a design | `core/art_studio.py` (painting on the PC's own GPU, once its engine is set up) | **Later** |
| What to build next with what you have | `core/development_engine.py` (DEC-0144: paths, made before bought), `capability_reminders` ("you have everything for X") | **Reuse** |
| Screens | `web/workshop.html`, `web/projects.html` (the design session's) | **Extend** |

**Genuinely missing (the real work):**

1. **Actual lumber sizes.** `build_calcs` knows 2× widths (a 2×6 is 5½") but not thicknesses (1½"), 1× stock (¾"),
   4×4s (3½") or plywood's real thickness (23/32" for "¾"). The handoff is right that a design must be drawn and cut in
   real dimensions; today it isn't, everywhere.
2. **A design made of parts.** A recipe's materials are free text. A Studio design needs named parts with a length,
   width, thickness, material and count, so one source of truth feeds the cut list, the drawings and the costs.
3. **Drawings.** Nothing draws a design. Front, side and top views of a box-shaped part list are plain geometry and
   can be drawn as SVG in code; exploded views and 3D are later.
4. **A printable plan.** "PDF" in MIA today means *reading* plan PDFs. A printable page (the browser's own print to
   PDF) gives Zac a plan to carry to the bench without a PDF library.
5. **A structural check.** Anything that bears load (a deck, a loft, a shed roof, a shelf for heavy things) needs the
   "verified calculation / estimate / assumption" labels the handoff asks for, and a professional flag. `build_calcs`
   already says "rules of thumb, never engineering"; a design needs it per part.

## 2. Structure (no new subsystem)

- `core/lumber.py` (new, small): nominal → actual for dimensional lumber, 1× boards, posts and sheet goods; used by
  `build_calcs` and every design.
- `core/craft_recipes.py` (extended): a recipe gains `parts` (the design). Its `materials` lines are *derived* from the
  parts when there are any, so nothing can disagree; free-text recipes keep working as they are.
- `core/design.py` (new, pure logic): parts → cut list (through `buy_boards`/`sheets_for` in actual sizes), bill of
  materials (lumber, sheets, fasteners, glue, finish), cost (material prices on hand, else estimates, labelled), the
  three views as SVG, and a structural flag.
- The rest stays where it is: projects, jobs, products, the business book, goods, the development engine.
- Screens: the design session's Studio page over `core/design.py` (Who builds what); voice tools by the parity
  session ("make this 48 inches wide", "what tools do I need", "optimize the cut list").

## 3. Data model

A **part**: `name`, `count`, `length_in`, `width_in`, `thickness_in` (actual), `material` (e.g. "2x6 pressure-treated",
"3/4 plywood"), `grain` (along the length or either, for sheet layout), `note`. A **design** is a recipe with parts,
`dimensions` (overall W × D × H), `joinery` (butt and screws, pocket screws, dados…), `outdoor` (weather-resistant
material and finish), `load` (none, light, heavy, structural), and its `steps`. Everything else (cut list, bill of
materials, cost, views) is computed, never stored, the same "derive it, don't keep a second copy" rule the rest of
MIA keeps.

## 4. Interface (for the design session)

One **Studio** page with the handoff's sections, each a view of the same design: Inspiration (the plans shelf and
saved pictures), Designer (parts and overall size, edited in a form, or said to MIA), Drawings (the SVG views),
Materials & Cuts (cut list, bill of materials, what's on hand and short, the shopping list), Instructions (tools,
steps, finish, a printable plan), and the project's dashboard (stage, costs estimated and actual, photos). Same look
as the rest (DEC-0023, the canvas standards).

## 5. The smallest useful first version

1. `core/lumber.py`: actual sizes, used by `build_calcs` (fixes every existing calculator too).
2. Parts on a recipe and `core/design.py`: cut list, bill of materials, stock check and cost from parts, in actual sizes;
   the overall dimensions checked against the parts.
3. The three orthographic views as SVG.
4. The structural flag and the three labels on every number (verified by the code / estimate / assumption).
5. The design session's Studio page and a printable plan; the parity session's voice tools.

First design to prove it: Zac's own next build (a seed-starting shelf is already on his homestead path, DEC-0144).
Phases 3 to 5 of the handoff (instructions with progress, deeper homestead links, 3D, CNC, laser, AR) come after.

## 6. Risks

- **Structure.** A shelf that holds seedling trays is not a loft. Anything load-bearing gets the professional flag and
  never a "construction-ready" claim (the handoff's own rule, and DEC-0144's).
- **Real sizes.** Mixing nominal and actual sizes is the classic error; one table, used everywhere, and tests on it.
- **Two cut-list paths.** The calculators and designs must use the same packing (`buy_boards`), or the shelf and the
  Studio will disagree.
- **Images.** A photo-to-design is a *proposal* from the vision model, labelled as a guess, never measured.
- **Lanes.** Three sessions build in parallel; the Studio page is the design session's, the voice tools the parity
  session's. Claim first.

## 7. Testing

The calculators' existing tests keep passing with actual sizes; a design's cut list is the same whether it comes
from parts or the matching calculator (a raised bed, both ways); the overall dimensions always match the parts; a
load-bearing design always carries the flag; the SVG views have the parts' real proportions; the shared pattern is
held by a test that a kitchen recipe, a workshop design and a garden batch all answer "what it takes / what's on
hand / what it made" the same way.

## Decisions for Zac

1. Approve the first version above (the five steps), built in that order?
2. Should the Studio be one page for woodworking only, or the shared **Make** space for the workshop, the kitchen and
   bakery, the garden and the flock (your note), with woodworking first?
3. Drawings: plain 2D views first (recommended: exact, cheap), or wait for 3D?
4. Printable plan as a print-ready page (recommended, no new library) or a generated PDF file?
