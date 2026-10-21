# Homestead goods (DEC-0036)

Things you make in batches and sell (hot honey, salve, sourdough), on
the Workshop's own loop: **recipe → stock check → Bought It → Begin
Crafting → goods on hand → market day → the day's tally**. Built
2026-10-21. One-off builds (a bench) work the same as before.

## Using it

1. **Workshop → Recipes → Add Recipe.** Materials one per line, in
   whatever units you think in: `2 cups Raw honey`, `500 g Bread flour`,
   `3 Chili peppers`, `6 Glass jar 8oz`. Fill in **One batch makes**
   (6) and **Of what** (jars), **Sells for, each**, and **Keeps for**
   (days; 0 for honey that keeps). The card shows what a batch costs,
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
- **Hot honey:** plain honey has its own exemption, but honey with
  fresh garlic or peppers in it is a different product, and fresh
  garlic in honey is a known botulism risk. Ask the health department
  before selling it (dried peppers are the usual approach).
- **Herbal salve** isn't food: it's a cosmetic under the FDA's rules
  (its own labeling, and no health claims like "heals").

Sources: forrager.com/laws/kentucky, the National Agricultural Law
Center's Kentucky cottage food summary.

## What's next (not built yet)

- Saying it: "sold 3 jars of hot honey", "I baked 6 loaves" (the
  Assistant's tools, with the live check kept at 213/213).
- MIA's morning plan from what's low and what usually sells ("craft 12
  hot honey, bake 6 loaves").
- A harvest from the Grow Lab going straight into Materials.
- Quotes for custom orders by the piece from a batch recipe (an order
  for 3 dozen rolls).
- Densities for cups ↔ pounds, if the unit mismatch gets in the way.

Code: core/units.py, core/craft_recipes.py, core/goods.py,
core/goods_actions.py, core/business_book.py (market days, label
info), core/web_craft.py (goods_section), web/workshop.js, web/label.*.
