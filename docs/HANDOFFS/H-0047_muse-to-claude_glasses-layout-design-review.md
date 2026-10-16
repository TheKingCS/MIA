# H-0047: Glasses layout + pins — design review (accepted, with polish notes)
- From: muse · To: claude (cc zac) · Date: 2026-10-16
- Related: H-0045, H-0046, H-0044, H-0043, H-0042, H-0041, DEC-0024, DEC-0023, DEC-0016, H-0035

## Response

H-0045 and H-0046 are accepted as built. Two things noted for the
record: Zac's favorites ordering (DEC-0024) supersedes H-0044's
"most used first" — no usage tracking, no conflict to resolve. And
the layout in H-0046 (orb alone, no scroll, two moves, no chat bar)
is exactly what Zac asked for. Nothing here needs Zac's approval;
everything below is small, reversible polish inside those constraints.

## Polish notes (look only, no engine changes)

1. **Saturn rings:** the near-half pass should dim slightly so her face
   stays legible while listening. Keep the tilt fixed — it should read
   as an orbit, not a wobbling ellipse.
2. **Orb alone:** her answer text under the orb caps at ~2 lines, then
   fades. Keep the idle breathing amplitude subtle — she breathes, she
   doesn't bob.
3. **Back row:** style it distinct from action rows (dim + chevron) so
   it reads as navigation, not another action. It must stay reachable
   inside the 5-row window.
4. **Confirm two-row:** Approve selected by default is fine; Cancel one
   move away. Keep the labels verb-first (Approve / Cancel).
5. **Pin row:** use the star glyph from the Apps page so the pin and
   the favorite read as the same thing. The dashed row and the
   "Pin to / Unpin from glasses" wording stand.
6. **Line icons:** one consistent stroke weight at glance size. The
   letter stays as fallback only when an icon is missing. Verify the
   icon frame doesn't crowd the 54 px app name at phone-width fit —
   that clipping is what Zac saw.
7. **Missions card:** if a mission has more than 4 objectives, show the
   first 3 + "n more" so the card stays inside the fixed composition.
   Objective checkmarks in white/cyan; gold only on the claim-ready
   celebration (gold = celebration only, H-0035).
8. **Long status lines:** truncate with an ellipsis, never wrap onto a
   second line that pushes the composition.
9. **Inbox / Household / People panels:** accepted as built — all
   read-only, "Any emails I should answer?" returns MIA's sentence,
   nothing is sent or filed.

## One engine question (yours to settle, no Zac approval needed)

- People: "Who haven't I talked to in a while?" needs a stated rule
  for "a while" — e.g. 30 days, or a per-person cadence if Life State
  already holds one. State the rule in your reply or in
  CURRENT_STATE so the panel never answers from free text.

## Guardrail (DEC-0008)

UI polish only. No new engine surface, no Life State change, no
`/api/state` change, nothing duplicated, nothing new to track. All
items above are REAL look work on what H-0045/H-0046 already built.
