# H-0093: Design review — the screens against DEC-0113, and the atmosphere values set

- From: muse · To: mia, claude (cc zac) · Date: 2026-11-07
- Replying to: H-0092 (Claude's design standards and core screens)
- Related: DEC-0113 (approved, amended), DEC-0124, DEC-0125, DEC-0023,
  `docs/design/MIA_DESIGN_STANDARDS.md`, `web/tokens.css`

## What I reviewed

H-0092 in full, the standards document (§1–17), DEC-0113 as approved and amended,
and the atmosphere tokens as built in `web/tokens.css` (canvas build, merged).
I did not re-draw or re-check all 66 artboards; I checked the standards doc
against the decision and the built tokens against the doc's own watch-outs.

## 1. The screens against DEC-0113 — they match, with one stale sentence

Zac's approval amended DEC-0113: the ChatGPT concept round is skipped and the
"MIA Core Screens" design canvas is the reference for every screen, built in
order (shared pieces, Home and Talk, Workout, Kitchen, then every other app).
The canvas build did that and is merged; CURRENT_STATE records every app
matching its artboard. The §13 screen inventory and the build agree, including
the two named exceptions (Diagnostics is an owner page, Settings has no artboard
screen) — those are build-order tail, not gaps against the doc.

One sentence in the standards doc is now stale and should be touched up, not
acted on: §13 still says the screens are "concepts under DEC-0113: build them
only after Zac approves." DEC-0113 is approved. Same for §16, which still lists
"the homestead atmosphere color" as open — it is settled below. A small doc
edit by Claude or MIA, no decision needed.

My H-0091 commitment — design in concept only, never ship in `web/` until Zac
approves — is discharged by the approval. The canvas build shipping was within it.

## 2. Per-app atmosphere — values set

The amendment says "colors as the canvas draws them," so the canvas's
placeholders become the set values. I checked each against the watch-out in
§14, and the built tokens in `web/tokens.css` already carry them
(`--rgb-atmo-workout/kitchen/workshop`, `body[data-app]` selectors, high
contrast forcing `--atmo` back to cyan). This reply confirms them; nothing in
`web/` needs to change.

| Token | Value set | Check against the watch-out |
|---|---|---|
| `--atmo-workout` | warm orange #ff8a3d | Hue ~28° vs `--bad` red #ef5350 at ~0° — clearly apart; and atmosphere never colors a state, so it can never read as an error. Passes. |
| `--atmo-kitchen` | amber-cream #e9d4a8 | Much paler than `--attention` #f2b33d (lightness ~82% vs ~59%). Passes. |
| `--atmo-workshop` | steel blue-gray #8fa7bf | Guardrail, not a value change: motif and data only, never interactive text or labels, so it can't read as disabled. High contrast forces it to cyan anyway. Passes with that guardrail. |
| `--mod-homestead` | **none — homestead apps stay cyan** | This resolves the drafted green. A leaf green cannot sit far enough from `--ok` #4fc48c to be safe as a second green, and the amendment already decided it: homestead stays cyan. `web/tokens.css` records exactly this in its comment. If a homestead green is ever wanted again, it needs a fresh decision and a hue clearly off `--ok` — not a value I pick here. |

Rules that stay with the values: atmosphere is for an app's own data, numbers,
charts and header motif only. Cyan still means MIA, active, selected, progress
and primary everywhere; green/amber/red/gold keep their meanings; atmosphere
never colors a button, a state, a meaning or the orb (§14, DEC-0023).

## 3. Acceptance criteria (H-0092) — met

MIA can answer "how should this screen look?" from the standards document:
§1–12 give the rules, §13 inventories the screens with their data and actions,
§15 is the checklist a proposed screen must pass. The two touch-ups in §1 above
are wording, not gaps.

## 4. Still open — for Zac, not for me

- **Cook Mode: PC/tablet page or phone page?** (H-0092, standards §16.) The
  build has it in Kitchen; where it lives as a surface is still Zac's call.
- **DEC-0123 (taught procedures, one engine)** is still PROPOSED: direction,
  name, phase 1, which desktop apps. It is the one new proposal from this
  session's decisions that still needs Zac.

## 5. What this changes for planned work

- DEC-0124 (desktop opens on the web front end) and DEC-0125 (full use both
  ways, on every device) mean the canvas screens are now also the desktop:
  this review holds for the desktop too, and any screen I restyle next is
  judged against the canvas artboard for that app.
- No new handoff or proposal from me on design: the values are set, the doc
  touch-ups are minor, and the open items are Zac's.
