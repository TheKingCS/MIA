# MIA OS: the orb (Prompt 11 §8; DEC-0237)

*Claude (Opus), 2026-11-17. Planning only. Presence from real events only (`core/orb_state.py`): never a timer
pretending.*

## 1. States

| State | Shape and motion | Colour | Label (always available) | From | Exists |
|---|---|---|---|---|---|
| Idle | still sphere, slow breathing glow | accent | "MIA" | nothing happening | yes |
| Listening | rings expanding with his voice level | accent, brighter | "Listening" | mic open | yes |
| Processing | inner swirl | accent | "Working on it" | request received | partial |
| Thinking | orbiting points | accent | "Thinking" | model generating | yes |
| Council | several orbiting points of different colours | scheme accents | "Asking my council" | council running | yes |
| Speaking | surface ripples with her voice | accent | "Speaking" | TTS playing | new |
| Interrupted | ripple stops, short contraction | accent | "Stopped" | he interrupted | new |
| Waiting for approval | a notch ring, steady | amber | "Needs you" | a card waiting | new (the colour exists) |
| Executing | a progress arc around | accent | "Doing it: …" | an action running | yes (working) |
| Background | a small dot orbiting | accent-soft | "Working in the background" | a run in progress | partial |
| Success | one bright pulse | green | "Done" | a change finished | yes |
| Warning | a slow amber edge | amber | "Something to look at" | a warning | yes |
| Error | a broken ring | red | "Something went wrong" | a failure | new |
| Unavailable | grey, no glow, dashed outline | ink-faint | "Offline: answers in words are off" | model or runtime down | new |
| Muted | a slash across the mic glyph inside | ink-dim | "Muted" | mic disabled | new |

**Never motion alone:** each state has its label (shown on hover, said by a screen reader, written under the orb in
reduced-motion mode) and its distinct shape or colour. Priority when several apply: error > approval > listening >
speaking > council > thinking > executing > warning > background > idle (extends `orb_state.PRIORITY`).

## 2. Per device

| Device | Render |
|---|---|
| Desktop | CSS and canvas; particles at full effects |
| Phone | CSS only; no particles on battery |
| Glasses | flat rings on black (see-through), the label in one line |
| Small displays | a glyph and its label |
| Spatial | a 3D sphere (the Nexus's renderer) |
| Low power, reduced motion | static glyph per state, the label always shown |

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-VIS-009 | Every orb state shall have its own label and a shape or colour distinct from the others, and appear only from a real event. | Must | R1 | All | Partial | T: one test per state | DEC-0237 → 11 |
| REQ-VIS-010 | With reduced motion, each orb state shall be a static glyph with its label shown. | Must | R1 | All | New | T | DEC-0237, DEC-0238 → 11 |
