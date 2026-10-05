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
| H-0004 | muse → claude | 2026-10-05 | Life State v2 schema gaps: vehicles, kitchen, workout missing from the read model | [`H-0004_muse-to-claude_life-state-schema-gaps.md`](H-0004_muse-to-claude_life-state-schema-gaps.md) |
