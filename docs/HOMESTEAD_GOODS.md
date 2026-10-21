# Homestead goods (DEC-0036)

Things you make in batches and sell (banana bread, cookies, bread,
honey), on
the Workshop's own loop: **recipe → stock check → Bought It → Begin
Crafting → goods on hand → market day → the day's tally**. Built
2026-10-21. One-off builds (a bench) work the same as before.

## Using it

1. **Workshop → Recipes → Add Recipe.** Materials one per line, in
   whatever units you think in: `2 cups Raw honey`, `500 g Bread flour`,
   `3 Chili peppers`, `6 Glass jar 8oz`. Fill in **One batch makes**
   (2) and **Of what** (loaves), **Sells for, each**, and **Keeps for**
   (days; 0 for honey, which keeps). The card shows what a batch costs,
   what each one costs, and from what to what each material goes.
2. **Materials** can be kept in any unit. A recipe line converts to it
   when both measure the same thing: weight to weight (g, oz, lb),
   volume to volume (tsp, tbsp, cup, fl oz, pint, quart, gallon, ml),
   counts to counts (a dozen is 12). Cups against pounds can't be
   compared (that needs a density): the line says so, and you change
   one of the two units.
3. **Begin Crafting** (how many batches) → tick the steps → **Finish**:
   the materials come out of stock and the goods go in, with today as
   their made date and a sell-by from the shelf life.
4. **Workshop → Goods**: everything on hand, batch by batch: Fresh,
   **Sell First** (the last quarter of its shelf life) or **Past
   Sell-By**. Sales come out of the oldest batch first. **Toss** takes
   some out as a loss on that batch.
5. **Market day**: **Open Market Day** (where, and how many of each
   you're taking; after a few days MIA suggests how many from what
   usually sells), tap **+1 Sold** for each sale (the tap is the
   approval; Undo is in the message), **Close The Day**: what sold,
   what's left (toss the leftovers that won't keep), what you took in,
   what it cost to make and the profit, with XP for the day.
6. **Labels**: Goods → **Label Info** once (business name, address,
   and the statement your rules require, in their exact words), then
   **Labels** on a batch prints one per item with that batch's made
   date. A recipe's **Label: ingredients** sets the list when the
   recipe's lines aren't all weights (MIA can only order by weight or
   volume), and leaves out packaging.

## Chickens, the greenhouse, wood goods, dry goods (DEC-0037)

- **Chickens** (Apps → Chickens): add your flock (hens, breed, when they
  came). Log eggs with one tap (+1 … +12); the screen shows eggs today
  and this week, the lay rate, loose eggs and two weeks as bars. **Bought
  Feed** (pounds and cost; also a cost in the business's books) gives the
  feed cost per dozen over the last 30 days. Loose eggs go **Into
  Cartons** (dozens into goods on hand at the feed cost; first add an
  "Eggs" recipe from the starters and pick it on the flock), **For
  Baking** (into Materials as Eggs at the feed cost each, so the banana
  bread's cost includes them) or **Eaten At Home**. **Hens Came Or
  Went** keeps the count. Any log line can be taken back.
- **The greenhouse**: Grow Lab → a batch → **Harvest** → "Also into
  stock?": **goods** (microgreens, starts that are ready: how many
  clamshells or pots) or **materials** (dried herbs for a blend). The
  first time, it carries the batch's cost (seed, trays); later cuts
  don't pay for the seed again.
- **Into stock by hand**: anything else that isn't crafted (a flat of
  starts you potted up) goes in with its date and what one cost.
- **Starter recipes** (Workshop → Recipes → **From A Starter**): cutting
  board, bread board, cedar planter, birdhouse, wooden sign, taco
  seasoning, Italian herb blend, chamomile mint tea, cookie and brownie
  mix in a jar, kettle corn, banana bread, chocolate chip cookies, eggs,
  microgreens, tomato starts. Each is a starting point with no price:
  set yours and change it to how you make it.

## Kentucky notes (Zac, 2026-10-21; not legal advice)

What we found when building this, to check with the health department
(Kentucky's home-based processor rules, 902 KAR 45:090):

- A home-based processor registers with the health department; sells
  directly to consumers in Kentucky (home, farmers markets, roadside
  stands, events; not stores, restaurants or shipping), with a yearly
  sales limit.
- Allowed: shelf-stable foods: breads and baked goods that don't need
  refrigeration, jams and jellies, honey, dried herbs and mixes, candy.
  Not allowed under the home-based processor rules: things that need
  refrigeration, acidified foods, sauces, oils, and more.
- The label needs: the product name, the business's name and address,
  the net amount, the date it was made, the ingredients heaviest first,
  allergens, and the statement "This product is home-produced and
  processed" (in at least 10-point type; MIA prints it that size).
- **Zac's line (2026-10-21): only what those rules allow**: banana
  bread and other quick breads, cookies, breads, honey and the like.
  No infused honey, salves or anything needing refrigeration. Watch
  the toppings: cream cheese frosting or cream fillings make a baked
  good perishable, which the rules don't allow.
- Tip: write baking recipes in grams (or all in cups). When every
  line is a weight, the label lists the ingredients heaviest first by
  itself; mixed units need the recipe's "Label: ingredients" line.

Sources: forrager.com/laws/kentucky, the National Agricultural Law
Center's Kentucky cottage food summary.

## What's next (not built yet)

- ~~Saying it~~ **built 2026-10-21** (`core/assistant_goods_actions.py`): "How many eggs
  this week?", "I collected 9 eggs", "What goods do I have on hand?", "Sold 3 loaves
  of banana bread", "What's due for taxes?", "How close am I to freedom?". Still to
  add: "I baked 2 banana breads" (a batch by voice).
- MIA's morning plan from what's low and what usually sells ("craft 12
  cookies, bake 2 banana breads").
- A harvest from the Grow Lab going straight into Materials.
- Quotes for custom orders by the piece from a batch recipe (an order
  for 3 dozen rolls).
- Densities for cups ↔ pounds, if the unit mismatch gets in the way.

Code: core/units.py, core/craft_recipes.py, core/goods.py,
core/goods_actions.py, core/business_book.py (market days, label
info), core/web_craft.py (goods_section), web/workshop.js, web/label.*.
