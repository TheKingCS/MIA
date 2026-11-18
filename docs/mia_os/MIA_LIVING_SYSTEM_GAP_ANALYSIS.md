# MIA: living system gap analysis (Prompt 21, deliverable 5)

*Claude (Opus), 2026-11-18. Version 1.1, revised after independent reviews by Fable and Codex (their findings and the
responses: `MIA_LIVING_SYSTEM_REVIEW.md`). Planning only. Every item Prompt 21 names, classified with its evidence,
using the classes in `MIA_LIVING_SYSTEM_PRINCIPLES.md` §3. The evidence comes from a read-only investigation of the
documents and code, checked where it mattered.*

## 1. The headline

1. **Most of it has a home, and much is built:**
   - Prompt 20's doctrine;
   - the history, links and the action contract with its grants;
   - 96 loops;
   - the lab;
   - specialists;
   - runs;
   - recall's first slice.
2. **The real gaps are few and mostly small:**
   - a trace id that ties a cause to its effects;
   - the existing provenance contract carried onto the memory stores;
   - sync's approved "losing value kept" not built;
   - a clock service;
   - one model-server address and the runtime's model calls on the provider;
   - a retention registry that also decides what syncs;
   - a generic read-back after a change.
3. **Four live bugs were found and fixed in this prompt:**
   - **four device-only files syncing:** what's noted on the PC, the recall index, runs and turn traces;
   - **a run synced to the phone was marked stopped there** while it still ran on the PC;
   - **a failed change said "nothing was changed"** while its first writes stayed.
4. **Approved decisions with no code yet:**
   - DEC-0204 (the GPU queue);
   - DEC-0208 (routing in code);
   - DEC-0209 (MIA's own council);
   - DEC-0218 (read-back);
   - DEC-0224 (a reproducing test before a fix);
   - part of DEC-0220 (the truth registry's states and evidence; `capabilities.py` has five statuses and a retired
     state already);
   - DEC-0243's kept loser.
5. **What the first draft proposed and the reviews took out, rightly:**
   - a new sync clock;
   - a compensation framework;
   - runtime-enforced timeouts on all capabilities;
   - code-detected contradictions in free-text memories;
   - a dated "restore my habits";
   - durable events in the history;
   - one ten-stage engine.

   Each was either not implementable here, overbuilt for one person, or risked a safeguard.

## 2. Every item, classified

### §1 of the prompt: the living system

| Item | Class | Evidence | Answer |
|---|---|---|---|
| Unified cognitive architecture | Covered, under-specified | `MIA_OS_LIVING_SYSTEM.md` §5.1; `assistant_turn.py`; `background_jobs.py` | one vocabulary of stages with shared joins, not one engine → cognitive §1 |
| Working memory | Partial | `conversation_state.py` | a written limit → memory §1 |
| Episodic | Covered | `life_events.py`, conversations, change history | — |
| Semantic | Partial | `user_memory_manager.py` | the epistemic declaration → memory §2 |
| Procedural | Covered (several engines) | taught skills, browser routines, workflows, paths; `runs.py` | one run record (DEC-0214) |
| Prospective | Covered, under-specified | life notes, alarms, calendar, reminders, maintenance | one due shape → memory §5 |
| Autobiographical | Covered, under-specified | chronicle, seasons, saga; `dev_evolution`, `dev_history` | named → memory §1 |
| Environmental | Partial | sensors, homestead, system health, connectivity, activity, weather | read where needed → memory §1 |
| Provenance | **Conflicting** | REQ-INT-015 "Exists" vs `EPISTEMIC_BASELINE` exempting the memory stores | the existing contract declared on them, at the MVP gate → memory §2 (DEC-0281) |
| Confidence | Partial | `links.derived`, specialists' derived/confirmed, `calibration.py` | `how` plus `confirmed_at`; no separate number → memory §2 |
| Contradiction resolution | Partial | sync sees same-field conflicts (DEC-0243), unbuilt for the loser; nothing for free text | sync's loser kept; the model proposes possible memory clashes → memory §3 |
| Consolidation | Partial | seasons, chronicle, reflection | folds deferred past R1 |
| Retrieval | Partial | `recall_index.py` (first slice) | R1 design stays → memory §7 |
| Continuous learning | Covered, under-specified | 96 loops, corrections, styles, the gate's pace | the lifecycle's states named → memory §4 (DEC-0282) |
| World model, knowledge graph | Covered | records + links + history (DEC-0137, 0188) | no second graph |
| Goal hierarchy | Partial | intents' chain, why-links, missions, directions | arbitration rule (he decides); a ranker deferred past R1 → cognitive §5 |
| Event-driven awareness | Partial | synchronous bus; daily checks on timers | unchanged; refs and trace id on events → contracts §6 |
| Capability / self-awareness registry | Partial | `capabilities.py` (five statuses, a `retired` state), the app registry, the tool registry, `ACTION_TYPES` | the four descriptions checked as one (DEC-0283); the truth registry's evidence and states (DEC-0220) |
| Reflection and evaluation | Covered | self-audit, self-report, benches, calibration | — |
| Multi-agent and model orchestration | Partial | development council, specialists and their review, teams (T2) | routing (0208), the GPU queue (0204), her council (0209), already approved |
| Universal action and skill infrastructure | Covered, under-specified | the action contract, grants, effects, UAL, runs | the descriptions checked as one → contracts §2 |
| Self-inspection and development | Covered | the lab, the protected list, her merges, inspection | DEC-0224 enforced; each merge names what shows it helped (LS-06) |

### §2: the cognitive runtime

| Item | Class | Answer |
|---|---|---|
| Intake | Partial | the trace id; the desktop's chats in the traced turn → cognitive §2 |
| Classification and validation | Covered | outside text marked where it enters (WP-03) |
| Attention and priority | Covered, under-specified | the gate, presence, homeostasis; one policy deferred |
| Context construction | Covered | — |
| Memory retrieval | Partial | memory §7 |
| Reasoning and planning | Partial | routing (0208); plan steps' dependencies when teams need them |
| Tool and agent selection | Partial | routing in code |
| Authorisation and execution | Covered | — |
| Verification | Partial (DEC-0218 approved; some flows re-read) | the generic read-back → contracts §2 |
| Experience into knowledge | Partial | the lifecycle's states |
| Long-running continuity | Covered | `runs.py`; a run stays on its device (fixed now) |
| Interfaces between stages | Under-specified | cognitive §2's table |
| Provider independence | Partial (ten direct callers) | contracts §7 |

### §3: learning

| Item | Class | Answer |
|---|---|---|
| Temporary, inferred, proposed, procedure | Covered | named → memory §4 |
| Verified knowledge | Partial | `checked`, `confirmed_at` → memory §2 |
| Evaluation before adoption | Covered (DEC-0212) | each habit shown with its evidence |
| Versioning and rollback of what's learned | Partial | per-habit resets, a never-reset list; a dated restore deferred → memory §4 |
| Provenance and correction | Partial / covered | memory §2 |

### §4: awareness and initiative

| Item | Class | Answer |
|---|---|---|
| Operational state, tasks, deadlines, problems, opportunities | Covered | — |
| Environmental changes, devices, capabilities, long-term objectives | Partial | device records (WP-10); the truth registry; arbitration by him |
| Notify, recommend, ask or act | Covered | the gate decides how to speak up; the tiers decide what may change (P6) |

### §5: the universal tool and skill contract

| Field | Class | Answer |
|---|---|---|
| Inputs, outputs | Partial | schemas checked against kinds; structured outputs where another step reads them |
| Permissions | Covered | — |
| Authentication | Partial | named for the kinds that need one |
| Execution state | Covered | proposals and runs |
| Errors | Partial | four kinds named |
| Timeouts | Partial (on outside calls) | deadlines for device and outside reach only |
| Cancellation | Partial | a cancel check in long loops; the stop honours it |
| Reversibility | Covered | — |
| Verification | Partial | the generic read-back |
| Audit | Covered | plus the trace id |

### §6: distributed intelligence

| Item | Class | Answer |
|---|---|---|
| Identity, offline, local execution | Covered | — |
| Device authentication | Partial | device records with scopes (WP-10) |
| Synchronisation | Covered (DEC-0243's merge), with leaks fixed now | the retention registry decides what syncs |
| Conflict resolution | Partial | the loser kept, one note (DEC-0285 implements DEC-0243) |
| Context handoff | Partial | the conversation continues from its synced copy |
| Resource allocation | Partial | DEC-0245, the GPU queue |
| A third full engine | Requires research | the topology before the laptop (Beta) |

### §7: self-evolution

Covered end to end (inspect, find, analyse, research, propose, isolate, test, authorise, deploy, roll back, keep
history). Partial:
- **Post-merge evaluation:** each merge names the test or loop that shows it helped (LS-06).
- **Retiring a capability:** a recorded state in `capabilities.py`, made through the lab (REQ-LS-011).
- **The lab isn't a sandbox:** a Landlock-narrowed worker on MIA OS.

### §8: additional infrastructure

| Item | Class | Answer |
|---|---|---|
| Temporal reasoning | **Missing** | the clock service (DEC-0284) |
| Context switching | Partial | workspaces (DEC-0230, Beta) |
| Multimodal perception | Covered (vision outside the provider) | contracts §7 |
| Provenance and verification | Partial | memory §2; World Intelligence's sources; specialists' review |
| Entity resolution | Partial (`resolve_by_name` within a type) | across types only by his stated link; deferred past R1 |
| Resource-aware scheduling | Partial | homeostasis built; the GPU queue (0204) |
| Event processing | Covered, under-specified | contracts §6 |
| Distributed databases | **Requires research** | the JSON stores at 10× today's records on the PC and the phone before R1; sqlite for a store that outgrows them, one at a time, behind the same API |
| Sync and conflicts | Partial | contracts §8 |
| Plugin and app SDKs | Partial | manifests, the scaffold; extensions later (Q-94) |
| Native app framework | Covered | — |
| Sandboxed execution | Partial | DEC-0176 |
| Prompt injection | Covered | `untrusted()`, outside tags with sweep tests; WP-03 |
| Privacy boundaries | Covered | — |
| Accessibility | Partial | FW-11 (Alpha) |
| Disaster recovery | Partial | WP-09, FW-09 |
| Data portability | Covered, under-specified | the account export; REQ-LS-012 |
| Update and migration | Partial | DEC-0267's versioned migrations |
| Long-term compatibility | Covered, under-specified | principle P10 |
| Observability and evaluation | Covered | plus the trace id and template version |

### Beyond the checklist

| Need | Answer |
|---|---|
| Causal trace ids | DEC-0280 |
| A change that fails part way | fixed now (contracts §5) |
| One record-type registry | contracts §3 |
| Prompt template versions | contracts §4 |
| A retention registry that decides what syncs | DEC-0286 |
| A replay of a simulated week across subsystems | after the clock service (LS-09) |
| A budget for her own initiative | homeostasis gains a daily compute budget for her own jobs, shown in Diagnostics (LS-10) |
| Owner continuity | a question for Zac (Q-111) |

## 3. One responsibility, several mechanisms

| Responsibility | Plan |
|---|---|
| What MIA can do (eight registries) | the four capability descriptions checked as one; the truth registry over them (DEC-0220); `MIA_OS_LIVING_SYSTEM.md` §3's "four registries acceptable" is read as "acceptable while they're checked to agree" |
| Multi-step work (eight engines) | each keeps its screen; all write to `runs.py` (DEC-0214) |
| Undo | `undo_log.py` (recent) and `change_history.py` (30 days): two layers of one mechanism, sharing `keep_sticky` |
| The runtime (`core_runtime.py`, `runtime.py`) | one retired when the image's runtime is the only one (FW-03) |
| A conversation turn | the desktop's chats in the traced turn |
| Model calls | one address; the runtime's calls on the provider |
| Reviewers | one rule for reading a reviewer's reply: only a clean agreement agrees (`specialist_review.read_reply`, 2026-11-18) |

## 4. Completeness for each major subsystem (§9 of the prompt)

| Subsystem | Purpose | Interface | Data | Security | Fails | Tested by | Accepted when |
|---|---|---|---|---|---|---|---|
| Cognitive runtime | asked and noticed work through shared joins | cognitive §2 | turn traces (on their device) | trust label from intake | cognitive §7 | the end-to-end tests below | each test passes with one trace id |
| Memory | his beliefs, with how they're known | the epistemic fields; `due()` | his stores, sealed | personal, never to a cloud | an unreadable store is named | memory §8 | a memory's whole life passes |
| Learning | lessons through gates | the lifecycle states | each loop's own | his yes for facts; grants for procedures | nothing adopted | memory §8 | a habit reset leaves his own settings untouched |
| Action contract | the one boundary | the four descriptions, checked | history | tiers, grants, stop | fails closed; a failure puts back its writes | `test_authority_review.py`, contracts §10 | every description agrees |
| Initiative | noticing and speaking up | Candidate | the gate's state | nothing changes without a tier | nothing unprompted goes out | the replayed week (LS-09) | the right things said once, in time |
| Devices and sync | one MIA everywhere | the sync contract | the retention registry | scoped keys | offline works alone | contracts §10 | a conflict keeps the loser and asks once |
| Self-development | her own improvements | the lab's proposal | git, the lab's records | protected list, suite, Claude's pass | reverted by itself | the lab's tests | a merge names what shows it helped |
| Models | replaceable intelligence | the provider | settings | sensitive never to a cloud | the fallback chain | routing tests | a model swap changes no data |
| Time | one clock | the clock service | zones on moments | — | — | frozen-clock tests | no naive local time in new code |

## 5. End-to-end tests

1. **A promise and a reading:**
   - he says "I'll fix the coop door Saturday";
   - the note is kept and is on Saturday's due list, on the phone too;
   - a temperature reading crosses a limit, and the greenhouse's own loop acts (DEC-0246);
   - MIA's message waits for the flow guard and is said once.
2. **A conflict across devices:** he changes the coop door size on the phone and the PC while apart. Sync keeps the
   loser in the change history and one note asks which is right.
3. **A failed change:** an approved change fails after its first write. That write is put back and he's told plainly.
4. **A model swap:** the everyday model changes. His data, links, habits and grants don't. The turn traces show the
   new model and the same template version.
5. **A replayed week** on a frozen clock: every due item is said on its day, nothing twice, and the stop holds what it
   should.

## 6. Work packages (each specified in full before it starts, REQ-IMP-012)

| ID | Package | Release | Sessions |
|---|---|---|---|
| LS-01 | The trace id through the turn, proposals, the history and change history; the template version (DEC-0280). **Built 2026-11-18** (`core/trace.py`): a turn, each scheduled job run and each screen press start one; proposals, their approval later, life events, changes, runs and the security log carry it; the turn trace keeps it and the prompt code's version | Alpha | 1 to 2 |
| LS-02 | The epistemic declaration and `confirmed_at`, `holds` on `user_memories` and `life_notes`; declarations on `life_events` and `links` (DEC-0281). **Built 2026-11-18:** his memories and life notes carry source, how, `confirmed_at`, `holds_from`/`holds_until`; the history and links declare it; all five off the baseline | **MVP gate** (REQ-INT-015) | 1 |
| LS-03 | Sync's loser kept in the change history with one note (DEC-0285, implementing DEC-0243); the retention registry deciding what syncs (DEC-0286) | Alpha | 2 |
| LS-04 | The four capability descriptions checked as one; deadlines and cancel checks for device and outside work; four error kinds (DEC-0283) | Alpha | 2 |
| LS-05 | The generic read-back after a change (DEC-0218); the record-type registry. **Built 2026-11-18**: `core/record_types.py` holds the one table (moved from links, which read it), with `HISTORY_ONLY` for the 25 kinds the history names that can't be read by id yet, each with why; `tests/test_record_types.py` fails on a new kind in neither. `core/read_back.py` checks every approved change: the files it wrote still hold what it left, and the records its history names resolve unless it removed them; the proposal keeps `read_back` ("ok" or what didn't) and his result line says so. It found two mixed refs at once (workshop recipes as `recipe:`, a person's own record sets), both fixed | Alpha | 2 |
| LS-06 | DEC-0224 enforced in the lab; each merge names what shows it helped. **Built 2026-11-18** (`core/dev_lab.check`): a change to code is ready only with a proving test, one failing at the start that passes in the lab, or one of its own test files that fails on the starting code (run in a `_proof-` copy with the lab's tests laid over the start) and passes in the lab. They are kept as `shown_by`, named in `describe`, in the reviewer's prompt and in the merge's commit message ("Shown by: ..."). A change to tests, docs or data alone needs none | Alpha | 1 |
| LS-07 | The clock service for new code; tests freeze it (DEC-0284). **Built 2026-11-18** (`core/clock.py`): now and today in his zone (`region.timezone`, else the computer's), `frozen()` for tests, the week, and `parse_day` for the day a phrase means; recurrences later | Alpha | 1 |
| LS-08 | One model-server address; the runtime's calls on the provider's `embed` and `see`. **Built 2026-11-18**: the address is written once (`core/llm_manager.DEFAULT_SERVER`) and every module and tool asks `local_server_url()`, which reads `llm.base_url`; embeddings (`meaning`, `recall_index`) and vision (`sight`) go through `OllamaBackend.embed` and `see`. Six background writers (Chronicle issues, creations, knowledge, the coder, paths, work review) still post their own JSON-format requests to that address; they move onto the backend when it takes their options. `tests/test_model_server_address.py` fails on the port written anywhere else | Alpha | 1 |
| LS-09 | A replayed week across the subsystems (after LS-07) | Beta | 2 |
| LS-10 | A daily compute budget for her own initiative; each habit's evidence and reset in "What I've learned" | Beta | 1 to 2 |

**Deferred past R1:**
- entity matching across types;
- folding repeated memories;
- a single attention policy and goal ranking;
- a dated restore of habits;
- structured outputs for every capability;
- the laptop's sync topology (researched before Beta).

These run beside the foundation (Q-103: both at once), the critical path first: about 14 to 16 sessions in all, most
in Alpha.

## 7. Fixed in this prompt (with tests)

1. **Four device-only files syncing:**
   - what's noted on the PC (`activity.json`);
   - the recall index (`recall_index.json`);
   - runs (`runs.json`);
   - turn traces (`turn_traces.jsonl`).

   All four are now in `core/sync.py`'s `NEVER_SYNC` (REQ-DST-011). Copies already on the phone stay there until
   removed (Q-112).
2. **A run synced to the phone was marked stopped** by the phone's start-up recovery while it ran on the PC: fixed by
   (1).
3. **A failed change said "nothing was changed"** while its first writes stayed: the failure now puts them back
   (`core/actions.py`).

Prompt 21 says not to begin implementation. These are bug fixes to what already runs, found by the investigation and
confirmed by both reviewers, and they're told to Zac as such.

## 8. Requirements

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-LS-001 | A turn, a job and a change shall carry one trace id from intake into the turn trace, proposals, the history and the change history; a private turn is never traced. | Must | R1 | All | Exists (2026-11-18, LS-01) | T | DEC-0280 → 21 |
| REQ-LS-002 | The memory stores shall declare the epistemic contract (source, when, how, checked), and his memories and life notes shall carry when he confirmed them and when they hold. | Must | MVP | All | Exists (2026-11-18: user_memories, life_notes, life_events, links; intents next) | T: the baseline loses those stores | DEC-0281, REQ-INT-015 → 21 |
| REQ-LS-003 | When a memory he's keeping seems to contradict one held, she shall say so and he shall decide; nothing is overwritten. | Should | R1 | All | New | T | DEC-0281 → 21 |
| REQ-LS-004 | Every inferred habit shall be shown with its evidence and its own reset, and no reset shall touch his grants, his standing yeses, a pause he asked for, the stop, or anything he set himself. | Must | R1 | All | Partial | T | DEC-0282 → 21 |
| REQ-LS-005 | The tool, the action kind, the manifest and the effects table of every capability shall agree, checked by a test; device and outside work shall have deadlines and honour cancellation. | Must | R1 | All | New | T | DEC-0283 → 21 |
| REQ-LS-006 | A change that fails part way shall leave every store it wrote as it was before, and say so truthfully. | Must | MVP | All | Exists (2026-11-18) | T | DEC-0283 → 21 |
| REQ-LS-007 | New code shall get the time from one zone-aware clock service, and tests shall freeze it. | Must | R1 | All | Exists (2026-11-18, LS-07) | T | DEC-0284 → 21 |
| REQ-LS-008 | A field changed on two devices shall keep the losing value in the change history and tell him once, without quoting a sensitive value. | Must | R1 | All | New | T | DEC-0285, DEC-0243 → 21 |
| REQ-LS-009 | Every store shall be listed with its class, retention, end of life and whether it syncs, sync shall read that list, and a store missing from it shall fail a test. | Must | R1 | All | Partial (NEVER_SYNC) | T | DEC-0286 → 21 |
| REQ-LS-010 | The model server's address shall come from one setting, and MIA's runtime shall call models only through the provider interface. | Must | R1 | All | Partial (2026-11-18, LS-08: the address is one setting; six JSON-format writers still post directly) | T | DEC-0206, DEC-0207 → 21 |
| REQ-LS-011 | Retiring a capability shall be a recorded state, made through the lab, never a silent removal. | Should | R1 | All | Partial (`retired` state) | R | DEC-0283 → 21 |
| REQ-LS-012 | Everything of his shall be exportable in open formats in one step, and an export shall restore on a fresh MIA. | Must | R1 | All | Partial (account export) | T | DEC-0251 → 21 |

## 9. Decisions and questions

**Proposed decisions** (records in `docs/DECISIONS.md`):

| DEC | Decision |
|---|---|
| DEC-0280 | A trace id from intake into every record of what happened; the template version in the turn trace |
| DEC-0281 | The existing epistemic contract declared on the memory stores, with `confirmed_at` and `holds` on his memories and life notes; an outside source can't be checked by itself |
| DEC-0282 | One learning lifecycle with named states; habits shown and reset one at a time; a list nothing resets |
| DEC-0283 | The four descriptions of a capability checked as one; deadlines and cancellation for device and outside work only; a generic read-back |
| DEC-0284 | One zone-aware clock service for new code |
| DEC-0285 | DEC-0243's losing value built: kept in the change history with one note; no new clock |
| DEC-0286 | A retention registry for every store, which also decides what syncs |

**For Zac:**

| Q | Question | Recommended |
|---|---|---|
| **Q-111** | If something happened to you, should someone you trust be able to open MIA's data? It's sealed, with a PIN at start. The usual answer is a sealed envelope with the recovery key, kept with your important papers. MIA never gives anyone access herself. | Yes, an envelope you keep; MIA stays yours alone |
| **Q-112** | Four files meant to stay on the PC had been copying to your phone: what MIA noted about your apps, her recall index, her runs and her turn logs. That's fixed today. Remove the copies already on the phone? | Yes |
| **Q-113** | Build the living system packages LS-01 to LS-10 alongside the foundation work, critical path first, as with the Windows backlog (Q-103)? LS-02 is small and belongs at the first version's gate. | Yes |
