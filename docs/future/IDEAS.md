# MIA: future features (the ideas list)

*Started 2026-10-18 at Zac's request: "a document for potential future
features… automating things that will make my life easier and save me
money." Add to it any time: tell Claude, or edit it on GitHub. Nothing
here is approved or scheduled until Zac picks it (DECISIONS.md); when
one is picked, it gets a DEC number and moves to the build queue in
`docs/NEXT_SESSION.md`.*

**How each idea is written:** what it does for you, what MIA already has
that it builds on, what it needs from outside, and its status
(💡 idea · 🔍 being planned · 🛠 being built · ✅ built).

---

## Money

### 1. Insurance check-up: compare and save ✅

*Built 2026-10-19 (DEC-0034): Apps → Insurance.*

*Zac, 2026-10-18.* MIA keeps track of your insurance (car, home or
renters, health, life, umbrella) and helps you find a better plan.

**What it would do**
- **Policy vault:** each policy as a record: insurer, what's covered,
  limits, deductibles, the premium and how often it's paid, and the
  renewal date. Filled from the policy PDF or the declarations page
  (the Inbox and OCR already read documents) for you to check.
- **Renewal heads-up:** about 45 days before a renewal, a note through
  the communication gate: "Your car insurance renews in 6 weeks; last
  year it went up 12%. Want to shop it?"
- **What you're paying for:** the total per year, the change since last
  year, and things worth a look: coverage that may not fit any more
  (full coverage on an old car), a deductible you could raise because
  your emergency fund can cover it, or a missing bundle discount.
- **Shopping it:** a checklist of what an agent needs, and quote-request
  emails MIA **drafts** for you to send (MIA never sends; you press Send).
  It never fills in an insurer's website for you.
- **Side by side:** type in or forward the quotes you get back, and MIA
  lines them up against your current policy, same limits against same
  limits, so a cheaper quote that covers less is called out, not hidden.
- **Switching:** once you pick, the steps (start the new one before
  cancelling the old one, no gap), a mission for it, and the savings
  logged so the Chronicle and your money boss count them.

**Builds on:** the Inbox and OCR (reading policies), email drafts, the
communication gate, the Budget (premiums as bills), missions, the
Chronicle.
**Needs from outside:** your quotes. There's no honest, free,
offline-friendly way to pull live prices from every insurer, so MIA
compares what you get rather than shopping for you.
**Guardrails:** never money to a child account; the policies stay on
your devices; MIA explains the trade-offs and you decide; never advice
presented as a licensed agent's.

---

## Homestead business

*Claude's list, 2026-10-21, after homestead goods (DEC-0036); Zac picked
the first four to build the same day ("start working on chickens,
microgreens and plant starts, small wood goods, and seasonings and
spices / dry goods in jars"). Everything stays within Kentucky's rules
for what a household may sell; check each with the health department.*

### 2. Eggs from your own hens ✅

*Built 2026-10-21 (DEC-0037): see `docs/HOMESTEAD_GOODS.md`.*

*Claude, 2026-10-21; Zac picked it (DEC-0037).* A flock log that turns
eggs into money you can see: what the hens lay, what their feed costs
per dozen, cartons into stock for the stand, eggs into the bakery.

**What it would do:** each flock (hens, breed, started); eggs collected
each day; feed bought; birds added or lost; the lay rate, eggs a week,
feed cost per dozen; **Carton** puts dozens into goods on hand (with
their date and sell-by) and **For baking** puts eggs into Materials at
what they cost you, so the banana bread's cost is real.
**Builds on:** homestead goods (batches, market day, labels), Materials,
the game layer (an animal-care skill).
**Needs from outside:** nothing.
**Guardrails:** Kentucky has its own rules for selling eggs (storage
temperature, cartons, labels): MIA holds your notes, never legal advice.

### 3. Microgreens, seedlings and plant starts ✅

*Built 2026-10-21 (DEC-0037): see `docs/HOMESTEAD_GOODS.md`.*

*Claude, 2026-10-21; Zac picked it (DEC-0037).* The greenhouse grows
something to sell every week: microgreens all year, tomato and pepper
starts in spring.

**What it would do:** a Grow Lab batch's harvest (or the starts that are
ready) goes straight into goods on hand, at what the batch cost per
unit, or into Materials when it's an ingredient (herbs for a spice
blend). Then the market day sells it like anything else.
**Builds on:** the Grow Lab (batches, harvests, yield, losses),
homestead goods.
**Needs from outside:** nothing.
**Guardrails:** raw produce and plants aren't cottage food; check
whether anything you sell needs a nursery or produce permit.

### 4. Small wood goods for the stand ✅

*Built 2026-10-21 (DEC-0037): see `docs/HOMESTEAD_GOODS.md`.*

*Claude, 2026-10-21; Zac picked it (DEC-0037).* Cutting and bread
boards, trays, planters, birdhouses, signs: sell beside the bread.

**What it would do:** workshop recipes in batches (a run of 10 boards),
cost and profit each, the market day. Starter recipes to copy and
change.
**Builds on:** the Workshop, homestead goods. Nothing new needed.
**Needs from outside:** nothing (a laser engraver later, for names).
**Guardrails:** food-contact finishes are the maker's call; MIA keeps
your notes on them.

### 5. Seasonings, spices and dry goods in jars ✅

*Built 2026-10-21 (DEC-0037): see `docs/HOMESTEAD_GOODS.md`.*

*Claude, 2026-10-21; Zac picked it (DEC-0037).* Dried herbs, spice
and tea blends, baking mixes in a jar, candy (fudge, brittle, kettle
corn): on Kentucky's allowed list, shelf-stable, cheap to make.

**What it would do:** recipes in grams so labels order the ingredients
by themselves; dried herbs from the Grow Lab into Materials; starter
recipes to copy.
**Builds on:** homestead goods, the Grow Lab.
**Needs from outside:** nothing.
**Guardrails:** labels print the person's own words.

### 6. Beekeeping beyond honey 💡

*Claude, 2026-10-21.* Beeswax candles (not food), comb honey; a hive
log: inspections, treatments and harvests per hive.
**Builds on:** Maintenance's assets and schedules, homestead goods.

### 7. Jams and jellies 💡

*Claude, 2026-10-21.* Allowed in Kentucky with standard recipes
(low-sugar ones may not be); a canning batch log with the lot on each
jar. **Builds on:** homestead goods.

### 8. Subscriptions: weekly bread, eggs or a veggie box 💡

*Claude, 2026-10-21.* Steady money you know in advance: repeating
orders, and "what to bake for subscribers this week".
**Builds on:** Orders & Quotes, homestead goods.

### 9. Classes and experiences 💡

*Claude, 2026-10-21.* Sourdough or woodworking classes, farm tours: a
booking calendar and a sign-up list per class.
**Builds on:** the Calendar, customers.

### 10. Seasonal goods 💡

*Claude, 2026-10-21.* Pumpkins and fall decor, Christmas wreaths,
firewood bundles: a seasonal plan saying when to start each.
**Builds on:** seasonal questlines, the Calendar, homestead goods.

### 11. Later, bigger 💡

*Claude, 2026-10-21.* A farm stay or campsite (Real Estate's rentals),
compost and worm castings by the bag, dog treats (Kentucky registers
these separately).

---

## Add the next idea here

Copy this shape:

### N. Name 💡

*Who, date.* One or two sentences: what it does for you.

**What it would do:** the main pieces.
**Builds on:** what MIA already has.
**Needs from outside:** accounts, devices, data.
**Guardrails:** privacy, children, never acting without you.
