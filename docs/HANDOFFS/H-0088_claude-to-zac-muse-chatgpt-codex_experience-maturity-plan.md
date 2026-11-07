# H-0088: Experience Maturity, Stage 1: what's there, and the plan

- From: claude · To: zac, muse, chatgpt, codex · Date: 2026-11-07
- Replying to: H-0087 (the Experience Maturity handoff)
- Related: DEC-0113 (proposed), `docs/EXPERIENCE_MATURITY_AUDIT.md`, `docs/design/MIA_VISUAL_IDENTITY.md`,
  `docs/design/MIA_DESIGN_SYSTEM.md`, `docs/design/VISUAL_COLLABORATION.md`, `docs/design/applications/`

## What I did (Stage 1 only; nothing redesigned)

| Assignment | Deliverable |
|---|---|
| Review against the repository, the audit | `docs/EXPERIENCE_MATURITY_AUDIT.md`: maturity per app, Workout and Kitchen in depth, documents that disagree, inconsistencies, constraints; part 2 is generated from the code (70 pages, 52 apps, 168 routes, 306 action kinds, tokens and components) |
| Collaboration proposal | `docs/design/VISUAL_COLLABORATION.md` + the empty library `docs/design/visual_library/` with `MANIFEST.md` |
| Initial concept exploration plan | `docs/design/MIA_VISUAL_IDENTITY.md` §4–5: three directions (Workshop OS, Ambient presence, Heads-up instruments) and round one's ready-to-paste ChatGPT prompts |
| Design-system specification | `docs/design/MIA_DESIGN_SYSTEM.md`: all 15 areas, each "built today" vs "proposed" |
| Workout and Kitchen briefs | `docs/design/applications/workout.md`, `kitchen.md`, and the 18-part `TEMPLATE.md` |
| Dependencies, risks, decisions | below |

## Findings that shape the plan

- **Capability isn't the gap; finish and proof are.** Everything has real data behind it; almost nothing has been
  used enough to call it trusted (Kitchen opened once on this PC, Workout never; the phone keeps its own counts).
  Workout and Kitchen are both at level 3 (Integrated).
- **Design documents disagree.** The desktop-era handoff (2026-09-27) and the photo-header mobile concept (DEC-0018)
  are superseded by the Stark look (DEC-0023); the audit's §4 says which to keep as history.
- **Per-app atmosphere already half-exists**: `--mod-*` tokens are in `web/tokens.css`, all pointed at cyan since
  DEC-0023. The handoff's per-app moods would only give them their own values.
- **Two orbs** (Home's and the glasses') were built separately; one orb component is the first shared piece.
- **The ChatGPT app can't be called by Claude**; the OpenAI Images API can be, with a key, a cap and approval; the PC
  already has a free local image model (SDXL-Turbo).

## Risks

- **Designing for capability nobody uses**: mitigated by making real use the gate to level 5, and measuring it
  (page usage, a maturity register).
- **A redesign breaking working pages**: new component names come with aliases; flagship pages move one at a time;
  the test suite and a screenshot check per page.
- **The phone part of Workout** needs an Android build and real-device testing (native count voice, workout listening):
  the biggest schedule risk for "Trusted".
- **Concept art becoming the interface**: concepts are references; screens are built from tokens and components.
- **Image API cost and credentials**, if chosen: a key Zac creates, a monthly cap, approval per batch.

## Decisions for Zac (DEC-0113, proposed)

1. Approve the Experience Maturity direction and its sequence (identity → shared shell → Workout → Kitchen → widen),
   and the maturity standard with a measured register.
2. **Per-app atmosphere**: a secondary color and motif per app on the shared identity (Claude: yes).
3. **Dark only**, with high contrast as the accessible alternative (Claude: yes).
4. **Image pipeline**: start with the repository library and ChatGPT by hand, plus the PC's local model for
   variations; decide on the OpenAI Images API after round one (Claude: yes, in that order).
5. **Run round one** of concepts (the prompts in `MIA_VISUAL_IDENTITY.md` §5) before any visual change is built.

## Next, once approved

- **ChatGPT**: round one (five prompts × three directions); Zac saves the keepers to the library.
- **Muse**: shortlist with Claude; values for the design system's proposals; the orb's states; then Workout's spec.
- **Claude Code**: the contrast test, the one orb component, named surfaces and buttons (with aliases), then
  Workout's build; in parallel, the engine pieces that don't wait on the look (Kitchen's cooking session).
- **Codex**: review each built piece against its spec.
