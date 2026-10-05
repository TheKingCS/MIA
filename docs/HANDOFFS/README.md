# Handoffs

*Bigger pieces of work passed between Zac, ChatGPT, Muse and Claude
(rules: `docs/COLLABORATION.md`). One file each, named
`H-0000_from-to-to_subject.md`. Never put real personal data in a
handoff: use placeholders.*

## Template

```
# H-0000: <subject>
- From: <name> · To: <names> · Date: <date>
- Related: <DEC-, Q-, H- IDs, files>

## Context
## What's needed
## Constraints
## Acceptance criteria
```

## Index

| ID | From → To | Date | Subject | Where |
|---|---|---|---|---|
| H-0001 | chatgpt → claude, muse | 2026-10 | System architecture handoff: engine first, surfaces consume it | Not in the repo (relayed by Zac); its outcome is DEC-0003, DEC-0005, DEC-0006 |
| H-0002 | muse → claude | 2026-10-05 | MIA Engine Kickoff Spec | Not in the repo: it contained real personal seed data (DEC-0002). Answered by `docs/ENGINE_PHASE1_PLAN.md` |
| H-0003 | claude → muse | 2026-10-05 | Where MIA is, and how design connects to the engine | [`H-0003_claude-to-muse_where-mia-is.md`](H-0003_claude-to-muse_where-mia-is.md) |
| H-0004 | muse → claude | 2026-10-05 | Life State v2 schema gaps: vehicles, kitchen, workout missing from the read model | [`H-0004_muse-to-claude_life-state-schema-gaps.md`](H-0004_muse-to-claude_life-state-schema-gaps.md) (DONE, claude 2026-10-05) |
| H-0005 | claude → zac, muse, chatgpt | 2026-10-05 | Where MIA is, what she needs, and a Phase 2 proposal (web front end) | [`H-0005_claude-to-all_where-mia-is-and-phase-2.md`](H-0005_claude-to-all_where-mia-is-and-phase-2.md) |
| H-0006 | muse → zac, claude, chatgpt | 2026-10-05 | Review of H-0005 and the Phase 2 proposal | [`H-0006_muse-to-all_phase-2-review.md`](H-0006_muse-to-all_phase-2-review.md) |
| H-0007 | claude → muse (cc zac, chatgpt) | 2026-10-05 | The foundation is ready: build MIA's Home on it | [`H-0007_claude-to-muse_foundation-ready-build-home.md`](H-0007_claude-to-muse_foundation-ready-build-home.md) |
| H-0008 | claude → zac, muse, chatgpt | 2026-10-05 | The glasses platform (Meta Ray-Ban Display) and how MIA gets there | [`H-0008_claude-to-all_glasses-platform-and-plan.md`](H-0008_claude-to-all_glasses-platform-and-plan.md) |
| H-0009 | muse → claude (cc zac, chatgpt) | 2026-10-05 | Home build accepted — plan, Life State mapping, questions | [`H-0009_muse-to-claude_home-build-accepted.md`](H-0009_muse-to-claude_home-build-accepted.md) |
| H-0010 | chatgpt → claude (cc muse, zac) | 2026-10-05 | Answers to current MIA questions (Q-0001, Q-0002, Q-0006, Q-0003/Q-0011) + architectural verdict | [`H-0010_chatgpt-to-claude_answers-to-current-questions.md`](H-0010_chatgpt-to-claude_answers-to-current-questions.md) |
| H-0011 | chatgpt → zac, claude, muse | 2026-10-05 | Decisions on Q-0001 (non-punitive), Q-0002 (child safety escalation), DEC-0014 extension | [`H-0011_chatgpt-decisions_q0001-q0002-dec0014.md`](H-0011_chatgpt-decisions_q0001-q0002-dec0014.md) |
| H-0012 | muse → claude (cc zac, chatgpt) | 2026-10-05 | Design review: DEC-0016 and the glasses composition (response to H-0008) | [`H-0012_muse-to-claude_glasses-design-review.md`](H-0012_muse-to-claude_glasses-design-review.md) |
| H-0013 | muse → claude (cc zac, chatgpt) | 2026-10-05 | Engine data gaps found building the concept screens (missions, skill XP, character level, rarity) | [`H-0013_muse-to-claude_engine-gaps-concept-screens.md`](H-0013_muse-to-claude_engine-gaps-concept-screens.md) |
| H-0014 | claude → muse (cc zac, chatgpt) | 2026-10-05 | The public preview (GitHub Pages) is set up; notes on Home, Missions, Skills | [`H-0014_claude-to-muse_public-preview-and-review.md`](H-0014_claude-to-muse_public-preview-and-review.md) |
