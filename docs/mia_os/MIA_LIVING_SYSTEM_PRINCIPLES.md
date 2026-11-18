# MIA: living system principles (Prompt 21, deliverable 1)

*Claude (Opus), 2026-11-18. Version 1.1, revised after independent reviews by Fable and Codex
(`MIA_LIVING_SYSTEM_REVIEW.md`). Planning only. Prompt 21 asks whether the architecture makes MIA one coherent,
continuously evolving intelligence, not a set of capable modules. This document states the principles every subsystem
is measured against. `MIA_LIVING_SYSTEM_GAP_ANALYSIS.md` applies them to every item the prompt names, with the
evidence from the documents and the code. The four companion documents are the cognitive architecture, memory and
learning, the runtime contracts, and the gap analysis. Proposed decisions: DEC-0280 to 0286, each waiting for Zac.*

> Two principles came from the reviews: build the small join, not the large framework (P13), and every addition is
> sized against one person's system (P14).

## 1. Where this starts

Prompt 20 (`MIA_OS_LIVING_SYSTEM.md`, DEC-0173, approved) already adopted the Living System doctrine as invariants
over what exists:
- every process has an improvement loop (96 in `docs/LOOPS.md`);
- facts are worked out in code and the model only phrases them;
- the history is never rewritten;
- a stop holds everything.

Prompts 07, 08, 09 and 12 placed memory, autonomy, self-awareness and devices. Prompt 21 doesn't replace any of that.
It checks the **joins**. The review of 2026-11-18 showed that careful parts fail where they meet:
- undo against the stop;
- a grant against a kind that covers many things;
- erase against the writer's safety copy.

The principles below are written to catch those joins.

## 2. The principles

| # | Principle | What it rules out | Where it's held |
|---|---|---|---|
| P1 | **One vocabulary, shared joins.** A turn, a daily check and a job use the same named stages where they apply, and meet at the same joins (the trust label, the gate, the action contract, the history, a trace id). Not one engine: controllers keep their own loops (DEC-0246) | a proactive path with its own rules beside the turn's; forcing everything through one pipeline | `MIA_COGNITIVE_ARCHITECTURE.md` |
| P2 | **One contract per kind of thing.** One capability contract for every tool and action; one record reference (`kind:id`) registry; one provider interface for every model call | a fifth registry; vision or embeddings calling a model server directly | `MIA_UNIVERSAL_RUNTIME_CONTRACTS.md` |
| P3 | **Facts in code, words from the model.** A number, a date, a count, a size or a decision about what may happen comes from code or a record | a model's arithmetic or a model's yes | DEC-0206, `core/build_calcs.py`, the specialists' worksheets |
| P4 | **Every belief says how it's known.** A memory, a link or a statement about herself carries its source, how it was learned (said, observed, inferred, computed), when, and for his memories when he confirmed it and when it holds | "MIA knows" without saying from what | `MIA_MEMORY_AND_LEARNING_ARCHITECTURE.md` §2 |
| P5 | **Nothing learned changes behaviour without a gate.** Each kind of learning has its own evaluation before it's used, and a way back | a learned weight or a merged change that nobody checked | DEC-0212, the lab, Claude's inspection |
| P6 | **Initiative is not autonomy.** MIA notices, ranks and decides how to speak up (notify, recommend, ask, or act on a grant). What she may change is decided only by the tiers and his grants | a model's judgement that something "is fine to just do" | DEC-0181, DEC-0215, DEC-0217 |
| P7 | **Every change is traceable end to end.** An input, the turn or job it started, its tool calls and proposals, the records written and the outcome share one trace id | an outcome that can't be tied to what caused it | DEC-0280 |
| P8 | **Safeguards are tested in pairs.** A new safeguard lists every other mechanism touching the same file, record or reply (undo, history, the writer's safety copy, sync, another process) and is tested against each | a stop that an undo lifts; an erase that a safety copy undoes | the knowledge entry of 2026-11-18; `tests/test_authority_review.py` |
| P9 | **Time is explicit.** New moments carry their zone; "tomorrow", "this weekend" and "in a month" are worked out by one clock service | 168 files in `core/` each asking the machine for a naive local time (counted 2026-11-18) | DEC-0284 |
| P10 | **Designed for decades.** Formats change additively or by versioned migration; ids never change; models, providers, devices and the OS are replaceable without touching his data | a format, a model or a device he can't leave | DEC-0206, DEC-0267 |
| P11 | **One name for one thing.** Two mechanisms for one responsibility are joined or one is retired, on a plan, never silently left | three task engines and two undo logs with no plan | the gap analysis §3 |
| P12 | **Preserve what works.** This is an architectural completion, not a rewrite: every addition names the existing code it extends | a parallel cognitive engine beside the one that runs | Prompt 21 §10, Prompt 17b §2 |
| P13 | **The small join, not the large framework.** Where a gap is a missing link between two working parts, the link is built; a general framework waits until three uses need it | a compensation framework where restoring the before-images is a few lines | the reviews, 2026-11-18 |
| P14 | **Sized for one person.** An addition says what it costs to run and keep for years, and is deferred when the plain way works | a sync clock in a two-device star | the reviews, 2026-11-18 |

## 3. How each item is judged

Every item Prompt 21 names gets exactly one class, with its evidence:
- **adequately covered**: designed and built, with tests;
- **covered but insufficiently specified**: built, but its contract isn't written down;
- **partially addressed**;
- **missing**;
- **conflicting**: a document and the code, or two decisions, disagree;
- **requires research**.

A requirement is added only where something is missing or under-specified. Covered items aren't restated to look
complete. No recommendation becomes a decision here: each new decision is proposed and waits for Zac.

## 4. What "complete" means here

For every major subsystem, the gap analysis gives the ten things Prompt 21 §9 asks for:
- purpose, responsibilities, dependencies and interfaces;
- persistent data, security boundary and failure behaviour;
- performance, testing strategy and acceptance criteria.

It also gives end-to-end scenarios that cross subsystems. A subsystem whose entries are all filled in, whose
acceptance test exists, and whose joins with its neighbours are tested in pairs (P8) is complete. Anything less is
listed as a gap with a work package.
