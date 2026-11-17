# MIA OS: glasses, wearables and spatial hardware (Prompt 06 §8)

*Claude (Opus), 2026-11-17. Planning only. Spatial interface design is Prompt 11's.*

## 1. The glasses (verified as used; specifications from public sources)

Meta Ray-Ban Display with the Meta Neural Band. A small full-colour display in the right lens (reported 600 x 600, a
20-degree field of view, 90 Hz), camera, microphones, speakers; the Neural Band reads wrist muscle signals (EMG) as
gestures. Up to about 6 hours of glasses battery. **They don't run MIA:** MIA reaches them through the phone, with
Meta's Wearables Device Access Toolkit (camera, display, input, speech; `android-phone/`), and MIA's cards are
rendered on the phone side. A web path (an app at a URL) is also in Meta's developer preview.

| Capability | MIA's use | Status |
|---|---|---|
| Display | glance cards: Today, a reply, a step, a council line | built |
| Camera | "what am I looking at?" (Look) | built |
| Microphones and speech | voice to MIA through the phone | built |
| Neural Band gestures | next/back/select on cards | built where the toolkit exposes it |
| Motion | not used yet | later |

**Constraints:** everything depends on Meta's toolkit, still a developer preview, and on the phone being near. MIA's
rule holds: the glasses hold no data beyond a session (REQ-DEV-009), and every action is reachable on the phone.

## 2. After the glasses

| Device | Status | What it would need |
|---|---|---|
| A smartwatch | not owned | Wear OS companion; not planned |
| Other AR or VR headsets | speculative | the web front end in their browser first |
| A wrist or body sensor for health | speculative | Health Connect on the phone |
| MIA's own glasses | speculative (`docs/VISION.md`) | out of scope |

Nothing in MIA OS depends on any of these (DEC-0205).

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-HW-016 | MIA shall keep working fully when the glasses' toolkit changes or breaks: every glasses action stays available on the phone and the PC. | Must | MVP | Gl | Exists (parity, DEC-0125) | T: parity | DEC-0125 → 06 |

Sources: Meta's announcements and coverage of the Ray-Ban Display and the developer preview (Android Central,
Auganix, PPC Land, Neowin), read 2026-11-17; the repository's glasses code.
