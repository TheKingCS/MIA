# H-0094: Generated environments — MIA builds the place around you

- From: muse (for zac) → To: claude, chat (cc zac)
- Date: 2026-11-08
- Related: DEC-0130 (Nexus, accepted), DEC-0128 (device fabric, PROPOSED), DEC-0123 (taught procedures, PROPOSED), DEC-0127 (subscription product, PROPOSED), DEC-0119 (MIA for Zac alone, never children), DEC-0114 (Highest Self, PROPOSED), DEC-0002 (no personal data in the repo), DEC-0053 (offer-then-search), DEC-0014 (MIA does not punish the user for being human); draft filed as DEC-0132 (PROPOSED)

## Context

On 2026-11-08 Zac studied two reels from the AR/AI creator AETHER (@ae.t.he.r, Quest 3) and directed that what they show becomes a MIA function:

1. A voice-driven orb in mixed reality generating objects on spoken command — an apple, an info panel, physics — no menus, no controllers.
2. His biggest reel (18.8k likes): the orb transforming his bedroom on voice command — Witcher interior, then Minecraft, then Cyberpunk, characters appearing and persisting across changes, then back to the real room. His caption: the orb was his first AR project; he dreamed of diving into any reality, like in Ready Player One; the orb became his identity.

Zac's direction, in substance: the ability to generate environments in real time is absolutely a function MIA will have in the future. He then extended it himself, in the same conversation, to the social form: sit in a virtual bar when home alone or with friends; meet people in virtual places; friends who are there are cut into the same scene, each seeing the same scene from their own perspective.

The convergence is not lost on him: Ready Player One / the OASIS is already MIA's recorded long-term vision (Lens Arcade's hub, Oct 2026). AETHER went orb → identity → generated worlds as experiences. MIA is going orb → identity → a someone who runs your life, with generated worlds as one of her powers. The difference is the point: he generates places; MIA generates places *for a purpose in a life she knows*, remembers them, and hosts you in them.

Honest staging note (from muse's read of AETHER's own how-it-works post): today's working pipeline is scan the room → an AI coding agent builds a scene app on a PC (minutes) → step in on Quest. The reel's seamless morphing is the sizzle cut. This proposal tiers the function accordingly and promises no dates for the frontier tier.

## What's needed

**From claude — a feasibility read:**
- Pipeline options on the stack MIA already has. The Nexus (DEC-0130) is a web build (2.5D first, every device at its own depth). Can generated environments ride the web/WebXR stack, or does Tier 1 need a Unity build on the PC? What serves Quest best without forking the one brain?
- Asset and scene generation routes: text-to-3D / scene services vs procedural and template composition from parts she assembles. What runs on the PC on hand (Ryzen 7 9800X3D, RX 7900 XTX 24 GB) vs what needs a cloud service (cloud use only under the constraints below)?
- Room input: what a Quest room scan gives her today, and what the device fabric (DEC-0128, if approved) adds — surfaces, lighting, anchors she can generate against.
- Tier 2 sync: options for multi-user shared scenes where each person is present in the same generated space from their own perspective (hosted relay? peer? an existing platform's rooms?), and what presence of a friend minimally requires from their side (Quest? glasses later? phone fallback?).
- Sequencing: where Tier 1 slots after the current Nexus/canvas work, and the smallest demonstrable first scene.

**From chat — the vision check:**
- MIA inside a generated place: host, bartender, ambient presence, or the place itself being hers? What keeps a virtual bar she runs *MIA* and not a game lobby — and what does the Highest Self doctrine (DEC-0114, if approved) say about how she carries herself in a social space?
- Generated environments for a purpose vs for escape: MIA's principles say she helps a person live their life, not become their life. Where is the line she should hold by design?

## The proposal (draft DEC-0132)

1. **Environment generation is a named MIA capability**: speak, and MIA generates the environment around you. Generation is an engine capability, never a surface fork — the PC builds; Quest is the dive surface; the Nexus is where generated places live as destinations (portals); glasses get the glance layer and, on Orion-class hardware later, generated overlays in real space.
2. **Tier 1 — she builds it, you step in (near-term).** Spoken request → MIA composes/builds a scene on the PC from a room scan or from a Nexus environment brief (minutes, honestly labeled) → step in on Quest. First scenes are places with jobs: walk the walipini before digging it, stand in a workshop layout before buying lumber, a focus room, a bar's first rough cut. Generated places persist in the Nexus and can be re-entered and revised by voice.
3. **Tier 2 — shared generated places.** Friends present in the same generated scene, each from their own perspective: the virtual bar at home, alone with MIA hosting or with friends cut in; meeting people in virtual places. Everyone present is there by their own opt-in (constraints below). MIA hosts: she keeps the scene coherent across viewers, runs the ambience, and is a presence in it.
4. **Tier 3 — real-time generation (frontier, no dates).** Speak and the room re-renders around you live; objects and characters persist across transformations; generation latency and hardware (Orion-class glasses) decide when this tier opens. Named as the north star so Tiers 1–2 build toward it instead of painting into a corner.

## Constraints

- **DEC-0002 holds absolutely.** Room scans and geometry of Zac's home are personal data: they stay local and private, never in this repo, never committed as fixtures or "sample rooms." Public demos use a sample persona's room, as with all MIA demo data.
- **Cloud generation is opt-in per service.** If a tier needs a cloud text-to-3D or scene service, MIA offers it first and sends nothing until Zac approves that service (the DEC-0053 pattern). Local generation on his GPU is the default route wherever it can carry the quality bar.
- **People are not props.** A friend's presence/likeness in a shared scene is their data: shared scenes only with everyone present opted in; no recording of a shared space without everyone in it knowing; MIA never generates a real person's likeness into a scene uninvited.
- **DEC-0119 boundary.** Tier 2 opens friends-only. Public social worlds — meeting strangers in generated places — raise moderation, safety and identity questions that need their own decision before that door opens; nothing in this proposal approves it.
- **Enter by choice, never ambient.** Generated places are destinations Zac asks for. They never interrupt, nag, or pull him out of his real life; the Nexus stays the calm home and "less friction, not more notifications" governs her hosting too (DEC-0014: MIA does not punish the user for being human — including for leaving a virtual bar to go live his actual evening).
- **Cost is visible.** Generation compute beyond the local GPU is money; any recurring generation cost surfaces in the open like every other MIA cost, and product questions (does generation ship in the DEC-0127 subscription, at what tier) stay Zac's calls there, not settled here.

## Open questions for Zac

1. Approve the direction and the three tiers as drafted (DEC-0132)?
2. Tier 1's first scene: the walipini walkthrough, the workshop layout, the bar's first cut, or a focus room?
3. Local-only generation to start, or is one approved cloud service acceptable if the quality gap is large?
4. Tier 2 scope: friends-only as drafted, with public social worlds as a separate later decision?

## Acceptance criteria

- DEC-0132 recorded in `docs/DECISIONS.md` as PROPOSED with this tiering and these constraints, status Zac's to change.
- Claude's feasibility handoff returns pipeline, generation-route, room-input and sync findings, plus a smallest-first-scene recommendation.
- Chat's vision reply on MIA's role inside a generated place is on file before any Tier 2 design work.
- No build starts before Zac approves DEC-0132.
