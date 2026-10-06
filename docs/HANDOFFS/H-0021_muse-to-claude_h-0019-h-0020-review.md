# H-0021: Review of the equipment and kitchen/workout/real-estate screens
- From: muse · To: claude (cc zac, chatgpt) · Date: 2026-10-06
- Related: DEC-0017, DEC-0018, H-0019, H-0020, Q-0014, `docs/design/IMAGE_REQUESTS.md`

## Context
Read H-0019 and H-0020 in full. Verified against the live preview (`thekingcs.github.io/MIA/web/garage.html` renders the strip, the red Needs Attention panel, asset cards with top tasks and status chips, and Next up) and the repo source (`equipment.js` shared across the four screens, `concept.css` module tokens for Kitchen/Workout/Real Estate).

## What's accepted
- **Reviewer/polisher role** per DEC-0018 item 4 (you build the look, I review and polish). I'm *not* doing a unilateral restyle — DEC-0018 deliberately changed the split, and I won't silently contradict it.
- **The screens hold the concept pattern.** The strip, the red needs-attention list, asset cards with tasks and chips, the tabbed sections, daily-mission progress bar, per-exercise sparklines, property figures — all of it reads as MIA's look on the live preview.
- **The data flow stays yours.** Every change stays an action with confirm and undo; `MIAShell.form` stays the single form path.

## Notes (non-blocking, your call on implementation)
- **Asset icons** (🚗 🚜 🔌 🏠 🌱 🔨): keep yours. They read well and stay honest for kind, not identity.
- **Asset page's seven tabs on the phone:** keep the sideways scroll under the tab styling — it's the established phone pattern. If it ever feels hidden, a 2px gradient fade at the strip's right edge would be the smallest honest affordance.
- **Photo fields:** yes to all three — answered in Q-0014. Assets, recipes and properties each get a photo + upload into `web/img/`; cards and the asset page show the photo when one exists, module-color placeholder until then. DEC-0002 holds: photos come from Zac's own library through the upload action, nothing real lands in the repo through me.
- **"Replaces Muse's summary-only pages" (H-0020):** agreed — my static concept pages served their purpose as the design target; the working screens are the real thing now. The concept pictures remain the reference for the look.

## Constraints
- Keep every action propose → confirm → undo (H-0019/H-0020 acceptance criteria stand after any polish).
- Placeholders only in the repo (DEC-0002); demo-labeled on the public preview.
- Guardrail (DEC-0008) run on this handoff: no new life events, no schema extensions on my side, no duplication, read/propose/approve intact — pass.

## Acceptance criteria
- My sign-off on the look after your concept pass: the screens match the concept pattern above and every flow stays undoable. Given.
- Next is Missions, Skills, Character (H-0013); nothing from me blocks that queue.
