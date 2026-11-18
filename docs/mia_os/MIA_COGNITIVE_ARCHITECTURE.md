# MIA: the cognitive architecture and runtime (Prompt 21, deliverable 2)

*Claude (Opus), 2026-11-18. Version 1.1, revised after independent reviews by Fable and Codex
(`MIA_LIVING_SYSTEM_REVIEW.md`). Planning only. It names what exists at each stage and the smallest change that ties
them together. Proposed decisions:
- DEC-0280: a trace id through the stages;
- DEC-0284: the clock service.*

## 1. One vocabulary, shared joins

Today a conversation turn is a pipeline:
- `core/assistant_turn.py`: the safety floor and the stop first;
- the message sorted by kind (`core/message_kind.py`);
- context assembled in code (`core/context_assembler.py`);
- the model plans and phrases;
- changes through the action contract (`core/actions.py`).

Proactive work runs on the scheduler and daily checks (`core/background_jobs.py`), offers candidates to the
communication gate (`core/communication_gate.py`), and asks `core/grants.require` before it changes anything.

**The architecture.** These are **one vocabulary of stages, not one engine**. A turn, a daily check and a job each use
the stages that apply to them, through the same shared joins:
- the trust label set at intake;
- the gate for anything unprompted;
- the action contract for any change;
- the history for what happened;
- a **trace id** that links them (DEC-0280).

Nothing is forced through a ten-stage runtime:
- **Controllers keep their own loops and safety** (DEC-0246): the greenhouse node acts on its own readings, and MIA
  only reads its snapshots.
- **The event bus stays synchronous and in-process** (CLAUDE.md).
- **No threading is added for the sake of the shape.**

```
Asked (he says or presses) ─┐                                                 ┌─► said / shown
Noticed (a schedule, a reading, a record changed) ─┴─► stages below, as they apply ─┴─► the history (one trace id)
```

## 2. The stages and their joins

| # | Stage | Lives in (exists) | The join, and what's added |
|---|---|---|---|
| 1 | **Intake** | `assistant_turn.run_assistant_turn` (web, phone, voice); the desktop's chats through `instant_answer` and `ChatWorker` (the same request logic, but not the traced turn wrapper); the scheduler; the UAL's capture; the inbox; sensors | a **trace id** made here, in memory only (a private turn is never traced, as today); the desktop's chats wrapped in the same traced turn |
| 2 | **Classify and validate** | `safety_floor`, `stop`, `message_kind.sort`, `quick_commands`, `question_plans`, `browser_safety.untrusted()` | outside text is marked data where it enters and stays so (DEC-0249, WP-03); nothing new |
| 3 | **Attend** | the gate (learned pace, focus, flow), `presence`, `relevance`, `homeostasis` | nothing now; one attention policy across them is deferred past R1 (§5) |
| 4 | **Assemble context** | `context_assembler` v2, `self_knowledge`, recall, "What I Used" | the epistemic fields shown with each record where a store has them (memory §2) |
| 5 | **Plan** | the tool loop, `question_plans`, the specialists' worksheets (the model picks calculators, code computes), `step_plans` | routing in code (DEC-0208, approved, unbuilt) with the fallback chain |
| 6 | **Authorise** | `ActionCenter.propose`, `grants.require`, `kind_grants`, `spoken_approval`, `stop` | nothing (its joins fixed and tested on 2026-11-18) |
| 7 | **Execute** | each kind's `execute`; `runs.py` for multi-step work | a failure puts back what it had written (fixed now, 2026-11-18); deadlines for device and outside work (contracts §2) |
| 8 | **Verify** | plans re-check before each step | a generic read-back after a change (DEC-0218, approved): what it touched is re-read (contracts §2) |
| 9 | **Record** | `life_events`, `change_history`, `turn_trace`, `security_log`, `agent_activity` | the trace id in each; the prompt template's version in the turn trace |
| 10 | **Learn** | corrections, 96 loops, `response_style`, the gate's pace, life notes, `dev_knowledge`, taught skills | each lesson with a named state (memory §4) |

## 3. Long-running work

`core/runs.py` gives multi-step work its record: start, step, wait, finish and `recover()` after a restart. The stop
holds a run between steps, and `stop.stop_now` also ends speech, a running skill and browser tasks. It stays the one
record of work that outlives a turn (DEC-0214). The engines that write their progress there:
- plans;
- taught skills;
- browser routines;
- teams;
- workflows.

A run belongs to the device that runs it and doesn't sync (fixed now: a run synced to the phone was marked stopped by
the phone's start-up recovery while it still ran on the PC).

## 4. Choosing tools, agents and models

| Choice | Today | Architecture |
|---|---|---|
| Tool | domains, trigger words, the meaning matcher | unchanged |
| Specialist | `specialists.py`, the roster | unchanged |
| Model | the configured model; the specialists' bench choices | routing by task class from measurements (DEC-0208), the fallback chain (REQ-AI-013), a conversation first in the GPU queue (DEC-0204) |
| Provider | `LLMBackend` for generate and chat; **at least ten modules** call the model server's API directly (`meaning`, `recall_index`, `sight`, `chronicle_issue`, `creation_maker`, `dev_knowledge`, `mia_coder`, `paths`, `work_review`, `self_repair`), most with its address written in | the backend gains `embed` and `see`. The runtime's own calls move onto it (`meaning`, `recall_index`, `sight`, `paths`, `creation_maker`) and the address comes from one setting everywhere. The development tools (`mia_coder`, `work_review`, `dev_knowledge`) may keep their own client but read the same setting |

## 5. Goals and arbitration (deferred past R1)

Intents with their chain, why-links, missions, paths and standing directions all exist. When two pull different ways,
the rule is the same as for every belief: **MIA never settles a conflict between two things he holds**. She puts it to
him once, with both named. A single attention policy and a ranking of his goals across areas are deferred past R1:
- the gate, presence and homeostasis work today;
- a unified ranker is the kind of machinery Prompt 21 warns against building before it's needed.

## 6. Time (DEC-0284, proposed)

No module uses time zones; 168 files in `core/` call the machine's naive local time and 246 use `datetime.now()` or
`date.today()` (counted with grep on 2026-11-18).

**The architecture:** one clock service, `core/clock.py` (to be written). It gives:
- now, in his zone from `core/region.py`;
- today and the week as he means them;
- relative times ("tomorrow morning", "in two weeks", "the first Saturday of March");
- recurrences ("every second Tuesday"), worked out in code, never by the model.

New code uses it; existing modules move as they're touched. Tests freeze it, so a test can't fail because the suite
crossed midnight (the glasses test, 2026-11-18). The gate already takes a `clock`, which is the pattern.

## 7. Failure behaviour

| Stage fails | What happens |
|---|---|
| Intake (a channel breaks) | the others go on; the channel says so |
| Classify (the model is away) | the crisis, the stop and quick commands are sorted in code; anything else is answered from records with "my model isn't answering" |
| Attend (the gate can't read its state) | nothing unprompted goes out; replies and alarms still do |
| Assemble (a store unreadable) | the answer names what it couldn't read (REQ-FUN-221) |
| Plan (no model) | the fallback chain, then code-only answers |
| Authorise (grants unreadable) | fails closed: a card, never a change (DEC-0254) |
| Execute (an error) | what it had written is put back; said plainly |
| Verify (the read-back disagrees) | not said as done; its Undo offered |
| Record (a log can't be written) | the change stands; the gap is logged where it can be |
| Learn (a lesson can't be kept) | nothing is adopted |

## 8. Performance

| Measure | Target | Measured by |
|---|---|---|
| A spoken question to the first word | under 3 s on the PC, everyday model | `turn_trace` |
| Context assembly | under 300 ms | `turn_trace` |
| A noticed signal to its candidate at the gate | under 2 s | the scheduler's timing |

## 9. What this changes, in order

1. The trace id through the turn, proposals, the history and the change history; the template version in the turn
   trace (DEC-0280).
2. The desktop's chats in the traced turn.
3. The model server's address from one setting; the runtime's model calls onto the backend's `embed` and `see`.
4. The clock service for new code (DEC-0284).
5. The generic read-back (DEC-0218).
6. Routing in code and the GPU queue (DEC-0208, DEC-0204), already approved.
