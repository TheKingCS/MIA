# H-0087: MIA Experience Maturity & Visual Identity Initiative

- From: zac, with chatgpt · To: claude, muse (Claude Design), codex · Date: 2026-11-07
- Related: H-0088 (Claude's reply), DEC-0113 (proposed), DEC-0023, DEC-0017, `docs/EXPERIENCE_MATURITY_AUDIT.md`
- Note: Zac and ChatGPT numbered this H-0084; that number was already used (the benchmark-ladder feasibility), so it's
  filed as H-0087.

## Context (summary of the handoff as received)

MIA's emphasis moves from capability to **finished experience**: "MIA Experience Maturity, Phase 1", with three
objectives: (1) MIA's definitive visual identity and design system; (2) Workout and Kitchen as polished flagship
apps; (3) a repeatable design → build → test → refine process for every app. Build on the existing architecture;
don't replace working systems.

## What's needed

1. **Repository investigation** → `docs/EXPERIENCE_MATURITY_AUDIT.md`: every app, page, route, component, token,
   data connection, action, state, device; existing vs planned; inconsistencies; obsolete docs reconciled with the
   shared web architecture.
2. **Visual identity** (JARVIS and EDITH, holographic, cyan, engineering, spatial presence; refined and believable,
   not a generic cyberpunk dashboard; per-app atmospheres on one identity) → `docs/design/MIA_VISUAL_IDENTITY.md`,
   `docs/design/MIA_DESIGN_SYSTEM.md` (15 areas: color, type, spacing, surfaces, controls, icons, navigation, charts,
   motion, the orb, listening/thinking/speaking/attention, notifications, accessibility, light/dark, devices),
   then approved updates to `web/tokens.css` and shared components.
3. **ChatGPT + Claude visual collaboration**: ChatGPT as visual concept designer, Muse as interface designer, Claude
   Code as engineering, Codex/ChatGPT as review. Investigate an image pipeline (OpenAI Images API vs the ChatGPT
   app, which isn't callable by Claude; repo asset workflow; manifest); preferred now: a repository library
   `docs/design/visual_library/` with a manifest. Concepts are references, not production assets.
4. **Application design blueprint**: a standard 18-part spec per app → `docs/design/applications/`.
5. **Pilot one, Workout**; **pilot two, Kitchen** (target experiences as listed in the handoff; never present
   unverified repetition counts as verified performance).
6. **Sequence**: investigation → identity → shared shell → Workout → Kitchen → expansion.
7. **Maturity standard**: 1 Exists, 2 Functional, 3 Integrated, 4 Polished, 5 Trusted (a passing test suite alone
   isn't a finished experience); connect to her self-assessment.
8. **Constraints**: local-first, no unnecessary rewrites, preserve working functionality, one source of truth, no
   logic in presentation, reuse actions and APIs, desktop + phone + glasses, no unnecessary dependencies, document
   decisions, independent review and acceptance testing.

## Immediate assignments for Claude

Review against the repository; the audit; the collaboration proposal; the initial concept exploration plan; the
design-system specification; the Workout and Kitchen briefs; dependencies, risks and decisions for Zac. **Present
the approach before any large implementation.**

## Final objective (Zac's words)

"We are building MIA: a persistent, intelligent, personalized companion that can help manage, understand and
participate in everyday life. Her interfaces should feel like natural extensions of her intelligence and
personality ... The next chapter is about making MIA feel as capable as she actually is."
