# Smart Closet (DEC-0162)

*Claude, 2026-11-15, from Zac: "an inventory of my clothes ... suggest
outfits, let me rate them, maybe let me see what they would look like
together ... think of what an ai integrated smart closet would be useful
for and implement that".*

## What it's for

- **Getting dressed without thinking about it.** Each morning: what to wear, for today's weather and plans.
- **Wearing what you own,** not the same five things. It notices what has rested longest and what never gets worn.
- **Learning what works.** Ratings make good outfits come back and bad ones disappear.
- **Knowing what's clean, what needs a repair, and what's missing** (no rain jacket, no gym shoes).

## Stage 1: built 2026-11-15

**Pieces:**
- name, kind (top, bottom, dress, layer, outerwear, shoes, accessory) and colour;
- warmth (light, medium, warm);
- the occasions it suits (everyday, work, gym, date, dressy, outdoors, lounge);
- waterproof, condition, clean or in the wash;
- a photo from the phone's camera;
- notes, and when it was last worn.

**Outfits** are pieces saved together, with 1–5 star ratings and notes.

**Today's picks.** Worked out in code (`core/smart_closet.suggest`), never
by the model:
- **Weather:** hot days get light pieces; cold days get warm ones plus a layer; cool or wet days get outerwear, and wet ones a waterproof one.
- **The day's occasion:** gym, date, dressy or outdoors from calendar words; work on a Loop work day.
- **Rest:** nothing worn yesterday; pieces rested a week score higher.
- **Ratings:** an outfit rated 2 stars or under is never suggested, and loved ones come first.
- **Colour sense:** neutrals go with anything; two different bold colours count against an outfit.
- **Every pick says why.**

**Seeing pieces together.** Each pick and each outfit shows its pieces'
photos side by side (a colour swatch when a piece has no photo yet).

**Insights:**
- not worn in six months: let it go?
- the most worn;
- the best rated;
- in the wash or needing a repair;
- gaps.

**Everywhere:**
- the web page (Home › Personal Tools › Smart Closet);
- voice tools: what to wear, closet report, add clothing, save, wore, rate, laundry;
- a glasses card, "Today's Outfit";
- every change is an action with undo;
- the closet is personal and sealed at rest.

## Later stages (not built)

1. **Morning card through the communication gate.** "Rain today: the rain shell with jeans and boots", only on days it helps.
2. **Laundry flow.** "Wore it" puts pieces in the wash after N wears; laundry day reminds you what's running low.
3. **Outfit previews beyond side-by-side.** A cut-out collage of the photos first; a generated try-on image only on the PC's own model, never a cloud service, because the photos are of the person.
4. **Packing lists** from a trip (`core/trip_manager.py`) or a Life Enrichment Protocol plan: days × weather × activities.
5. **Care and repair.** Washing instructions from a label photo (OCR); repair to-dos.
6. **Buying and letting go.** Gaps become a shopping-list item (never a purchase without approval). "Let it go" pieces become a donate or sell list (Businesses › orders if sold).
7. **The partner's closet** in their own account, and "what should we both wear" for a planned outing (DEC-0163, multi-user rules).
8. **A learning loop** (`work/loop_coverage.json` `store:closet`, todo): count suggestions worn against skipped, to tune the weights.

## Rules kept

- **Facts in code.** The model only phrases (DEC-0004).
- **Nothing is bought, sold or donated without approval.**
- **Photos stay on the person's devices.**
