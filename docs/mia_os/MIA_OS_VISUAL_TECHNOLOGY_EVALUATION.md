# MIA OS: visual technology evaluation and decision records (Prompt 11 §23, §25)

*Claude (Opus), 2026-11-17. Planning only. DEC-0234 to 0240 are PROPOSED.*

## 1. Technologies

| Need | Options | Recommendation | Why |
|---|---|---|---|
| Styling | CSS custom properties (exists), a CSS framework (Tailwind), CSS-in-JS | **CSS custom properties** | already the whole system; no build step; themes swap values at runtime |
| Design tokens as a standard | W3C Design Tokens format, Style Dictionary | **export to the W3C format** for Muse's tools, generated from `core/themes.py` | keeps one source; tools read it |
| Orb and effects | CSS + canvas 2D (exists), WebGL, Lottie | **CSS and canvas**; WebGL only in the 3D room | light, reduced-motion friendly |
| 3D and spatial | three.js (the Nexus), Babylon.js, WebXR | **three.js** now; WebXR when a headset exists | exists; WebXR is the standard path to headsets |
| Fonts | Inter, Noto, JetBrains Mono | **Inter and JetBrains Mono** in the image (SIL Open Font Licence) | readable, open, offline |
| Icons | own line set (exists), Lucide, Phosphor | **own set**, extended in Lucide's grid style | consistent; open licences if borrowed |
| Linux app theming | KDE colour schemes, Kvantum | **KDE colour schemes** | supported by KDE; no extra engine |
| Sounds | Web Audio tones (exists), WAV/OGG files | **Web Audio tones**, as `web/sound.js` | no files, offline, voiced per theme |
| Contrast checks | own (WCAG formula in code) | **own** | simple, testable |

## 2. Decision records

### DEC-0234: one design system for every device
Requirements: REQ-VIS-001, 002, 005, 006, 017, 018, 019, 024. Selected: tokens only, set by theme data; every device
renders MIA's web screens with the full or reduced set. Rejected: a native design system per platform (three to keep
in step). Reversibility: high.

### DEC-0235: the identity holds without colour, transparency or motion
Requirements: REQ-VIS-003, 007, 008, 014, 025. Selected: the orb's shapes, labels, the one accent, mono labels and
the layered layout carry identity; a Light theme; high contrast over any theme (exists).

### DEC-0236: themes and personalisation are validated data
Requirements: REQ-VIS-004, 013, 015, 016. Selected: the Theme Studio's checked data (known tokens, clamped,
contrast-checked, backdrops by id); no CSS, script or URLs. Rejected: user CSS (could hide the approval card or load from the internet).

### DEC-0237: the orb, one component, fourteen states
Requirements: REQ-VIS-009, 010, 015. Selected: state from real events, each with a label and a distinct shape or
colour; static glyphs in reduced motion.

### DEC-0238: motion in three speeds, meaningful apart from decorative
Requirements: REQ-VIS-010 to 012, 026.

### DEC-0239: spatial interfaces are views of the same capabilities
Requirements: REQ-VIS-020 to 022. Selected: portals open the same screens; features labelled by hardware.

### DEC-0240: a small local audio identity
Requirements: REQ-VIS-023. Selected: the win sounds kept; listening, needs-you, error and done tones added the same
way; the one existing off switch; alarms always.
