# <App>: design specification

*Template (H-0087). Copy it to `docs/design/applications/<app>.md`. Grounded in what MIA actually does: every
screen names its data source and every button its action kind. Status at the top: brief (what's needed) → spec
(Muse's design) → built → accepted (Zac, after real use).*

**Status:** brief · **Maturity now:** <1–5> · **Target:** <level> · **Owner:** Muse (design), Claude Code (build)

1. **Purpose and intended experience**: what it's for, and how it should feel to use, in a few sentences.
2. **Existing functionality**: what works today (engine and screens), with the files.
3. **Navigation hierarchy**: the home view, its modes and sub-pages, and how you get there.
4. **Screen and page inventory**: every screen, with its data (`MIA.*` call, API route).
5. **Annotated visual mockups**: from approved concepts (`docs/design/visual_library/` ids).
6. **Layout specifications**: per screen: regions, sizes, surfaces (design system §4).
7. **Component definitions**: which shared components, and anything new (proposed into the design system first).
8. **Interaction behavior**: every action (its action kind), its confirm and undo, what moves and why.
9. **All relevant states**: empty, loading, active, completed, error, offline, child account, demo.
10. **Voice and assistant integration**: what can be said (tools, quick commands), what she says back, her orb.
11. **Memory and contextual awareness**: what she remembers and uses (memories, life events, links, the life state).
12. **Mission and gamification integration**: missions, XP, skills, streaks, rewards it feeds.
13. **Data and API dependencies**: engine files, routes, action kinds; anything the engine must add (built in core
    first, never in `web/`).
14. **Desktop presentation**
15. **Phone presentation**
16. **Glasses presentation** (where it applies)
17. **Accessibility**: contrast, focus, screen reader, text size, voice-only use.
18. **Acceptance criteria**: testable statements, including real-use ones (level 5).
