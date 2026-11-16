# MIA Specialized Agent Teams: audit and proposed architecture

*Claude (Fable), 2026-11-16, for Zac's handoff of the same day
(`docs/mia_os/prompts/25_SPECIALIZED_AGENT_TEAMS.md`, kept verbatim). This is the handoff's section 13: the twelve
deliverables it asks for before any implementation. Nothing here is built. Everything proposed waits on Zac
(section 12); only he approves a decision.*

## 1. The headline

Most of the machinery the handoff describes already exists in MIA, in pieces that were built for other purposes and
don't yet know about each other:

- **16 specialists** with charters, limits and workbooks (`core/specialists.py`, DEC-0109) are the start of the
  agent registry.
- **The council's floor** (`core/council_floor.py`) is a working, budgeted way for several models to answer and
  question each other through MIA.
- **The run record** (`core/runs.py`) and **the stop** (`core/stop.py`) already list and halt anything done in steps.
- **Projects, needs, prices, opportunities, plans and material lists** already hold a project's facts.
- **The lab** (`core/dev_lab.py`) already writes and tests code in isolation and merges only on Zac's approval.
- **Grants and the action contract** already separate "an agent proposed it" from "Zac approved it".

What is missing is small in code and large in consequence: **a team record** (who is working on what, for which
project), **a workspace** (the structured findings, conflicts, decisions and deliverables of that work), **a
coordinator** that breaks an objective into tasks with dependencies, and **an honest answer about which model does
the thinking**.

That last point is the real constraint, and it should be said plainly before anything is built:

> MIA's own model is small (llama3.2:3b for conversation; qwen2.5:14b for the heavier local work). It can classify a
> request, name disciplines, keep a record and phrase facts. It cannot do acoustic engineering. A team that produces
> work worth trusting on a wearable audio device needs the stronger models: the council's cloud members, on Zac's
> own accounts, with their usage limits and with whatever he chooses to send them. So a team's quality, cost and
> privacy are all set by one decision (Q-53), and "local-first" here means: local for coordination, records and
> anything his data touches; cloud for the specialist thinking, on his yes.

The second honest limit: **artifacts**. Today MIA can produce documents, code (in the lab), pictures, material and
cut lists (computed in code), screens and workflows. She has no CAD, PCB, circuit-simulation or slicer tool. Those
arrive one at a time as tools (section 9, phase T5), each a real integration; until one exists, the team says "this
needs a CAD model, which I can't make yet" rather than describing one as if it were made.

## 2. Audit: what exists (deliverable 1)

| The handoff asks for | What MIA has | State |
|---|---|---|
| Agent registry | `core/specialists.py`: 16 specialists (construction, homesteading, radio, strategy, maker, outdoors, music, research, testing, engineering, and six trades), each with a charter, skills, curriculum tracks, loops, **limits**, and trigger words; `who_knows(question)` picks them | Built for knowledge, not for tasks: no tools, task types, model needs or evaluation history |
| Agents that build MIA | `work/agents.json` and `core/work_agents.py`: roles as provider + model + tier (read, propose, experiment, review); approve is Zac's only, in code | Built; development only |
| Agent communication | `core/council.py` (one threaded record), `core/council_floor.py` (each message of Zac's opens a budget; a member asks another with one `ASK name:` line that MIA gates; members read a short context, never the whole chat; nothing in the chat can approve, grant or start work) | Built; free text, not structured findings |
| Model routing | Roles in `work/agents.json`; `core/dev_usage.py` (a member resting at its limit is skipped); `core/model_registry.py` (what's really running); `core/model_bench.py` | Per role by configuration; no per-task routing |
| Independent review | DEC-0174 (another model reviews); the lab compares the suite before and after; the UAL's Verify action checks claims against sources | Built for code and claims |
| Tasks and dependencies | `core/runs.py` (one record per run: steps, where it is, why it ended); `core/workflows.py` (fixed-vocabulary steps); `core/taught_skills.py`; plans across apps is UI-7, **not built** | The record exists; a task graph does not |
| Project and mission systems | `core/project_manager.py`, `core/mission_manager.py`, `core/requirements.py` (needs), `core/price_book.py`, `core/opportunity.py`, `core/plan_library.py` and `core/build_calcs.py` (quantities in code), `core/paths.py` (learning) | Built |
| Memory and knowledge | Specialist workbooks (notes are *derived* until Zac confirms; withdrawn ones kept), `core/dev_knowledge.py`, the Knowledge Vault, `core/links.py`, `core/life_events.py` | Built |
| Research | `core/web_search.py` and `core/online_lookup.py` (his own search engine), the UAL's Research and Verify, World Intelligence watches, her browser behind its gate | Built |
| Approval and permission | `core/actions.py` (propose, approve, execute, record, undo), `core/grants.py` (five tiers; nothing she reads can grant), `core/action_effects.py` (reach and reversibility), `core/change_history.py`, `core/browser_safety.py` | Built |
| Stop | `core/stop.py` ("stop", "stop everything") | Built |
| Deliverables | `core/creations.py` (versioned screens with publish and rollback), the lab's branches, `core/art_studio.py`, plans and cut lists, drafts of email | Built for those kinds; no general artifact store |
| Observability | `core/agent_activity.py` (the Dashboard's card), `core/turn_trace.py`, `core/answer_ratings.py`, `core/loops.py`, `core/operating_journal.py`, the Fix-It Log | Built |
| MIA Forge (apps) | Planned (M7), not built | — |
| A teams interface | Agent Activity's card and the dev window's council | Seeds only |

**Gaps, in order of how much everything else waits on them:** (1) the team and its workspace; (2) tasks with
dependencies (shared with UI-7); (3) structured contributions instead of chat; (4) a registry entry that says what
an agent can *do*, not only what it knows; (5) a general deliverable record; (6) artifact tools.

## 3. What each word means (deliverable 3)

| Word | What it is | Where it lives |
|---|---|---|
| **Model** | An engine that turns a prompt into text or a picture. Has a provider, a cost, limits, and strengths. Knows nothing about MIA | `work/agents.json` providers; Ollama |
| **Tool** | One thing MIA can do, in code, with a tier: search, read a page, compute a cut list, propose an action. Tools do; models only say | the tool registry and app manifests |
| **Agent** | A *role*: a charter (what it covers), its limits (what it never does), the tools it may call, the knowledge it reads first, the kinds of task it takes, and how its work is judged. Not a process and not a model: the same model can serve six agents, and an agent's model can change | the agent registry (section 4) |
| **Department** | A label grouping agents for people to browse. Carries no behaviour | a field on the agent |
| **Team** | The agents chosen for one objective, with one lead, for as long as that work lasts | a team record on a project |
| **Coordinator (lead)** | MIA herself, in code plus one model call per decision: she holds the objective, the task list and the budget. Not another agent that could be argued with | `core/teams.py` (proposed) |
| **Workspace** | The structured record of a team's work: the brief, findings, conflicts, decisions, tasks, deliverables, approvals | a personal store per project |

The rule that keeps this one intelligence rather than a crowd: **agents never talk to Zac and never act.** They
write contributions into the workspace. MIA reads the workspace and speaks, proposes and reports, as she does now.

## 4. Schemas (deliverable 4)

All are dataclasses in code and JSON at rest, as every MIA store is; the registry is code (like `SPECIALISTS`), so a
test checks every tool, skill and loop an agent names is real.

**Agent** (extends `Specialist`; existing fields unchanged):

| Field | Meaning |
|---|---|
| `id`, `name`, `charter`, `limits`, `words`, `skills`, `tracks`, `loops`, `starts_from` | as today |
| `department` | research, engineering, software, design, fabrication, business, homestead |
| `task_types` | which of: research, compare, design, estimate, review, safety_review, write, build_code |
| `tools` | tool names it may call; all must be tiered observe or suggest, or prepare-in-workspace (section 6) |
| `needs` | what the model must be able to do: `reasoning` (low, medium, high), `vision`, `code`, `local_only` |
| `reviews` | agent ids whose work it is qualified to review |
| `caveat` | the sentence attached to its output where a professional is needed ("not a substitute for a licensed electrician") |

Evaluation history is *not* on the agent: it is computed from workspaces (section 8), so nothing an agent writes
can raise its own standing.

**Team:** `team_id`, `project_id`, `objective` (his words), `brief` (the structured version he confirmed),
`level` (moderate, complex, major), `members` [{agent_id, why, model_role}], `budget` {calls, spent},
`may_send` (what he approved leaving the device: nothing, the brief, the brief and named records), `status`
(proposed, working, waiting_on_you, reviewing, delivered, stopped), `created`, `run_id` (its run record).

**Task:** `task_id`, `team_id`, `agent_id`, `type`, `title`, `asks` (the question, with refs to workspace entries
it should read), `depends_on` [task_id], `acceptance` (what done means, checkable), `review_by` (agent id or
"you"), `status` (waiting, ready, working, needs_review, accepted, rejected, failed, dropped), `attempts`,
`output` [entry_id].

**Workspace entry** (the structured replacement for chat; one small record each):

| `kind` | Carries |
|---|---|
| `finding` | a claim, its `basis` (source, computed, assumption) and `sources` |
| `constraint` | something another agent's work must respect ("no rigid part over 12 mm at the temple"), with `affects` [agent ids] |
| `question` | to an agent, the lead, or Zac |
| `recommendation` | a choice, the options considered, why |
| `conflict` | two entries that disagree, both kept, with what would settle it |
| `review` | a verdict on a task's output (accept, change, reject), the defects found |
| `decision` | who decided (always the lead under a rule, or Zac), from which entries |
| `risk` | what could go wrong, how bad, what reduces it |
| `deliverable` | a file or record, its kind, version, the task that made it |

Every entry has `by` (agent id and the model that wrote it), `at`, `task_id`, `refs`, and `status` (derived,
reviewed, confirmed by Zac, withdrawn), the same honesty the specialists' notebooks already keep.

## 5. The workspace and how work flows (deliverables 2 and 5)

```
his words ──▶ triage (code + local model) ──▶ a team is PROPOSED: disciplines, members and why,
                                              what it would cost, what would leave the device
                     │                                   │ his yes (or changes)
                     ▼                                   ▼
            simple / moderate:                    brief confirmed ──▶ tasks with dependencies
            answered as today                             │
                                                          ▼
                                     ready tasks run, one model call each, reading only the
                                     entries they depend on; each writes entries
                                                          │
                              constraints and conflicts re-open the tasks they affect
                                                          │
                                     review tasks (a different agent AND a different model)
                                                          │
                                     the lead assembles the report from accepted entries
                                                          ▼
              what was done, what isn't, decisions, costs, risks, files, next steps ──▶ Zac
```

- **One store per project** (`teamwork.json` in the person's folder, a personal store; sealed, atomic, in the
  durable history). The project already owns its needs, prices and plans; the workspace links to them by ref
  (`core/links.py`) and never copies a record.
- **Agents retrieve, they aren't fed.** A task's prompt is: the agent's charter and limits, the brief, the entries
  its `asks` and `depends_on` name, and its acceptance criteria. Never the whole workspace. This is the council
  floor's `context_for` rule, kept.
- **Findings influence each other through `constraint` and `conflict`,** not through conversation: a constraint
  naming an agent re-opens that agent's accepted task (once; a second re-open goes to the lead, a third to Zac),
  so the textile finding really does move the speaker layout, and a loop can't run away with the budget.
- **Quantities and money are computed in code** where a calculator exists (`core/build_calcs.py`,
  `core/price_book.total_cost`); a number a model produced is marked `basis: assumption` until checked.
- **The lead decides only by rule** (an accepted review; the only option within budget and constraints).
  Anything else that matters becomes a question to Zac, with both sides.
- **A team is a run:** it appears in "what's running", stops on "stop" like any run, and after a restart says where
  it was. Nothing new for the stop to learn.

## 6. Permissions and approval (deliverable 6)

The handoff's five levels map onto what MIA already enforces; no new permission system.

| Handoff level | In MIA | Who may |
|---|---|---|
| 1 Think | observe, suggest tools | any agent, inside a team he started |
| 2 Create | writing entries and deliverables **inside the workspace**; code only in a lab worktree | any agent whose `tools` list it |
| 3 Modify | an action proposal on the contract; a lab branch waiting for merge | proposed by the lead only; Zac approves |
| 4 Act | `act_with_approval` kinds: buy, send, publish, operate a device | proposed by the lead only; Zac approves each |
| 5 High-impact | the same, with reach "system" or "outside" and "can't be undone" said on the card; some kinds are tier *never* | Zac only; never a standing grant |

Rules that hold whatever a model writes:

1. **An agent has no grants and can hold none.** A team's ceiling is level 2. `grants.require` already refuses
   anything MIA starts herself above suggest without a grant, and there is no action that gives one.
2. **Proposing is not authorizing.** An agent's "we should order these drivers" is a `recommendation` entry. Only
   the lead turns entries into a proposal, only on the action contract, and only Zac's press approves it.
3. **Everything a model or a web page wrote is outside text.** Entries are framed as information when another
   agent reads them; an instruction inside one changes nothing (the UAL's rule, already tested).
4. **Nothing leaves the device without his say** (`may_send`). The default sends a cloud member the brief and
   entries written by other agents, never his records; a task that needs a record names it and waits.
5. **No agent edits the registry.** Charters, limits, tools and caveats change by commit, reviewed like code.
6. **Safety reviewers can block.** A `safety_review` task that rejects stops the dependent tasks until Zac sees it.
7. **Professional limits are said, not implied:** electrical, battery, structural, legal and medical output carries
   the agent's caveat on the report and on any deliverable.
8. **The audit trail is the workspace plus the action record plus the run record.** All three already exist.

## 7. Models and resources (deliverable 7)

- **An agent states needs; a router picks a model.** `needs` against what each configured role can do
  (`work/agents.json`), preferring: local when `local_only` or when the task touches his records; otherwise the
  cheapest role that meets `reasoning`; never a member resting at its usage limit.
- **Budget first.** A team is proposed with a number of model calls (as the council floor already prices a turn),
  shown before he says yes. The lead can't exceed it; at 80% it reports and asks.
- **Author and reviewer differ in model**, not only in agent (DEC-0174). Two agents on one model agreeing is not
  independent review; where only one capable model is available, the report says "not independently reviewed".
- **Disagreement is kept.** A council-style second opinion on a hard decision writes its own entries; conflicts
  stay in the workspace and in the report. Agreement is never reported as proof.
- **The GPU is one.** Local tasks queue; a team run yields to a conversation (homeostasis already eases off
  deferrable work).
- **Honest fallback:** with no cloud member available, a complex team is not started; MIA says so and offers what
  the local model can do (the brief, the disciplines, the open questions, a research plan).

## 8. Quality, review and learning (deliverable 8)

| What | How |
|---|---|
| Is a claim supported? | `basis` on every finding; a fact-check task on the ones a decision rests on (the UAL's Verify) |
| Is a deliverable right? | its task's `acceptance`, checked by `review_by`; code by the lab's suite |
| Did the result meet the objective? | the lead's final check against the brief's success criteria; then Zac's own verdict |
| How good is an agent or a model at a task type? | computed from workspaces: accepted on first review, rejected, re-opened by a constraint, Zac's corrections. Shown on its profile; used by the router as a tiebreak only |
| What is kept for next time? | on a delivered project, the lead drafts (a) notes for the specialists' workbooks, *derived* until Zac confirms; (b) a **team template**: disciplines, task graph, the constraints that mattered. A template is offered next time, never applied silently, and says which project it came from |
| What may never learn by itself | charters, limits, tools, caveats, permissions |

Each gets a loop in `core/loops.py` (team outcomes; template reuse), as DEC-0094 requires of every process.

## 9. Integration and roadmap (deliverables 9 and 10)

| Phase | What | Builds on | Model |
|---|---|---|---|
| **T0** | This document, reviewed; Q-53 to Q-58 answered | — | Fable |
| **T1 Registry** | `Specialist` gains department, task types, tools, needs, reviews, caveat; the 16 are filled in; a coordinator-free "ask the right specialist, with one reviewer" (the handoff's *moderate* level). Registry page | `core/specialists.py` | Opus, Fable reviews |
| **T2 Workspace** | The team and entry stores on a project; entries by hand and by voice ("note a constraint..."); the Project page shows them | projects, links, change history | Opus |
| **T3 Coordination** | Triage and the team proposal; tasks with dependencies; sequential execution on the run record; the budget; the stop | **UI-7** (plans across apps: build the task graph once, for both), `core/runs.py`, council floor | Opus, Fable reviews (it touches grants) |
| **T4 Collaboration and review** | constraint and conflict re-opening; review tasks on a different model; the blocking safety review; the report | T3; DEC-0174 | Opus, Fable reviews |
| **T5 Deliverables** | a deliverable record (versioned, linked to task and project); first artifact tools, chosen by the pilot project (likely: a document and a spreadsheet writer, then OpenSCAD for printable parts, since it is text a model can write and code can render) | creations, the lab, Forge (M7) | Opus |
| **T6 Teams page** | overview, workspace, agent profiles, conflicts, what's running, approvals; on the web frame, phone and glasses cards | Agent Activity, the shell | Opus builds, Muse's look |
| **T7 Learning** | outcomes per agent and model; templates; workbook notes | loops, specialists' workbooks | Opus, Fable reviews |
| **T8 New specialists** | one at a time, when a real project needs one that the 16 don't cover | T1 | either |

T1 and T2 are useful by themselves and need no cloud model. T3 onward is where Q-53 bites.

**Not proposed:** the handoff's ~45 named agents as a starting set. A charter is cheap to write and expensive to
make true: each needs limits, a caveat, tools and a way to be judged. Start with the 16 that exist plus the few a
pilot project needs (Q-55), as the handoff's own phase 8 says.

## 10. Risks worth naming

| Risk | Answer |
|---|---|
| Confident, wrong engineering (a battery pack, a mains circuit) | basis on every claim; computed numbers where a calculator exists; a blocking safety review; the caveat; the first prototype is always the low-energy one |
| Cost runs away | the budget is approved up front and enforced in code; re-opens are capped |
| His data reaches a cloud model | `may_send`, default nothing of his; shown on the proposal; logged per call |
| A planted instruction in a web page steers the team | entries are outside text; agents can't act; only the lead proposes, only Zac approves |
| Theatre: many "agents", one model agreeing with itself | reviews need a different model or say they weren't independent; the report counts calls and models honestly |
| A parallel system grows beside projects, runs and the council | one store, linked by ref; a team is a run; the council floor's gate is reused, not copied |
| A casual idea becomes a project | a team is only ever proposed; nothing starts without his yes (Q-54) |

## 11. Testing requirements (deliverable 11)

- **Registry:** every agent's tools, skills, tracks, loops and review targets exist; no agent lists a tool tiered
  above its ceiling; every agent in a safety-relevant department has a caveat.
- **Triage:** fixtures of requests sorted simple, moderate, complex; a brainstorm never proposes a team unasked.
- **Team proposal:** the hoodie request names its disciplines from the registry's words, picks the smallest covering
  set, and states cost and what would be sent, before anything runs.
- **Tasks:** a task runs only when its dependencies are accepted; a failure retries to its limit then stops its
  dependents and says so; the graph can't contain a cycle.
- **Context:** a task's prompt holds only the entries it names (asserted on the prompt); never a whole workspace.
- **Influence:** a constraint naming an agent re-opens that agent's task once; the cap holds.
- **Conflict:** two disagreeing recommendations both appear in the report.
- **Review:** a reviewer on the same model as the author is refused or marked not independent; a rejecting safety
  review blocks.
- **Permissions:** a sweep proves no agent tool can change a record outside its workspace; a planted instruction in
  an entry changes nothing; a `recommendation` to buy creates no proposal; `may_send: nothing` sends no record
  (asserted on the outgoing prompt).
- **Budget:** the run stops at its budget; "stop" ends a team at its current task with nothing half written.
- **Stand-in models throughout** (scripted answers); nothing in the suite touches the network.
- **One end-to-end pilot** on a real project of Zac's, judged by him, before T5.

## 12. Decisions for Zac (deliverable 12)

Each with its plain meaning and my recommendation. Proposed decisions DEC-0197 to DEC-0199 follow his answers.

| | Question | Recommended |
|---|---|---|
| **Q-53** | May a team's specialists run on the cloud models you already use for the council (Claude, Codex, Copilot, on your accounts)? Without them, a team can organise work but can't do real engineering thinking; with them, each project spends some of your usage and sends them the project brief | Yes, for teams you start, with a call budget shown first and nothing of your own records sent unless you say so for that project |
| **Q-54** | Does a team ever start by itself? | No. MIA may say "this looks like it needs an acoustic engineer, an electrical engineer and a textile engineer: shall I put a team on it?", and starts only on your yes. You can always ask for one |
| **Q-55** | Which real project is the pilot? The first team should be judged on something you actually want | The smart greenhouse: your records for it already exist (needs, plans, the node), the specialists are closest to it, and it risks less than a wearable with a battery. The hoodie second |
| **Q-56** | Start with the 16 specialists MIA has and add others as projects need them, rather than writing all ~45 now? | Yes |
| **Q-57** | For electrical, battery, structural and legal work, the team's output is a draft that says a qualified person must check it, and a safety review can block a design until you've seen it. Agreed? | Yes |
| **Q-58** | Where does this sit in the queue? It shares its task engine with "plans across apps" (UI-7) | T1 and T2 on Opus now, alongside the other Opus work; T3 after UI-7, so the task engine is built once; MIA OS Prompt 06 unchanged |

**Proposed (not approved):**
- **DEC-0197:** An agent is a role (charter, limits, tools, needs, caveat) in a code registry extended from the
  specialists; never a process, a model or a holder of grants. Agents write to a workspace; only MIA speaks,
  proposes and reports.
- **DEC-0198:** A team is proposed, costed and started only on Zac's yes; it is a run on a project, with a
  workspace of structured entries; its ceiling is creating inside that workspace and the lab.
- **DEC-0199:** Review is independent only across models; disagreement is kept and shown; what a team learns
  becomes derived notes and offered templates, never a change to a charter or a permission.
