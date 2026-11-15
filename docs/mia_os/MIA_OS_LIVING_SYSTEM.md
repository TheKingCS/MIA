# The Living System: how the doctrine maps onto MIA, and what it adds

*Claude (Opus), 2026-11-15, answering the foundational doctrine "The Living System: Identity, Continuity,
Awareness, Adaptation & Evolution" (kept verbatim: [`prompts/20_LIVING_SYSTEM_DOCTRINE.md`](prompts/20_LIVING_SYSTEM_DOCTRINE.md)).
The doctrine asks for an audit with repository evidence before any change. This is that audit and the proposal. It
is the doctrine's one mapping document: the master plan points here, and later prompts (04, 05, 07, 08, 13, 14, 16)
apply it. DEC-0173 is the proposed decision. The doctrine asks Fable to challenge this work; that review hasn't
happened yet (section 13).*

## 1. The headline

**MIA is already built as one system, and most of the doctrine describes what exists.** DEC-0137 (the Living
Systems Framework, approved 2026-11-08) found about 80% of a near-identical framework in working code and chose to
"generalize the existing foundation, don't rebuild it". This doctrine is broader (it adds homeostasis, provider
independence, autonomy levels and evolution governance), but the answer is the same: **no new "Living System"
service or app.** What the doctrine adds that MIA doesn't have is a short list:

1. **Grants** (DEC-0156, proposed, not built): the autonomy levels need them to be real, not conventions.
2. **Homeostasis:** MIA reads her health but doesn't act on it. Nothing defers work when the PC is busy or on battery,
   and a job that fails every time is retried at full rate forever.
3. **One epistemic contract:** what she knows, observed, inferred or holds stale isn't marked the same way across
   stores. Some stores mark it (World Intelligence's finds, links, the history's environment tag); most don't.
4. **The invariants as tests:** most of the doctrine's ten invariants already have a test somewhere; a few don't.
   The doctrine is satisfied when each one fails a build if it's broken.

Everything else in the doctrine is either built (with evidence below), already planned in an approved workstream, or
belongs to a later MIA OS prompt that will now carry it as an acceptance criterion.

## 2. The ten characteristics, mapped (deliverables 1 and 2)

Status uses the doctrine's own scale. Evidence is a file or test in this repository.

| # | Characteristic | Status | Evidence | What's missing |
|---|---|---|---|---|
| 3.1 | Persistent identity and continuity | **Existing, verified** | Identity in one place, outside any model (`core/personality.py` IDENTITY, DEC-0067); personal stores per person (`core/personal_data.py`), sealed (`core/at_rest.py`, tests `test_at_rest`, `test_key_unlock`); history kept forever (`core/life_events.py`, `test_life_events`); state survives devices (`core/sync.py`, `test_sync`), restarts and moves (`core/data_root.py`, `tools/move_home.py`, `test_data_root`); context rebuilt per turn, not a whole history loaded (`core/context_assembler.py` v2, `core/self_knowledge.block_for`, `test_state_export`) | Its seven layers (identity, user knowledge, episodes, state, objectives, learned capabilities, temporary context) exist in different stores but aren't named as one map; that's documentation (section 6) |
| 3.2 | Awareness and perception | **Partly** | Event bus (`core/event_bus.py`), history events, live change signal (`core/live.py`), sensors (`core/sensors.py`), connectivity (`core/connectivity.py`), the inbox and mail, the homestead snapshots, World Intelligence (`core/world_intel.py`, `test_world_intel`), health readings (`core/system_health.py`) | No common mark of known / observed / inferred / to investigate / stale (gap 3). OS-level perception (files, desktop events) waits on MIA OS (Prompt 05) |
| 3.3 | Integrated understanding | **Existing, verified** | Typed links between any records by `kind:id` (`core/links.py`, `test_links`), the life state as one derived picture (`core/context_assembler.py`, `/api/state`, schema-checked), reasons (`core/why_graph.py`), finds linked to watches and (W2) to projects | New stores must join the link catalogue; a test for that exists only for the search catalogue |
| 3.4 | Learning | **Existing, partly uniform** | 95 improvement loops (`core/loops.py`, `test_loop_coverage` fails on an undecided process), corrections (`core/corrections.py`), the Fix-It Log (`core/failure_log.py`), answer ratings and learned style (`core/response_style.py`), the gate's learned pace (DEC-0171), dev knowledge with provenance (`core/dev_knowledge.py`) | Provenance and confidence aren't uniform on the person's own knowledge (memories carry a source; most stores don't carry confidence) |
| 3.5 | Self-development | **Existing, verified** | The full lifecycle the doctrine lists: gaps found (`core/capability_gaps.py`), researched and built in an isolated worktree (`core/dev_lab.py`, `test_dev_lab`), reviewed by another model (the council, `core/council.py`), merged only on Zac's approval (DEC-0058), Night School (`core/night_school.py`), taught skills practised until proven (`core/taught_skills.py`) | "Retire a capability" has no procedure; "evaluate a new provider" is `core/model_bench.py` for local models only |
| 3.6 | Purposeful agency | **Partly** | Daily checks and the communication gate (`core/background_jobs.py`, `core/communication_gate.py`), missions MIA assigns, insights, the development engine's next step (`core/development_engine.py`), World Intelligence's watches | No one place that ranks objectives across domains (intents, projects, missions, maintenance, money each rank their own); the six levels aren't enforced as levels (gap 1) |
| 3.7 | Adaptability | **Existing, verified** | Modules discovered, never registered by hand (`core/module_manager.py`); tools in one registry (`core/assistant_actions.py`); actions in one contract (`core/actions.py`); sources as a table (`core/world_sources.py`); two model backends behind one interface (`core/llm_manager.py`: Ollama, llama.cpp's OpenAI-style server) | Cloud providers sit outside that interface (the council); the doctrine's "interchangeable providers" is Prompt 07's to design |
| 3.8 | Self-maintenance and health | **Partly** | Readings (`core/system_health.py`, `core/diagnostics.py`), the runtime's health endpoint and per-job failure isolation (`core/runtime.py`, `core/scheduler.py`, `test_runtime`, `test_scheduler`), nightly backups and restore (`core/auto_backup.py`, `core/backup_manager.py`), a damaged file set aside rather than lost (`core/data_recovery.py`, at_rest's copy aside), one MIA per folder (`core/instance_lock.py`), the security log | **Homeostasis** (gap 2): no deferral under load, no backoff for a job that keeps failing, no provider failover. Image rollback and recovery are MIA OS work (DEC-0157, Prompt 14) |
| 3.9 | Feedback and evaluation | **Existing, partly uniform** | Loops measure outcomes against floors and open tasks; taught skills count clean runs; browser routines count finishes; the gate learns from reactions; the undo log records what was taken back (`core/undo_log.py`) | Not every workflow states what "done" means; a loop's `covers=` is the place, and `work/loop_coverage.json` lists the ones still `todo` |
| 3.10 | Human-centred purpose | **Existing, verified** | Facts in code, the model only phrases (CLAUDE.md); consequential actions approved by a person (`core/actions.py`, `core/browser_safety.py`, email never sent by a tool); undo for every change; crisis handling never on the model (`core/safety_floor.py`, `test_safety_floor`); learning paths that make the person capable themselves (`core/paths.py`, DEC-0112) | — |

## 3. The shared services, mapped (deliverable 4, doctrine section 8)

| Service | Where it is | Status |
|---|---|---|
| 1. Identity and continuity | `core/personality.py`, `core/personal_data.py`, `core/data_root.py`, `core/sync.py`, `core/at_rest.py` | Existing |
| 2. Context and knowledge retrieval | `core/context_assembler.py` (life state), `core/self_knowledge.py`, `core/links.py`, `core/web_search.py` catalogue | Existing |
| 3. Events and awareness | `core/event_bus.py` (in-process), `core/life_events.py` (history), `core/live.py` (change signal) | Existing; synchronous by design (CLAUDE.md) |
| 4. Objectives and priorities | intents, projects, missions, the development engine | **Partly**: no cross-domain ranking (section 5.3) |
| 5. Initiative and orchestration | the scheduler and jobs, the gate, taught skills, the UAL (`core/ual.py`) | Existing for one machine; orchestration across devices is Prompt 12 |
| 6. Capability registration | `core/capabilities.py` (built from code), the tool registry, `ACTION_TYPES`, the UAL catalogue, `core/web_surfaces.APPS` | Existing; four registries that agree by tests, not one (acceptable: each is the authority for its kind) |
| 7. Learning and feedback | `core/loops.py`, corrections, failure log, ratings, the gate's pace | Existing |
| 8. Health and resources | `core/system_health.py`, `core/runtime.health()`, `core/scheduler.status()` | **Partly**: readings, no regulation (section 5.2) |
| 9. Policy and permissions | the action contract's approval, `browser_safety.classify`, child gating, UAL tiers, taught-skill gates | **Partly**: DEC-0156 grants not built |
| 10. Observability and audit | the gate's decision log, the history, the undo log, turn traces, the security log, agent activity (`core/agent_activity.py`), `/api/why` | Existing |

**No new central service is proposed.** The doctrine warns against one; DEC-0137 chose the same.

## 4. Gap analysis (deliverable 3)

| Gap | Severity | Owner | Where it goes |
|---|---|---|---|
| G1. Grants and the six autonomy levels enforced in code | high: the agency and human-authority invariants rest on it | **Fable** (DEC-0166: security design) | World Intelligence W4 already plans it; widen it to every tool and action as DEC-0156 says |
| G2. Homeostasis v1 | medium: wasted work and silent retry storms; matters more on the Pi and battery | Opus | new, small (section 5.2) |
| G3. One epistemic contract for facts | medium: the knowledge and learning invariants | Opus | a contract for new stores, applied to old ones as they're touched (section 5.4) |
| G4. Cross-domain objective ranking | medium: initiative is per domain today | Opus, after W2 | the development engine's ranking generalised, through the relevance engine (World Intelligence W2) |
| G5. Retiring a capability | low | Opus | a procedure in `docs/ADDING_MODULES.md` and the capability registry |
| G6. Provider failover and cloud providers behind the backend interface | medium | Prompt 07 (Opus) | Prompt 07's provider-independent design |
| G7. OS-level perception, image rollback, recovery environment | high for MIA OS | Prompts 05, 14 | already their scope |
| G8. Invariants not yet guarded by a test | medium | Opus | section 8's table: the missing tests |

## 5. Specifications

### 5.1 The Living Cycle (deliverable 5)

The doctrine's cycle (perceive, understand, prioritise, initiate, act, evaluate, adapt) is already MIA's shape, as a
**pattern each subsystem follows, not a central process.** Each stage has an existing contract:

| Stage | Contract | Example (World Intelligence) |
|---|---|---|
| Perceive | a store or adapter records what came in, with its source and time | `run_watch` reads sources |
| Understand | links to existing records (`core/links.py`), the life state | a find linked to a watch; (W2) to a project |
| Prioritise | a score with reasons, worked out in code | `world_intel.score`, (W2) relevance |
| Initiate | a candidate to the gate, or a proposed action | `candidate_for` → `offer_batch` |
| Act | an action through `core/actions.py` (approved where it must be) | `world_find.save` |
| Evaluate | a loop or outcome count | the gate's pace; (W1 todo) the source loop |
| Adapt | the loop's improve step, or a learned weight | the pace doubles or halves |

**A new subsystem's acceptance criteria include its cycle**: each stage named against these contracts in its design
note. That's how the doctrine reaches every subsystem without a new layer.

**Timescales** (doctrine section 5) map onto what exists: immediate (the turn, the action contract), short-term (the
scheduler's jobs: 20 seconds to 10 minutes), daily (`DAILY_CHECKS`), long-term (Night School, loops' monthly
evaluations, the weekly Chronicle, learning paths' stages).

### 5.2 Homeostasis and system health v1 (deliverable 6)

Small, in code, inside the scheduler and the jobs, not a new service:
- **Job classes:** each job and daily check is `essential` (alarms, power, the gate's urgent path, backups, the
  inbox) or `deferrable` (World Intelligence, Good News, Night School, the dependency audit, the system map).
- **Conditions, read from `core/system_health.py` and `core/connectivity.py`:** busy (CPU over 85% for the last few
  readings, or memory under 10% free), on battery below 30%, offline, disk under 5% free.
- **Rules:** a deferrable job doesn't start while busy, on low battery or (for online jobs) offline; it runs at the
  next tick that's clear. Each deferral is recorded on the job (`deferred`, with why), shown by the runtime's health
  endpoint and "how are you doing?".
- **Backoff:** a job that fails three runs in a row waits twice as long before the next try, up to six hours, and is
  reported once (to the Fix-It Log, and through the gate if it's essential). One success resets it. This is the
  doctrine's "prevent uncontrolled retries".
- **Providers:** when the model server doesn't answer, the existing wake-and-retry (`LLMManager._ask`) stays; failover
  to another approved provider is Prompt 07's.
- **Updates and rollback:** stores already have undo and nightly backups; the OS image's rollback is Prompt 14's.
- **Permission:** deferring and backing off are MIA's own reversible choices about her own work, logged; nothing
  outward. Q-26 asks Zac to confirm.

### 5.3 Objectives and initiative

Intents (open-ended goals), projects, missions and learning paths are the objective records; there's no new store.
What's missing is a **cross-domain ranking**: World Intelligence's relevance engine (W2) scores against these
records, and the same scoring, generalised from the development engine's `next_step`, ranks what MIA proposes next
across domains. Built with W2, not separately.

### 5.4 Identity, memory and continuity (deliverable 7)

The doctrine's seven layers, named onto stores, so a new feature knows where its data belongs:

| Layer | Where | Rule |
|---|---|---|
| Identity and principles | `core/personality.py`, `CLAUDE.md`, the decisions | one source; a feature never defines its own persona |
| User knowledge | memories, people, intents, preferences (`core/user_memory_manager.py`, relationships, person settings) | personal stores, sealed, with source |
| Episodes | conversations, the history (`core/life_events.py`), turn traces | the history is never rewritten |
| Operational state | each store's current records; the runtime's health | stores are the current state (ENGINE_PHASE1_PLAN) |
| Active objectives | intents, projects, missions, paths, watches | section 5.3 |
| Learned capabilities | taught skills, browser routines, learned styles and paces, dev knowledge | each with its evidence (clean runs, counts) |
| Temporary context | the turn's assembled context (`context_assembler`, `self_knowledge.block_for`) | built per turn, never stored as truth |

**Across providers:** every layer above lives outside any model, and the turn's context is assembled by code. A model
swap (`llm.backend`) doesn't change any of it. A test proves this (section 8).

**The epistemic contract (G3)** for any record that states a fact about the world or the person: `source` (where it
came from), `at` (when it was read or said), `how` (`said` by the person, `observed` by a sensor or source, `inferred`
by MIA, `computed` in code), and, where it can go stale, `checked` (last verified). New stores carry it from their
first version; an old store gains it when it's next changed. World Intelligence's finds and links already do.

### 5.5 Autonomy and permissions (deliverable 9)

The doctrine's six levels onto what exists and DEC-0156:

| Doctrine level | MIA today | DEC-0156 tier |
|---|---|---|
| 1 Observe | stores, sensors, watches | observe |
| 2 Analyse | insights, relevance, research, comparisons | observe |
| 3 Recommend | the gate's messages, next steps | suggest |
| 4 Prepare | drafts (email never sent), proposed actions, plans | suggest |
| 5 Execute authorized tasks | routine actions with exact undo (Zac's rule: automate with exact undo), learned taught skills within their gates | act-within-grant |
| 6 Consequential | buy, pay, send, sign, delete, publish, share personal data: a person's press each time | act-with-approval / never granted |

**An agent can't grant itself anything:** taught skills keep each step's gate (`core/taught_skills.py`), browser
commits are approved only by a person (`core/browser_safety.py`), and untrusted text never grants (DEC-0156). The
grant check itself is G1, Fable's.

### 5.6 Self-development governance (deliverable 10)

Already the lab's lifecycle (DEC-0058, DEC-0167): a gap, a proposal, an isolated worktree with no real data, tests,
another model's review, Zac's approval of the merge. The doctrine adds **post-deployment evaluation** (a merged
change names the loop or test that will show whether it helped) and **retirement** (G5). Neither needs a new system.

### 5.7 Security and information integrity (deliverable 11)

Already in place and unchanged: outside text reaches the model only as `untrusted()`, a change asked for right after
reading the web is held (`carries_outside_text`), the browser types only the person's words (DEC-0122), facts and
prices are read in code, World Intelligence keeps every find's source. The doctrine's list adds nothing new beyond
G1 (grants) and G3 (marking what's inferred).

## 6. Documents updated, and no competing authority (deliverable 12)

The repository's MIA OS documents differ from the doctrine's list; the mapping:

| Doctrine names | Here | Change |
|---|---|---|
| MIA_OS_MASTER_PLAN | `MIA_OS_MASTER_PLAN.md` | the doctrine adopted as a foundation (on Zac's yes), pointing to this document |
| MIA_OS_VISION | `MIA_OS_VISION.md` | a paragraph: MIA is one Living System; apps, agents and models are its parts |
| MIA_OS_REQUIREMENTS, ARCHITECTURE, AI_ARCHITECTURE, SECURITY, ROADMAP | not written yet: Prompts 04, 05, 07, 13 and 16 | each carries section 8's invariants and section 5's specifications as acceptance criteria |
| MIA_OS_DECISIONS | `MIA_OS_DECISIONS.md` and `docs/DECISIONS.md` | DEC-0173 |
| MIA_OS_OPEN_QUESTIONS | `MIA_OS_OPEN_QUESTIONS.md` | Q-24 to Q-26 |

## 7. Dependencies (deliverable 13)

- G1 grants ← nothing new; it's DEC-0156 (Fable). Unblocks: unattended browser runs (World Intelligence W5), level 5
  everywhere.
- G2 homeostasis ← the runtime's scheduler (built). Unblocks: the Pi (battery, small CPU), World Intelligence's heavier
  watches.
- G3 epistemic contract ← nothing. Unblocks: W2 relevance's confidence, the learning invariant's test.
- G4 objective ranking ← W2 relevance.
- G6, G7 ← Prompts 07, 05, 14.

## 8. The invariants as tests (deliverables 8 and 14)

Each invariant, the test that already guards it, or the one to write.

| Invariant | Guarded by | To write |
|---|---|---|
| Identity: no competing identities | — | a test that every prompt speaking as MIA takes IDENTITY from `core/personality.py` (no second persona string) |
| Continuity: survives interruptions, updates, devices | `test_at_rest`, `test_sync`, `test_backup_manager`, `test_data_root`, `test_key_unlock`, `test_instance_lock` | — |
| Knowledge: provenance, confidence, time, relations | `test_world_intel` (sources), `test_links`, `test_life_events` | a test that every store created from now on carries the epistemic contract (a list of exempt older stores that may only shrink, like `work/doc_baseline.json`) |
| Agency: initiative within permissions | `test_communication_gate`, the action contract's tests, `test_taught_skills` | the grant check's tests (G1) |
| Learning: no unverified fact becomes authoritative | `test_corrections`, the gate's tests | with G3: an inferred fact never overwrites a said one |
| Expansion: through governed interfaces | `test_loop_coverage`, `test_parity`, `test_documentation`, the registries' tests | — |
| Resilience: one failure doesn't take the rest | `test_scheduler`, `test_background_jobs` (a failing check doesn't stop the others), `test_at_rest` (a bad file doesn't stop MIA) | homeostasis: backoff and deferral (G2) |
| Human authority | `test_safety_floor`, the email and browser commit tests | the grant registry sweep (G1) |
| Observability | the gate's log, `/api/why`, the undo log | a test that every job's deferral and backoff shows in `/api/runtime/health` (G2) |
| Evolution: testable, versioned, recoverable | git, the lab, `test_undo` paths, backups | per-store schema versions are T-03 (Prompt 15) |
| Continuity across models (acceptance, doctrine 18) | — | a test that a turn's context is assembled from stores alone: switching `llm.backend` changes no store and no assembled context |

## 9. Roadmap: the doctrine inside existing workstreams (deliverable 15)

No new workstream. In order:

| Step | What | Model |
|---|---|---|
| L1 | Adopt the doctrine (DEC-0173), update the master plan and vision, write the three missing invariant tests that need no new code (identity source, continuity across models, the epistemic contract for new stores) | Opus |
| L2 | Homeostasis v1 (section 5.2), with its tests | Opus |
| L3 | World Intelligence W2 (relevance) with cross-domain objective ranking (5.3), carrying the epistemic contract | Opus |
| L4 | Grants (DEC-0156) and the six levels enforced, with the registry sweep test | **Fable** |
| L5 | Fable's challenge review of this document, as the doctrine asks; disagreements recorded in DECISIONS | **Fable** |
| — | Prompts 04, 05, 07, 08, 13, 14, 16 carry sections 5 and 8 as acceptance criteria | as assigned |

## 10. Contradictions and decisions needed

- **"Codex" (doctrine section 19).** MIA's team is Zac, ChatGPT, Muse and Claude (`docs/COLLABORATION.md`); Codex
  isn't part of it. Its role (independent verification) is today Fable reviewing Opus's work (DEC-0166: "the reviewer
  is not the author"). Whether to add Codex as a collaborator is Zac's (Q-25).
- **"Hundreds of agents"** sits against CLAUDE.md's rule against speculative threading and services. The doctrine
  itself says to avoid premature, speculative capability; this proposal follows that.
- **A cloud model being part of MIA's continuity** is already settled: identity and context live outside every model.

## 11. Acceptance (doctrine section 18), how each is shown

| Criterion | Shown by |
|---|---|
| Continuity independent of model sessions | the continuity-across-models test (L1) |
| Context shared across apps and devices | `test_sync`, `test_state_export` |
| External information joins knowledge | `test_world_intel`; W2's linking tests |
| Discoveries related to goals and projects | W2's relevance tests |
| Initiative without constant prompting | `test_communication_gate`, `test_background_jobs`, World Intelligence's tick test |
| Consequential actions governed | the action contract's tests; L4's registry sweep |
| Feedback improves behaviour | the gate's learned-pace tests, `test_loop_coverage`, `test_taught_skills` |
| New capabilities without redesign | `test_world_intel` (an adapter added alone), module discovery tests |
| Health and resources observable | `test_runtime` (health endpoint), L2's tests |
| Failures isolated and recovered | `test_scheduler`, `test_at_rest`, L2's backoff tests |
| Self-development controlled | `test_dev_lab` |
| Autonomous decisions inspectable | the gate's log tests, `/api/why` tests |
| Coherent as it grows | `test_loop_coverage`, `test_parity`, `test_documentation`, the overview and registry tests |

## 12. Questions for Zac

- **Q-24.** Adopt the doctrine as MIA OS's foundation (DEC-0173), implemented as this mapping: invariants guarded by
  tests, homeostasis v1, one epistemic contract, grants, and no new "Living System" service?
- **Q-25.** Codex: add it to the team as an independent verifier (it would need its own entry in COLLABORATION.md
  and a way to read the repo, which is public), or keep that role with Fable reviewing Opus?
- **Q-26.** Homeostasis: may MIA defer her own background work (World Intelligence, Night School, Good News) while
  the PC is busy, offline or on low battery, and slow down a job that keeps failing, by herself, logged?

## 13. Status (2026-11-15)

- **Approved** (DEC-0173). **Built:** L1 (`tests/test_living_system.py`) and L2 (`core/homeostasis.py`; she says so each
  time she eases off or a job backs off, Zac's condition).
- **Checkers** (DEC-0174): Fable reviews all Opus work; Copilot, Claude, ChatGPT and Muse check independently where it
  fits. No Codex.
- **Still to come:** Fable's challenge review of this document (L5), L3 with World Intelligence W2, L4 grants (Fable).
