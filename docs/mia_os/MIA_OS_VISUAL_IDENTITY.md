# MIA OS: visual identity, themes and spatial interfaces (Prompt 11)

*Claude (Opus), 2026-11-17, on Zac's go ("lets go"). Planning only: no style sheet, theme, asset or navigation was
changed. The prompt is `prompts/11_VISUAL_IDENTITY_THEMES_SPATIAL_INTERFACES.md`. Muse owns the look (DEC-0017,
DEC-0023): this sets the system and its rules, and Muse refines the values. Twenty-four documents sit beside this one
(section 9).*

## 1. The headline

1. **MIA's identity is already built and approved in its essentials:** glass over dark depth (DEC-0183), Aquatic the
   default theme, one cyan accent that means MIA, meaning colours kept apart, gold allowed and legendary orange for
   rewards (DEC-0186), each app's own atmosphere colour (DEC-0187), five glass surface tiers clamped in code, ten
   themes as data (DEC-0136), seven colour schemes and layouts (DEC-0184), the orb's presence from real activity
   (`core/orb_state.py`). **Prompt 11 keeps it and completes it**, rather than redesigning.
2. **One design system for every device** (DEC-0234): values live only in tokens (`web/tokens.css`, set by
   `core/themes.py`); the desktop, the phone and the glasses all render MIA's web screens, so they share it by
   construction; the glasses and future wearables use a reduced token set.
3. **The identity survives without its effects** (DEC-0235): the orb's shape, the one accent, the mono technical
   labels and the layered layout make her recognisable in high contrast, monochrome, light, low power and with motion
   off.
4. **Themes and personalisation are data, never code** (DEC-0236), as the **Theme Studio** already does
   (`web/studio.html`, `core/themes.py`, `core/theme_actions.py`): he builds, saves (up to 12), exports and imports
   his own themes as files (`mia-theme/1`), each checked (text at 4.5:1, an accent that can't read as a warning, values
   that can't break out of CSS), with his own pictures as backdrops and a chime set. What's added: the orb's style,
   a palette suggested from one of his pictures, and a Light theme.
5. **The orb is one component with fourteen states**, each shown by shape, label and colour as well as motion
   (DEC-0237).
6. **Motion has three speeds and two kinds**: meaningful (state changes, always shown, reduced to a fade when asked)
   and decorative (off at light effects, on battery, while models are busy) (DEC-0238).
7. **Spatial is a way to see the same capabilities**, never a separate app: the Nexus stays Living Worlds' (DEC-0153);
   portals open the same screens; every spatial feature is labelled by the hardware it needs (DEC-0239).
8. **Audio identity is small and local**: a handful of quiet sounds, alarms unmistakable, every sound off with one
   setting (DEC-0240).

## 2. The audit (verified in the code and docs, 2026-11-17)

| Element | Exists | Kind |
|---|---|---|
| Tokens | `web/tokens.css` (282 lines): colour triplets, panels, ink, accent, meaning colours, type scale, radii, motion | **implemented** |
| Themes | `core/themes.py`: Stark, Y2K Cyber, Cyberpunk, Glass, Aquatic (default), Nebula, Evergreen, Aurelia, Glacial, Eclipse | **implemented** |
| Surface tiers | primary, secondary, floating, deep, interactive, each clamped (`TIER_RANGES`) | **implemented** |
| Colour schemes | cyan, turquoise, violet, gold, champagne, ice, rose (`core/appearance.py`) | **implemented** |
| Layout and effects | density comfortable/compact; sidebar full/icons; effects auto/full/light/none | **implemented** |
| Icons | `web/icons.js` (one line set) | **implemented** |
| Type | system fonts (Segoe UI Variable on Windows), a mono face for labels; no web fonts (offline) | **implemented** |
| Orb | presence states thinking, working, council, success, warning, notification, listening (`core/orb_state.py`, `shell.js`) | **implemented** (part) |
| Meaning colours | ok green, attention amber, bad red, win gold, rarities, checked by `tests/test_appearance.py` | **implemented** |
| Per-app atmosphere | `--mod-*` tokens (DEC-0187) | **approved**, partly applied |
| Backdrops | a theme's picture behind pages, one of his own pictures included (DEC-0136, `core/art_studio.py`) | **implemented** |
| Theme Studio | preview, tweak, save his own themes (up to 12), export and import (`mia-theme/1`), contrast and warning-colour checks, approved and undoable (`theme.save`, `theme.import`, `theme.delete`) | **implemented** |
| Photos | `web/img/` (17), never anything personal | **implemented** |
| Nexus, Living Worlds 3D | `web/nexus3d.js` (three-dimensional room) | **implemented** |
| Glasses | `web/glasses.js`: a 600×600 composition, black see-through, the orb, menu and Nexus (DEC-0153) | **implemented** |
| Phone | the same web pages, bottom bar under 720 px | **implemented** |
| Sounds | win chimes, a quest-complete arpeggio, a level fanfare made in the browser (`web/sound.js`), voiced per theme (`SOUND_SETS`: classic, bubbly, synth...), one on/off setting (`sound.on`) | **implemented** for wins; no listening, approval or error sounds |
| High contrast | an accessibility setting that overrides every theme (`[data-contrast="high"]` in `web/tokens.css`, `core/accessibility.py`) | **implemented** |
| Light theme | none | **missing** |
| Muse's identity and design-system drafts | `docs/design/MIA_VISUAL_IDENTITY.md`, `MIA_DESIGN_SYSTEM.md`, the Stark interface, the mobile concept | **documented**, partly approved |
| Remaining literal colours | style sheets outside tokens (`tools/css_colours.py` baseline) | **inconsistency**, shrinking |

**Recognisably MIA today:** the orb, the cyan accent on graphite and glass, the mono labels, the area dashboards, the
approval card. **Inconsistent:** the Qt classic screens (their own styling); some literal colours; the orb's states
incomplete (speaking, approval, error, muted have no state of their own).

## 3. Creative direction, reconciled

Zac's inspirations (Stark's holographic interfaces, JARVIS and EDITH, cyberpunk, Y2K and MySpace-era customisation,
cyber graffiti, liquid motion, spatial HUDs) and the restraint already approved ("never a costume", glow only where it
means something) are both kept by **splitting identity from expression**: the **Signature** (Aquatic glass, cyan)
is calm and precise everywhere by default; the **expressive** directions are themes and personalisation he chooses
(Y2K Cyber, Cyberpunk exist; Graffiti and Neon are proposed), all on the same tokens and rules.
`MIA_OS_CREATIVE_DIRECTION.md`.

## 4. Decisions (records in `MIA_OS_VISUAL_TECHNOLOGY_EVALUATION.md` §2)

| DEC | Decision | Status |
|---|---|---|
| DEC-0234 | One design system: values only in tokens, shared by every device's rendering | PROPOSED |
| DEC-0235 | The identity holds without colour, transparency or motion | PROPOSED |
| DEC-0236 | Themes and personalisation are validated data, never code | PROPOSED |
| DEC-0237 | The orb: one component, fourteen states, never shown by motion alone | PROPOSED |
| DEC-0238 | Motion: three speeds; meaningful and decorative kept apart; budgets | PROPOSED |
| DEC-0239 | Spatial interfaces are views of the same capabilities, labelled by hardware | PROPOSED |
| DEC-0240 | A small local audio identity, every sound off with one setting | PROPOSED |

## 5. Questions for Zac

`MIA_OS_VISUAL_OPEN_QUESTIONS.md`: Q-83 (the Theme Studio starting from one of your pictures), Q-84 (which
interface sounds on by default), Q-85 (add a Light theme now, Graffiti and Neon later), Q-86 (Zeta
Astralis prototyped on a small Android phone first).

## 6. Boundaries

Prompt 12 the devices and their links; Prompt 13 a theme's security in full; Prompt 16 the order of building. Muse
refines every value named here.

## 7. Sources

The repository and `docs/design/`, read 2026-11-17; DEC-0017, 0018, 0023, 0136, 0153, 0183, 0184, 0186, 0187;
Prompt 10. Technology sources in the technology evaluation.

## 8. What it means for him

MIA keeps looking like she does now, and gets more of herself: an orb that always says what she's doing, a light
theme for daytime beside the high-contrast setting he has, a few quiet sounds he can turn off, and the Theme Studio he already has,
able to start from one of his pictures.

## 9. The documents

`MIA_OS_CREATIVE_DIRECTION.md`, `MIA_OS_DESIGN_SYSTEM_ARCHITECTURE.md`, `MIA_OS_COLOR_AND_THEME_TOKENS.md`,
`MIA_OS_TYPOGRAPHY_AND_INFORMATION_HIERARCHY.md`, `MIA_OS_SHAPE_SURFACE_AND_DEPTH_SYSTEM.md`,
`MIA_OS_ICONOGRAPHY_AND_SYMBOLS.md`, `MIA_OS_ORB_VISUAL_AND_BEHAVIOR_SPECIFICATION.md`,
`MIA_OS_MOTION_AND_ANIMATION_SYSTEM.md`, `MIA_OS_THEME_AND_SKIN_ARCHITECTURE.md`, `MIA_OS_PERSONALIZATION_SYSTEM.md`,
`MIA_OS_DESKTOP_VISUAL_LANGUAGE.md`, `MIA_OS_MOBILE_VISUAL_LANGUAGE.md`,
`MIA_OS_WEARABLE_AND_SMART_GLASSES_VISUAL_LANGUAGE.md`, `MIA_OS_SPATIAL_INTERFACE_AND_PORTAL_ARCHITECTURE.md`,
`MIA_OS_ZETA_ASTRALIS_INTERFACE_CONCEPT.md`, `MIA_OS_AUDIO_IDENTITY.md`, `MIA_OS_APPLICATION_VISUAL_INTEGRATION.md`,
`MIA_OS_VISUAL_ACCESSIBILITY_STANDARDS.md`, `MIA_OS_RENDERING_AND_PERFORMANCE_STRATEGY.md`,
`MIA_OS_VISUAL_DESIGN_SPECIFICATIONS.md`, `MIA_OS_VISUAL_ARCHITECTURE_DIAGRAMS.md`,
`MIA_OS_VISUAL_TECHNOLOGY_EVALUATION.md`, `MIA_OS_VISUAL_ACCEPTANCE_CRITERIA.md`, `MIA_OS_VISUAL_OPEN_QUESTIONS.md`.

## Across devices (Prompt 12, 2026-11-18)

The household display and Zeta Astralis are endpoints rendering MIA's screens in the ambient and compact layouts (`MIA_OS_DEVICE_CLASS_AND_RUNTIME_ARCHITECTURE.md`).
