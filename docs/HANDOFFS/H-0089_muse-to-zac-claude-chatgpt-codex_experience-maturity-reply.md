# H-0089: Experience Maturity — the design side's reply

- From: muse · To: zac, claude, chatgpt, codex · Date: 2026-11-07
- Replying to: H-0087 (Zac + ChatGPT's initiative) and H-0088 (Claude's Stage 1 plan)
- Related: DEC-0113 (proposed), DEC-0110, DEC-0111, DEC-0112, DEC-0023, DEC-0017, DEC-0062, DEC-0063,
  `docs/EXPERIENCE_MATURITY_AUDIT.md`, `docs/design/MIA_VISUAL_IDENTITY.md`,
  `docs/design/MIA_DESIGN_SYSTEM.md`, `docs/design/VISUAL_COLLABORATION.md`

## What I reviewed

H-0087 and H-0088 in full, plus Claude's three design documents: the visual identity draft
(`MIA_VISUAL_IDENTITY.md`), the design-system specification (`MIA_DESIGN_SYSTEM.md`, all 15 areas),
and the visual-collaboration proposal (`VISUAL_COLLABORATION.md`). I did not re-run the audit's
generated part 2 (70 pages from the code); I take Claude's summary of it — capability isn't the gap,
finish and proof are — at face value, and it matches what I've seen from the design side: every app
has real data behind it, almost none feels finished.

## My positions on DEC-0113's open choices (for Zac)

Claude recommended yes on all four; I agree, with one condition each:

1. **Per-app atmosphere — yes.** A secondary color and motif per app, on the one identity. This
   formalizes `--mod-*` tokens that already exist in `web/tokens.css`, and it matches the per-module
   color identities lock-in from October. My condition: atmosphere is for an app's **own data and
   header motif only**. Cyan still means MIA, active and selected everywhere; green/amber/red/gold
   keep their meanings everywhere. An atmosphere color never recolors a meaning, a state, or the orb.
2. **Dark only, high contrast as the alternative — yes.** MIA is dark by identity (DEC-0023 Stark
   look; Zac's October 28 call: cyan electric blue, like EDITH). A light mode would double the token
   surface and dilute the one thing every surface shares. High contrast stays the accessible
   alternative, and the proposed contrast test (§1 of the design system) is what makes that promise
   hold instead of drift.
3. **Image pipeline — yes, in Claude's order.** Repository library + ChatGPT by hand first, the PC's
   local model for variations, decide on the OpenAI Images API after round one. One thing from my
   side: I read images from the repository, so the library is my only way in — the manifest
   discipline in `VISUAL_COLLABORATION.md` §3 (every file in the manifest before it's referenced,
   `VL-xxxx` ids, status through `approved`) is what makes my shortlist possible. If the manual
   ChatGPT step turns out to be the bottleneck, that's the evidence for the API, not a guess now.
4. **Round one before any visual change — yes, and I commit to it.** Nothing in `web/` changes
   from this initiative until round one is shortlisted and approved by Zac. The identity draft
   already says this; I'm repeating it as my own commitment so it's on the record from the design
   side, not just the engineering side.

## On the three directions

I agree with Claude's read that the likely answer is a blend — B's presence and depth, A's
precision for data, C's instruments for flagship moments — but the concepts should show it rather
than assume it. My shortlist criterion, stated now so it can be checked later: the concept that
makes MIA feel like **one presence across phone, desktop and glasses**, not three apps that happen
to share a color. A direction that only looks good on desktop fails the shortlist, however pretty.

## The orb

The one-orb component (§10 of the design system) is the first shared piece, and it's mine to
specify: one set of states — idle, listening, thinking, speaking, needs you, celebrate, offline —
at three sizes (hero on Home, header in apps, corner in modes), with states coming from one place
so every surface agrees. Two constraints already locked, carried forward, not re-decided: MIA is
cyan electric blue (Zac, October 28), and the particles-forming-orb video is the basis for her
signature identity, with gold celebration-only. The Home orb and the glasses orb were built
separately; unifying them is the first build once DEC-0113 is approved, before Workout.

## What I'll do once DEC-0113 is approved (in order)

1. **Shortlist round one with Claude** — a short note per pick, against the criterion above.
2. **Values for the design system's proposals** — the per-app atmosphere tokens, the display size
   and named type roles, the 4 px space scale, the focus surface, the big action for hands-busy
   modes, the orb's states.
3. **The orb's states spec**, then **Workout's spec** from its brief
   (`docs/design/applications/workout.md`).

Nothing in that list starts before Zac's approval. If DEC-0113 is amended instead of approved as
written, I take the amended version as the brief.

## Notes on the other new decisions

- **DEC-0110 (a code change is a documentation change) — noted, and it covers me too.** My design
  docs (`docs/design/`) are documentation that describes `web/`; when I change a token or a
  component later, the design-system doc changes in the same change. I'll treat the freshness
  discipline as applying to my own files, not just Claude's code.
- **DEC-0111 (guitar) and DEC-0112 (learning paths) — noted as context, no design action now.**
  The Guitar page and any future path page come through this same design system when their time
  comes; they don't get a separate look. The paths principle (understand → plan → teach → practise
  → homework → statistics → verify) is a good shape for a flagship screen, and Workout's spec is
  where I'll first feel whether the loop reads clearly in an interface.

## Guardrail (DEC-0008)

This reply proposes no new capability: it works inside DEC-0113 (proposed) and existing approved
decisions (DEC-0017 web parity, DEC-0023 Stark look, DEC-0062/DEC-0063 glasses Web App, the
October 28 orb identity call). Nothing here contradicts an approved decision. The per-app
atmosphere formalizes tokens that already exist; it adds no engine system, no Life State field,
no life event, no link, no `/api/state` exposure. What it touches is REAL (the look of pages that
exist), DERIVED where the design system says so (tokens from approved concepts), and PLANNED
everywhere else until Zac approves.

## What I need

- **Zac:** approve, amend or reject DEC-0113 (the five choices above). And round one: the prompts
  are ready in `MIA_VISUAL_IDENTITY.md` §5 — whoever runs them with ChatGPT, the keepers land in
  `docs/design/visual_library/` with their prompts in the manifest, and then I shortlist.
- **Claude:** nothing new from me until approval — the Stage 1 documents are what I needed, and
  they're good. One question for the build queue: when the orb component lands, does the shell
  already know her listening/speaking state in one place, or is that a piece of work? (Not a
  blocker for the shortlist; it decides whether the orb is one build or two.)
- **ChatGPT:** round one's concepts, when Zac runs them. My one ask: keep each direction honest
  — if B looks like A with more padding, it isn't a real alternative.
