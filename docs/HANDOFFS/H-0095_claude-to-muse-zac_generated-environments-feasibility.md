# H-0095: Generated environments — Claude's feasibility read

- From: claude → To: muse, zac (cc chat)
- Date: 2026-11-08
- Answers: H-0094 ("From claude — a feasibility read"). DEC-0132 stays PROPOSED; nothing here is built, and no build
  starts before Zac approves it.
- Related: DEC-0130 (the Nexus, built: `web/nexus.html`, `web/spatial.js`, the Garage environment), DEC-0128, DEC-0053,
  DEC-0002, DEC-0119, DEC-0126 (sealed at rest)

## The short answer

Tier 1 is feasible on the stack MIA already has, with no Unity fork: the PC composes the scene, MIA's own web server
serves it, and the Quest steps in through its browser (WebXR). Composition from a vetted local asset library, plus
parametric pieces built from real measurements, carries the quality bar; local image-to-3D on the 7900 XTX fills in
one-off props. Unity becomes worth it only at Tier 3 (live person tracking, heavy real-time effects). The smallest
first scene: **Zac's workshop layout, built from his real measurements, walked in VR, then pinned to the real garage
floor in passthrough.**

## 1. Pipeline: web/WebXR or Unity?

**Recommendation: WebXR for Tiers 1 and 2, served by MIA's PC.** Reasons:

- **One brain, one front end.** The Nexus is already a web build; a generated place becomes a page
  (`place.html?id=`) the Nexus links to as a portal, the phone opens as a window, and the Quest enters as an immersive
  session. No second app to sideload, update or keep in step with the engine.
- **Quest Browser covers Tier 1's needs today.** Meta documents WebXR passthrough (`immersive-ar`), plane detection
  (walls, floor, tables as horizontal or vertical rectangles) and anchors, including persistent ones (limits: 8
  persistent anchors per site; none in private mode; planes arrive 2 to 3 seconds after the session starts; one room
  capture prompt per session). Mesh detection on Quest 3 is reported but not on that page, so verify it on device.
- **The pipeline:** speech → MIA plans the place as a **scene document** (JSON: bounds, pieces with transforms,
  materials, lighting, sky, sound, the door's descriptors) → code checks it (sizes, counts, budgets) and builds what's
  missing → three.js renders it on PC, phone and Quest from the same document → saved as a place in the person's own
  folder, a portal in the Nexus, revisable by voice ("move the bench to the north wall") as edits to the document.
- **Same rule as the rest of MIA:** the model proposes the composition; code holds the facts (real dimensions from
  `core/build_calcs.py` for a walipini or a workshop, counts, budgets).
- **When Unity earns its place:** Tier 3's live morphing and people overlays need body and person tracking, native
  scene mesh and frame budgets the browser won't give. Even then, the scene document stays the source and a Unity
  client is one more renderer of it, not a fork of the brain.
- **Performance budget on Quest Browser:** about 100k triangles visible, baked lighting, compressed textures (KTX2),
  one dynamic light. Composition from game-ready parts fits; raw generated meshes need decimation before use.

## 2. Asset and scene generation routes

Ranked, local-first (DEC-0053: a cloud service only when Zac approves that service):

1. **Composition from a vetted library** (default). CC0 sets (Poly Haven, ambientCG, Kenney, Quaternius) vendored
   offline and tagged by kind and scale. This is what makes Unity Spark's results credible (Muse's addendum), and it
   keeps scenes coherent. MIA picks and places; code checks scale and collisions.
2. **Parametric pieces in code** for anything with real measurements: walls, benches, shelving, beds, a walipini's
   trench and glazing, with sizes from Zac's own data or `build_calcs`. Exact, cheap, and honest.
3. **Local image-to-3D for one-off props.** TRELLIS 2 runs on the RX 7900 XTX under ROCm (tested on gfx1100):
   about 30 seconds at 512 voxels, 90 seconds at 1024 and 3 minutes at the finest setting, 16 GB+ for textured BF16.
   It's image-to-3D, so pair it with a local text-to-image step, decimate, and cache. Labelled "about a minute" in
   the UI, not instant.
4. **Skies and backdrops:** local diffusion panoramas, which are cheap and do much of the "transport" work.
5. **Cloud scene services:** only per service, offered first, nothing sent before Zac approves it; the cost shown
   like every other cost.

The Ryzen 7 9800X3D and the 24 GB card cover all of 1 to 4 locally. Generated assets are cached by prompt and
reused, so a place reopens instantly.

## 3. Room input

- **What the web gets today (Quest Browser):** passthrough, planes (walls, floor, desk), anchors, and the room capture
  prompt. No raw camera pixels. That's enough to pin a generated layout to the real floor and walls (Tier 1 in
  passthrough) and to keep it there across visits with persistent anchors.
- **What it doesn't get:** Space Setup's full scene mesh isn't exportable as a file. A native app can read it through
  Meta's scene APIs (MRUK), which is the Tier 3 route if mesh-accurate occlusion is needed.
- **Privacy (DEC-0002, DEC-0126):** a room's planes and anchors are personal data: kept in the person's folder, sealed
  at rest, never in the repo. Demos use a sample persona's room.
- **What the device fabric adds (DEC-0128, if approved):** live state rather than geometry, such as the lights' color
  and level (so a generated scene can match or drive them), sensors and cameras. Room shape still comes from the
  headset.

## 4. Tier 2: shared places

- **Self-hosted on the PC first.** The scene document is authoritative on MIA's server; each guest sends head and hand
  poses about 20 to 30 times a second over a WebSocket; voice over WebRTC. Remote friends need a reachable address
  (a mesh VPN invite such as Tailscale, or a TURN relay); no third-party platform rooms (ownership, DEC-0002's
  spirit).
- **Libraries to stand on:** Networked-Aframe's model (open source, WebRTC and WebSocket adapters, a documented
  open-metaverse architecture) shows the pattern works on the web; MIA's version stays small and lives in its own
  server.
- **What a friend minimally needs:** a link and an invite token. On a Quest, they step in; on a phone or PC, they get
  a window into the scene with an avatar. Glasses get presence later. Each person sees the scene from their own pose
  because each renders it locally from the same document.
- **Friends only** (DEC-0119, H-0094): public worlds need their own decision.

## 5. The door: warnings before entry, kept light

- **Descriptors live on the place**, not in a ban list: violence, mature themes, horror, flashing or photosensitivity,
  social (others present), generated-by. Some are set by code from the scene document, not the model: strobing
  lights mark flashing, and invited guests mark social.
- **One card, three sizes.** In the Nexus, chips on the portal and an Enter / Not now card. On the Quest, a panel in
  front of you before the scene loads; entering is one pinch. On the glasses, a one-line glance ("The Bar: social,
  mature. Enter on the headset"). Shown once per place until its descriptors change, so it informs without nagging.
- **Host controls:** who may enter (only me, invited, friends) and the styling policy for a private place (open,
  propose-only, locked), shown on the card.

## 6. The Public Square rule in practice (open for claude in H-0094)

- **Overlays come from a catalog with tags.** A filter, accessory or outfit carries what it is; anything tagged
  degrading, sexualizing or targeting (labels, slurs, "on person X only" text) isn't offered for other people. The
  model never decides this; the tags do.
- **Standing recourses are instant and local:** lock my look, strip this off me. Both are one gesture, and both work
  without the host.
- **Repeat targeting is counted, not judged.** If someone re-applies overlays to a person who keeps stripping them
  (three times in a session), their overlays on that person stop and the host sees it. Host removal of a guest is one
  action.
- **Recording** needs everyone present to know: a visible recording mark for all, and no capture of a scene with
  guests unless each has seen it.

## 7. Sequencing and the smallest first scene

- **Where it slots:** after the Nexus on the glasses (NEXUS_PLAN M4) and Zac's review of the Garage environment.
  Tier 1 is then four steps: the scene document and its checker; the place page (three.js, VR and passthrough); the
  library and parametric pieces; voice to create and revise.
- **First scene: the workshop layout.** It's a place with a job, built entirely from Zac's real measurements and
  MIA's Garage data, with no characters, no sync and nothing generated by a model beyond the arrangement. Walk it in
  VR first, then pin it to the real garage floor in passthrough before buying lumber. The **walipini walkthrough**
  is second (the same pieces plus `build_calcs`); the **bar's first cut** waits for Tier 2.

## Risks, honestly

- Quest Browser performance is the ceiling for Tier 1 visuals; composition and baking keep within it.
- Mesh detection on Quest 3's browser needs confirming on the device before anything depends on it.
- Local text-to-3D quality varies; the library route stays the backbone, and generated props are labelled.
- Tier 3's seamless morphing remains frontier work, as H-0094 says; nothing here promises a date.

## For Zac

1. Approve DEC-0132's direction and tiers?
2. First scene: the workshop layout (recommended), the walipini, the bar's first cut, or a focus room?
3. Local only to start (recommended: everything in section 2's routes 1 to 4 runs on the PC)?
4. Tier 2 friends-only, as drafted?

## Sources

- Meta, WebXR mixed reality on Quest Browser: https://developers.meta.com/horizon/documentation/web/webxr-mixed-reality/
- TRELLIS 2 on ROCm (RX 7900 XTX): https://github.com/toastmanAu/trellis-2-rocm-comfyui
- Quest scene mesh is app-side, not exportable: https://communityforums.atmeta.com/discussions/dev-quest/export-space-mesh-scanned-on-quest-3/1095570
- Networked-Aframe as an open-metaverse basis: https://arxiv.org/html/2404.05317v5 ; https://github.com/networked-aframe/networked-aframe/discussions/432
