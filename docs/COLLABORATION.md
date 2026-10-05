# MIA Collaboration: how the team works

*The shared whiteboard for Zac, ChatGPT, Muse and Claude (started
2026-10-05). Every AI reads this first. The repo is the shared memory:
no AI talks to another directly, they all read and write these files.*

## Start here (every AI, every session)

1. Read **`docs/CURRENT_STATE.md`**: where the project is right now.
2. Check **`docs/QUESTIONS.md`** for questions addressed to you.
3. Check **`docs/HANDOFFS/`** for anything new addressed to you.
4. Check **`docs/DECISIONS.md`** before proposing anything: don't redo
   or contradict an approved decision without proposing a new one that
   supersedes it.
5. Run every proposal through the 10-question guardrail (below).

## Who does what

| Who | Role | Owns |
|---|---|---|
| **Zac** | Owner and director | Final say on direction, scope, priorities, personal data and every decision. Only Zac marks a decision APPROVED. |
| **ChatGPT** | Vision and systems integration | MIA's original vision and coherence, cross-module thinking, architecture review, "are we still building MIA?" checks. |
| **Muse** (also called Rocky) | Experience and interface | UX, UI, visual language, interaction design for the desktop, phone and Meta glasses. |
| **Claude** (Claude Code) | Engineering and engine | The repo's reality: architecture, services, data, APIs, implementation, tests. Keeps `CURRENT_STATE.md` up to date. |

Sign everything with your name (`zac`, `chatgpt`, `muse`, `claude`),
never just "AI". The history of who proposed, reviewed and approved
what is part of the project.

## The files

| File | What it holds | Who writes it |
|---|---|---|
| `docs/CURRENT_STATE.md` | The phase, what each of us is working on, what's blocked, recent changes, open items. Short: a two-minute read. | Claude rewrites it at the end of each session; anyone can propose edits. |
| `docs/DECISIONS.md` | Every decision, `DEC-0001` onward, with its status and who proposed, reviewed and approved it. Decisions never disappear: they become SUPERSEDED or REJECTED. | Anyone proposes; only Zac approves. |
| `docs/QUESTIONS.md` | Questions from one of us to another, `Q-0001` onward. The answer stays with the question. | Anyone asks; the person asked answers. |
| `docs/HANDOFFS/` | Bigger pieces of work passed between us, one file each: `H-0001_from-to_subject.md`. | The sender. |
| `docs/ROADMAP.md` | The engineering record: what was built, why, and how it was verified. | Claude. |
| `docs/NEXT_SESSION.md` | Zac's hands-on steps and Claude's build queue. | Claude. |
| `docs/ENGINE_PHASE1_PLAN.md`, `docs/schema/` | The engine contract: Life State v2, the schema, a placeholder example. | Claude. |

## How to write to the hub

- **Claude** commits directly (every commit is pushed).
- **ChatGPT and Muse**: if you can open a pull request or commit, do it
  and touch only the files above. If you can't, write your entry in the
  formats below and Zac pastes it in, or gives it to Claude to file.
- Keep IDs unique: take the next free number in the file.
- Link things by ID ("see DEC-0006, Q-0004").

### Formats

```
### DEC-0000: <title>
- Status: PROPOSED | DISCUSSION | REVIEW | APPROVED | IMPLEMENTED | REJECTED | SUPERSEDED (by DEC-xxxx) | ARCHIVED
- Proposed by: <name>, <date> · Reviewed by: <names> · Approved by: zac, <date>
- Decision: <one or two sentences>
- Why: <the reason>
- Related: <IDs, files>
```

```
### Q-0000: <short question> (<from> → <to>)
- Asked: <date> · Status: OPEN | ANSWERED | CLOSED
- Question: <full question with enough context to answer it alone>
- Answer (<name>, <date>): <answer>
```

Handoffs (one file in `docs/HANDOFFS/`): From, To, Date, Subject,
Context, What's needed, Constraints, Acceptance criteria, Related IDs.

## Working through the hub (Zac, 2026-10-05)

Muse and Claude talk through the repo as much as possible: questions in
`QUESTIONS.md`, work in `HANDOFFS/`, decisions in `DECISIONS.md`. Zac
reads `CURRENT_STATE.md` to see where everyone is and only steps in to
decide, steer or approve. When you finish something another member is
waiting on, say so in the handoff (a "Response" section) and in
`CURRENT_STATE.md`'s recent changes, so the next reader sees it first.

## Ground rules

1. **Zac stays in the loop.** The hub replaces copying and pasting, not
   Zac's judgement. Nothing is approved until Zac approves it.
2. **No personal data in the repo, ever:** no real names beyond first
   names already used, addresses, loans, lenders, amounts, accounts,
   passwords or keys. Use placeholders ("Robin", "Rental A", "Lender A").
   Real data enters through MIA and stays on Zac's device (DEC-0002).
3. **The repo is MIA; surfaces consume it** (DEC-0005). A design shows
   what `/api/state` provides, and anything else is marked PLANNED.
4. **Facts come from code; the model phrases and proposes** (DEC-0004).
5. **Never silently override a decision.** Propose a new one that
   supersedes it.

## The guardrail (DEC-0008): ask before every proposal

1. Does MIA already support it?  2. If so, where?  3. If not, is it
really missing, or just not shown yet?  4. Does it belong in the engine
or only the UI?  5. Can it be added without duplicating an existing
system?  6. Does it belong in Life State?  7. Does it create a life
event?  8. Does it create or use links?  9. Should `/api/state` expose
it?  10. Is it REAL, DERIVED, SIMULATED, STATIC or PLANNED?
