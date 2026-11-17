# MIA OS: visual open questions and risks (Prompt 11)

*Claude (Opus), 2026-11-17. Questions for Zac also appear in `MIA_OS_OPEN_QUESTIONS.md`.*

## 1. For Zac

| Q | Question | Recommended |
|---|---|---|
| **Q-83** | The Theme Studio already lets you make, save and share your own themes. Add to it: start from one of your pictures and MIA suggests colours from it that stay readable, and pick the orb's style? | Yes |
| **Q-84** | MIA already plays chimes for wins. Add quiet interface sounds: listening on and off, "needs you" and errors on by default; "done" and message chimes off; alarms always. The sound switch you have turns them all off (alarms excepted). OK? | Yes |
| **Q-85** | Add a Light theme now (high contrast is already a setting), and Graffiti and a Neon theme later? | Yes |
| **Q-86** | Zeta Astralis: try the forearm interface first on a small Android phone in a forearm mount running MIA's phone app, before any custom display? | Yes |

## 2. Risks

| ID | Risk | Response |
|---|---|---|
| R-61 | Effects use GPU time her models need | automatic step-down while generating (REQ-VIS-026) |
| R-62 | Many themes and personal palettes break readability | contrast checks refuse a failing theme (REQ-VIS-003, 013) |
| R-63 | The glasses' SDK limits what can be shown, and changes between releases | design within the cards; verify each SDK release |
| R-64 | The look drifts between Muse's designs, the code and the docs | tokens the only source; W3C token export for Muse's tools |

## 3. Before Prompt 12

Prompt 12 designs every device and how they link: it takes this document's per-device rules (desktop, phone,
glasses, household display, Zeta Astralis, spatial) as given.
