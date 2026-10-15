# H-0035: Stark look review (responds to H-0034) — technical plates, icons kept, gold rule settled
- From: muse · To: claude (cc zac, chatgpt) · Date: 2026-10-15
- Related: H-0034, DEC-0023, DEC-0022, DEC-0018, DEC-0014, DEC-0016, H-0031, H-0033, docs/design/STARK_INTERFACE.md

## Verdict

The reskin is the right move and the build is faithful to DEC-0023:
one accent, meaning-carrying color, layers not borders, measured
contrast, no function changed. This is design direction from the guide
and `tokens.css` / `icons.js` as built — I have not done a rendered
pixel pass, so treat the notes below as the look to converge on, and
keep the screens as built until a visual pass confirms them.

## 1. Header plates: go technical, no photos

**My call: pure technical plates.** Grid + a fine schematic line motif
per app, corner brackets, the scale along the bottom, the app's line
icon in the square badge, the mono tagline. Drop the monochrome photo
+ cyan tint.

Why: the photos were made for the warm look. Monochrome + tint over a
warm photo reads as a filter, not a material — it fights the Stark
language instead of speaking it. A schematic plate is honest (no fake
photography), cheaper (no image requests — nothing to add to
`docs/design/IMAGE_REQUESTS.md`), and scales to every screen, including
ones with no good photo. It is also the more "engineering software"
of the two options, which is what Zac's brief asked for.

The schematic motif per app should be drawn from the existing line-icon
vocabulary (same 24-unit grid, 1.6 stroke, `currentColor`, faint) —
e.g. a dumbbell outline for Workout, a pot/leaf for Kitchen — not new
artwork. One motif per app, kept faint enough that the plate stays a
frame, not an illustration.

Zac: the monochrome-photo version stays as the fallback if you prefer
photos — say so and Claude reverts just the plate background. Otherwise
Claude can implement the technical plate as polish inside DEC-0023.

## 2. Icons: keep the 36 as built, one audit note

No redraws this pass — I reviewed `icons.js` as code, not rendered,
and redrawing blind would be worse than leaving a coherent first pass.
One audit for the next visual pass: check optical weight consistency
at 16 px (the `mia` mark's triangle-in-circle is the likeliest to muddy
at small size; if it does, simplify to ring + core dot). The 24-unit
grid / 1.6 stroke / `currentColor` contract stays.

## 3. Character art, presence, dashboard saying card

- **Presence (`presence.html`):** full Stark frame — corner brackets,
  mono readouts (state, level, last sync), reactor orb as built. No
  photo hero. The orb is the character here; it does not need a
  picture behind it.
- **Character art:** keep the existing art, presented inside the
  technical plate (same frame as every header). No new art
  commissioned. If plates go schematic per §1, the character gets the
  same frame and the art itself is unchanged.
- **Dashboard saying card:** becomes a readout panel — mono label
  ("MIA SAYS" or the card's existing label), the line itself, a small
  index mark. No photo, no warm styling. The words are the content;
  the frame stays quiet around them.

## 4. Protein gold: DEC-0023's gold rule wins (H-0031 note superseded)

My H-0031 note said "protein in gold, matching the recipe page." That
was under the old look. Under DEC-0023, gold is earned celebration
only. I endorse Claude's resolution in H-0034, with one tightening for
consistency:

- The protein bar turns gold when the target is hit — that IS the
  earned moment. Good.
- Meal-card protein text stays white. Good.
- Recipe-page protein macro goes white too (not gold). A recipe's
  macro is a value, not an earned state, and the guide's rule is
  "values are white; color sits beside them." One rule, everywhere —
  no second meaning of gold to remember.

Celebration itself is unchanged: gold card over a dimmed screen stays
the loudest thing in MIA (DEC-0014), quiet everywhere else.

## 5. DEC-0022: the "which level" indicator belongs in the shell

DEC-0022 already requires MIA to say which level she's on. Experience
call: that is a small persistent readout in the shell — a mono label
(PHONE / HOME PC / ONLINE) with a cyan dot, in the header or status
strip — not a dialog, not a setting buried in a page. Same indicator
carries the Talk fallback: if Talk drops to the phone model
mid-conversation, the readout changes and a one-line note appears
("fell back to phone model"); no popup, no re-ask. This needs no new
decision — it is DEC-0022's own "saying which level she's on," placed.

## 6. Glasses: agreed, later

When I get to the glasses composition, it takes the same language —
cyan on black, mono labels, compact readouts — and `glasses.css`
stays untouched until then. The high-contrast tokens are the closest
bridge today (DEC-0016 holds: no claimed glasses features).

## Guardrail (DEC-0008) — technical plates (§1)

1. MIA supports header plates now (just built, photo version). 2. The
Stark layer in `concept.css`, plus `tokens.css` (`--hero-tint`).
3. Not missing — a look refinement replacing the photo with a schematic
motif. 4. UI only. 5. No duplication; it removes the photo dependency.
6. Not Life State. 7. No life event. 8. No links. 9. No `/api/state`
change. 10. STATIC presentation. **Pass.**

## What's still open on my side

- A rendered visual pass on the Stark screens (plates, icons at small
  size, presence, saying card) before final look sign-off.
- Note: H-0033's "H-0031 does not exist" is resolved — H-0031 now
  exists in `docs/HANDOFFS/` and Claude already acted on H-0031/H-0033
  (reps on the timer card, Week planner on a phone, per H-0034). No
  action from anyone on that thread.
