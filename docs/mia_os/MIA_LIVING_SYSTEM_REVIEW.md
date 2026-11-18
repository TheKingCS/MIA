# MIA: the independent reviews of Prompt 21's documents

*Claude (Opus), 2026-11-18. Zac scheduled Prompt 21 for Fable. It was written on Opus, so it was reviewed before he
reads it, independently and read-only:
- by a fresh Fable reviewer, which saw only the documents and the code (DEC-0174: Fable reviews Opus's work);
- by Codex (`codex exec`, read-only).

Both reviewed version 1.0. Version 1.1 of the four documents takes in what was accepted below.*

## 1. Fable's findings (13) and the responses

| # | Sev | Finding | Response |
|---|---|---|---|
| F-01 | High | Code can't detect contradictions in free-text memories; only sync's same-field conflicts are visible to code | **Accepted.** Code detects only sync's conflicts; for memories the model proposes a possible clash when one is kept, and he decides (REQ-LS-003 now Should) |
| F-02 | High | A hybrid logical clock is the wrong tool (a star topology, a three-way merge already finds conflicts) and stamping every record is permanent | **Accepted.** Dropped. DEC-0285 now builds DEC-0243's approved "losing value kept"; a third engine's topology is researched before the laptop |
| F-03 | High | The dated habit snapshot is mis-specified (the gate's pace is derived from a per-device log) and could restore over a grant, a pause or the stop | **Accepted.** Replaced by each habit shown with its evidence and its own reset, and a list nothing resets; a dated restore deferred |
| F-04 | High | Runtime-enforced timeouts can't safely cut off synchronous Python mid-write | **Accepted.** Deadlines only for device and outside work, passed into the waiting call; a cancel check in long loops |
| F-05 | Med | The compensation framework is overbuilt; a failed change already has its before-images and says "nothing was changed" falsely | **Accepted, and fixed now** in `core/actions.py`, with a test |
| F-06 | Med | Sizes far off (about 800 capability registrations); ten direct model callers, not three | **Accepted.** A generic read-back; outputs stay text unless another step reads them; sessions given per package; the ten callers named |
| F-07 | Med | "Exists"/"missing" claims that don't match: `capabilities.py` has statuses and a retired state; `resolve_by_name` exists; `life_events` has a source; the stop ends work in flight; the naive-time count; records not yet written | **Accepted.** Each corrected; the count's method stated; the decision and question records written in this commit |
| F-08 | Med | The epistemic proposal forked the tested contract (new values, a confidence repeating `how`, a "verified" without his yes) | **Accepted.** The existing four fields kept; `confirmed_at` and `holds` only on his memories and life notes; an outside source can't be checked by itself |
| F-09 | Med | REQ-INT-015 is Must · MVP, but its work was placed in Alpha | **Accepted.** LS-02 moved to the MVP gate; it's small |
| F-10 | Med | Durable events in the history would put device-only facts into a file that syncs and is never rewritten | **Accepted.** Noticed state is re-derived from the stores at start |
| F-11 | Med | `runs.json` and `turn_traces.jsonl` sync; a phone's start-up recovery could mark a PC's running run stopped | **Confirmed by reading `core/runs.py` and fixed now**: both added to `NEVER_SYNC`, with a test |
| F-12 | Med | New mechanisms weren't paired against forgetting (notes quoting values, losers in a never-rewritten history, a persisted Signal capturing private turns) | **Accepted.** The loser goes to the change history (30 days, reached by forgetting), never `life_events`; notes never quote a sensitive value; the trace id is in memory for a private turn |
| F-13 | Low | Implementation began against the brief (the sync fix); the master plan, diagrams and roadmap weren't updated; "one owner" per stage overstated; packages' dependencies unstated | **Accepted.** The fixes are bug fixes to what runs, told to Zac as such; the master plan, roadmap and diagrams are updated in this commit; dependencies stated (LS-09 after LS-07) |

## 2. Codex's findings (10) and the responses

| # | Sev | Finding | Response |
|---|---|---|---|
| F-01 | High | The sync proposal contradicts the approved three-way merge | **Partly accepted.** DEC-0243 keeps the merge and also approves "the losing value kept and he's told"; what was wrong was the new clock, now dropped |
| F-02 | High | The sync fix was presented as established while uncommitted | **Accepted.** It's committed with this prompt and described as a fix made in it, with its test |
| F-03 | High | One ten-stage runtime would absorb controllers' own loops (DEC-0246) and clash with the synchronous bus | **Accepted.** Reframed as one vocabulary of stages with shared joins; controllers keep their loops; nothing new runs to fit the shape |
| F-04 | Med | The desktop's chats use the shared request logic, not an independent loop | **Accepted.** Corrected: they share `instant_answer` and `ChatWorker` but not the traced turn wrapper |
| F-05 | Med | Fixed confidence levels describe evidence, not confidence; the contract is staged, not contradicted | **Accepted** (as Fable's F-08) |
| F-06 | Med | Entity resolution is partial, not missing | **Accepted** |
| F-07 | Med | Universal synchronous timeouts aren't implementable | **Accepted** (as Fable's F-04) |
| F-08 | Med | Multi-store "all or none" overpromises | **Accepted** (as Fable's F-05) |
| F-09 | Med | The master plan and integration documents weren't updated | **Accepted** (as Fable's F-13) |
| F-10 | Low | "Read-back missing" is too absolute | **Accepted.** Partial: some flows re-read; the gap is coverage |

## 3. Where the two agreed, and what came of it

Both reviewers found the diagnosis mostly right and the prescription too large. The first draft's seven heaviest
proposals were removed or narrowed:
- the sync clock;
- compensations;
- universal timeouts;
- code-detected contradictions in free text;
- the dated restore;
- durable events;
- one engine.

The work packages fell from twelve to ten, and from about two dozen sessions to 14 to 16. Fable would approve
DEC-0280, 0284 and 0286 as first written; the others are narrowed as it asked. Neither reviewer found anything that
would let what MIA reads grant her anything.

## 4. Not done

A second pass by either reviewer on version 1.1 hasn't been run. ChatGPT's planning review (Prompt 17b §6) hasn't
been done.
