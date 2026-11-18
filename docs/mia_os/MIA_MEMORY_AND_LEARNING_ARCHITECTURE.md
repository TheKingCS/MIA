# MIA: memory and learning architecture (Prompt 21, deliverable 3)

*Claude (Opus), 2026-11-18. Version 1.1, revised after independent reviews by Fable and Codex
(`MIA_LIVING_SYSTEM_REVIEW.md`). Planning only. It extends two approved decisions:
- DEC-0210: his memory lives in his stores, with one recall index beside them;
- DEC-0212: three kinds of learning, each with its own gate.

Proposed decisions:
- DEC-0281: the existing epistemic contract carried onto the memory stores;
- DEC-0282: one learning lifecycle, with a list of what's never reset;
- DEC-0286: a retention registry.*

## 1. The seven kinds of memory, mapped to what exists

No new store is needed. Each kind has a home; what was missing is the contract between them.

| Kind | Where it lives (exists) | What's missing |
|---|---|---|
| **Working** | `conversation_state.py` (in memory), the assembled context, `runs.py` | a written limit (what's carried, what's dropped first); it stays on the device the conversation is on |
| **Episodic** | `life_events.py` (append-only), conversations, `change_history.py`, runs, the memory vault | nothing: adequate |
| **Semantic** | `user_memory_manager.py` ("keep it"), his records, links, the specialists' workbooks, the reference library | the epistemic declaration on the memory stores (§2) |
| **Procedural** | taught skills, browser routines, workflows, learning paths | one run record (`runs.py`, DEC-0214), already planned |
| **Prospective** | life notes (promises), alarms, the calendar, online reminders, maintenance triggers, memory callbacks | one "due" shape (§5) |
| **Autobiographical** | his: the chronicle, seasons, the saga, the history; hers: `dev_evolution.py`, `dev_history.py`, `dev_knowledge.py` | named, nothing built |
| **Environmental** | sensors, the homestead link, system health, connectivity, what he's working on, weather, World Intelligence | read where needed; no new store |

## 2. How every belief is known (DEC-0281, proposed)

**The conflict.** `MIA_OS_MEMORY_INFRASTRUCTURE.md` and REQ-INT-015 (Must, MVP, "Exists") say every memory carries
its provenance. The code says otherwise:
- `tests/test_living_system.py` keeps an `EPISTEMIC_BASELINE` of stores not yet declaring the contract, and it may
  only shrink;
- seven stores declare it;
- the baseline still exempts exactly the memory stores: `user_memories`, `life_notes`, `links`, `life_events`,
  `intents` and `recall`.

**The contract is the existing one**, kept as the test defines it:
- `source`: where it came from;
- `at`: when;
- `how`: said, observed, inferred or computed;
- `checked`: when it was checked, where that applies.

No separate confidence field is added. `how` already says how it's known, and a number would be a model's guess (P3).
Two additions, only where a decision needs them:

| Store | Added | Why |
|---|---|---|
| `user_memories`, `life_notes` | `confirmed_at` (when he said yes to it), `holds` (`from`, `until`: "I used to live in…" isn't a contradiction) | what he's told her is his to confirm and to date |
| any record whose `source` is outside (a page, a feed, an import) | a ceiling: it can't be `checked` without his yes or a second, independent source named | an outside source never becomes trusted by itself (DEC-0249) |

**The order of work, small and at the MVP gate** (REQ-INT-015 is Must · MVP, so it stays there):
1. `user_memories` and `life_notes`: the declaration and the two fields.
2. `life_events` and `links`: a declaration only (they already carry source and when: `life_events.py`, `Link`).

Then `intents`, then the rest of the baseline, one store at a time as each is touched. A record from before the change
reads as `source: unknown, how: said`; nothing is guessed.

## 3. Contradictions and entities

**What code can see (sync).** When the PC and the phone both changed the same field of the same record, sync's
three-way merge sees it (DEC-0243). That's the one contradiction code detects for certain. The approved rule is built
there:
- one value wins, by the rule sync uses today (`merge_json`'s `prefer_local`);
- the other is kept in the change history (30 days, sealed, reached by forgetting);
- one note names the record and the field, and never quotes a value of a sensitive class (DEC-0251).

**What only a model can see (memories).** A memory is free text (`UserMemory`: text, when, its conversation, a
category), so "the coop door is 30 in" and "it's 32 in" clash only to a reader. When she offers to keep a new memory,
the model may point out an older one it seems to contradict. He decides which holds, and the older one gets its
`until`. The model only proposes; nothing is overwritten (Should, R1).

**Entities.** `assistant_lookup.resolve_by_name` already resolves a name to a record within each type and is used by
twelve modules, `links.py` among them. What's missing is identity across types: "Sam", "my brother" and the contact
"Samuel R.". That's kept as a stated link (`links.py`) when he says they're one person. Nothing matches identities by
itself: a wrong merge of two people is worse than two records for one. Deferred past R1.

## 4. The learning lifecycle (DEC-0282, proposed)

Every lesson has one of these states and moves only by its gate:

| State | What it is | Gate to the next | Way back |
|---|---|---|---|
| **Temporary** | context for this turn | none: gone after the turn unless kept | — |
| **Inferred** | her own guess (the gate's pace from what he dismissed, his answer style, what he's working on) | its loop's evidence | that parameter's own reset (most exist: a topic resumed, a style cleared) |
| **Proposed** | offered to him (a life note, a memory, a possible contradiction) | **his yes** | he says no |
| **Verified** | kept and trusted | — | "that's wrong" makes it a correction |
| **Procedure** | a taught skill learned, a workflow published | his grant (DEC-0215) | taking back the grant |

**Inferred habits are shown and reset one at a time.** Each is listed in "What I've learned" with the evidence it
rests on, and its own reset. Where one is missing, it's added. A habit isn't always a stored value: the gate's pace is
worked out from the recent message log (`communication_gate.py`). So its reset is "clear the evidence for this topic",
never a rewrite of the log.

**Never reset by any of this** (the same rule as undo's `STICKY_KEYS`, 2026-11-18):
- his grants and standing yeses;
- a pause he asked for;
- the stop;
- anything he set himself.

A reset applies to her guesses only.

A dated "put my habits back to last Tuesday" was considered and **deferred**:
- it would need a second copy of the evidence that forgetting must also reach;
- some habits live in per-device logs that don't sync.

**Evaluation before adoption** (unchanged from DEC-0212): a fact needs his yes; a habit needs its loop's evidence and
is shown; a procedure needs his grant; her code goes through the lab with a reproducing test (DEC-0224), the suite and
Claude's pass; a model goes through the bench and Claude's inspection (DEC-0200, DEC-0266).

## 5. Prospective memory: one "due" shape

Each source of things for later answers `due(context, until)` with:
- `ref`, `what`, `when`;
- `why` (the promise, the schedule, the trigger);
- `action` (the suggested one, as Home's due items already carry).

Home, presence and the glasses' feed already read due items from several sources. The shape is written down so a new
source (a promise in a conversation) appears in all of them. Each source implements it as it's next touched.

## 6. Summary, forgetting and retention

| Process | Exists | Plan |
|---|---|---|
| Summarising weeks into seasons, seasons into the chronicle | `seasons.py`, `chronicle.py` | — |
| Weekly reflection | `journal_reflection.py` | — |
| Folding repeated facts into one memory | no | deferred past R1 (proposed folds only, never automatic) |
| Forgetting everywhere (REQ-SEC-027) | the index drops a removed record at once (2026-11-18) | the change history's copy and the devices on their next sync |
| Retention | ad hoc per store | the registry, below |

**Retention registry (DEC-0286, proposed).** One table in code lists every store with:
- its class (DEC-0251);
- how long it's kept;
- what happens at the end;
- **whether it syncs**: sync reads the list, so a store made for one device can't sync by mistake. Four already had
  (what's noted on the PC, the recall index, runs, turn traces; fixed 2026-11-18).

A test fails on a store missing from it.

## 7. Retrieval

DEC-0210's design (sqlite-vec, chunks, history-driven refresh) stays the R1 target. The first slice, a sealed JSON
index of four sources, stays until it passes 50,000 entries or recall needs files.

## 8. Tests that show it works as one

1. **A memory's life:** he says something; she offers to keep it; he says yes (`confirmed_at`); it's recalled with
   "you told me on…"; a later remark that seems to contradict it is offered; his answer gives the older one its `until`.
2. **A habit and its reset:** three dismissals pause a topic; "What I've learned" shows why; its reset clears the
   evidence; the topic is offered again; a pause he asked for himself is untouched.
3. **A promise:** "I'll call the vet Friday" is offered, kept, appears on Friday's due list on the PC and the phone,
   and is done by voice.
4. **Forgetting:** "forget my old address" leaves it in no store, the index, the change history after its window, or
   the phone after its next sync. A conflict note about it never quoted it.
