# MIA Development Ecosystem: Phase 0 audit and proposal (MIA-DII)

*Claude, 2026-11-03, for Zac's review, in answer to "MIA Development
Ecosystem: Master Architecture & Implementation Specification". Audit and
proposal only: nothing here is built. It builds on
`docs/PERSONALITY_AND_ECOSYSTEM_AUDIT.md` (Audit B), which already inventoried
self-knowledge, testing and monitoring; this goes further into agents,
providers, tasks and permissions.*

**Where the evidence comes from.** The repo as it stands at `97d81df`, and
what's installed on this PC (checked, not assumed). I haven't tested any
provider's API, and I haven't checked prices beyond what's noted as known.

---

## 1. The headline

Most of the spec already exists **as a process**, and almost none of it
exists **as a system**.

The team already collaborates through one shared, version-controlled
knowledge base (`docs/COLLABORATION.md`): decisions (`DECISIONS.md`, 67, each
with who proposed and approved it), questions (`QUESTIONS.md`), handoffs
(`HANDOFFS/`, 81), the current state, the roadmap, and a build queue. That is
the spec's shared knowledge base, provenance and approval trail, kept by hand.

What's missing is the layer that makes it operable: tasks a program can read,
agents that can be assigned and tracked, and a view over all of it.

**So the recommendation is the opposite of a new platform:**
1. **Make what exists machine-readable.** No new database: the repo stays the
   single source of truth.
2. **Then add one orchestration loop on top** of the lab MIA already has
   (`core/dev_lab.py`), which runs Claude Code headless in isolated git
   worktrees, behind approval.

## 2. Inventory

| Capability | State | Where |
|---|---|---|
| Shared knowledge base, provenance, approvals | **Implemented, verified** (as Markdown) | `docs/COLLABORATION.md`, `DECISIONS.md`, `QUESTIONS.md`, `HANDOFFS/`, `CURRENT_STATE.md` |
| Task management | **Incomplete**: prose lists, not queryable | `NEXT_SESSION.md` (build queue), `ROADMAP.md` |
| Agent execution, isolated, behind approval | **Implemented, verified, single agent** | `core/dev_lab.py`, `tools/lab.py` (DEC-0058): proposal → git worktree → Claude Code headless → test suite → approve |
| Multi-agent orchestration | **Missing** | Each Claude session runs on its own; another session's work was only found through `git status` (2026-11-02) |
| Agent and role registry | **Missing** | Roles are a table in `COLLABORATION.md` |
| Provider adapters | **Incomplete** | Claude Code (the lab, via CLI). Ollama, llama.cpp (`core/llm_manager.py`, `core/local_model.py`). No OpenAI or Copilot |
| Model registry | **Implemented, partial** | `core/model_registry.py` (which model, from the runtime), `core/model_bench.py`, `tools/pc_model_check.py` |
| Model routing | **Implemented, partial** | `llm_manager`: home PC, then the phone's own model; not by task |
| Benchmarks and evaluation | **Implemented, verified** | `tools/intelligence_check.py` (112 questions), `pc_model_check.py` (213 tool choices), `conversation_check.py` (37 conversations) |
| Observability | **Incomplete** | `logger.py`, `failure_log.py` (stumbles), `turn_trace.py` (every turn, since today), `answer_ratings.py` |
| Tool registry | **Implemented** | `core/assistant_actions` registry (~175 tools), `core/capabilities.py` |
| Capability discovery and install | **Partial** | `core/module_validator.py` checks a module before install; no discovery, sandbox or revocation |
| Permissions | **Implemented, for MIA herself** | `core/actions.py` (Propose → Approve → Execute → Record → Undo), child accounts, the relay's allowlist. No equivalent for development agents |
| Background execution | **Implemented, scattered** | Qt timers and per-module threads; no job queue |
| Databases | **By design: JSON files** per store, written atomically (`core/atomic_write.py`), live refresh, undo | No SQL anywhere |
| Testing | **Implemented, verified** | 291 test files, ~4,760 tests; 6 CI workflows |
| Self-knowledge | **Implemented, partial** | `capabilities.py`, `self_docs.py`, `inspection.py`, `fact_owners.py`, `links.py` |
| Development interface | **Missing** | No dashboard; the lab is a CLI |
| Pi staging | **Planned** | `deploy/` (kiosk service), DEC-0015 priority 4 |

**Duplicated:** the to-do list lives in three places (`NEXT_SESSION.md`'s
queue, the roadmap's planned items, and lab proposals). **Disconnected:** the
lab doesn't know about decisions or handoffs, and failures and ratings don't
become tasks. **Obsolete:** `docs/ASSISTANT_AUDIT.md` and
`INTELLIGENCE_AUDIT.md` overlap later audits; worth marking superseded, not
deleting.

**Found and fixed along the way (not foundational):** none today. Open
findings are in the personality audit's sections E to G.

## 3. Gaps that should have existed earlier

1. **Tasks as records.** One file per task, with status, owner,
   dependencies, branch and evidence. Everything in the spec's acceptance
   list hangs off this.
2. **Knowing who else is working.** Two Claude sessions edited the same
   files on 2026-11-02. A lightweight claim ("I'm on these files, task X")
   would have prevented the overlap.
3. **Evidence on completion.** "Done" today means a commit message. A task
   should close only with its test run, its commit and its checks attached.
4. **A dev-agent permission model.** MIA's actions are well governed; the
   agents that build her aren't, beyond the lab's worktree.
5. **Not foreseen by the spec:**
   - **A cost and usage meter.** Two usage limits were hit on 2026-11-03.
     Agents should know their budget before they start.
   - **A reproducible environment.** This PC's test suite fails in places on
     unchanged code (Tesseract, PDF reading). CI and the lab need the same
     baseline, or "the tests pass" means different things.

## 4. Technology comparison

| Need | Options | Recommendation |
|---|---|---|
| Task store | GitHub Issues; Linear; files in the repo | **Files in the repo** (`work/tasks/*.md`, front matter) as the source, mirrored to GitHub Issues when a login exists (DEC-0067's choice). Works offline and in every session, and keeps history in git |
| Orchestration | LangGraph, CrewAI, AutoGen; a small native loop | **Native**, extending `dev_lab`. The frameworks bring heavy dependencies and their own state store, which would compete with the repo |
| Agent-to-agent messages | A message bus; files | **Files**: handoffs and task comments, as the team works now. The Claude sessions' own `SendMessage` can be used where present |
| Observability | OpenTelemetry, Langfuse, Phoenix; native | **Native first** (turn traces exist). Add OpenTelemetry export later if a viewer is wanted; Langfuse and Phoenix each need a server (Docker isn't installed) |
| Sandboxing | Docker; git worktrees; Windows Sandbox | **Worktrees** for code (the lab does this). Docker only if a provider needs a full sandbox |
| Dashboard | A new app; MIA's own web front end | **MIA's web** (`web/`, served by `server/app.py`), as an admin-only screen. No new frontend stack |

## 5. Proposed architecture

```
                   ┌──────────────────────── Zac ────────────────────────┐
                   │ approves decisions, merges, deploys                 │
                   └───────▲─────────────────────────────▲───────────────┘
                           │ approval queue               │ dashboard (web/dev.html)
┌──────────────────────────┴─────────────────────────────┴────────────────┐
│ The repo: the one source of truth                                        │
│  docs/DECISIONS · QUESTIONS · HANDOFFS · CURRENT_STATE (as today)        │
│  work/tasks/T-0001.md ...  (new: status, owner, deps, branch, evidence)  │
│  work/agents.json          (new: roles → provider + model + permissions) │
│  work/activity.jsonl       (new: append-only: who did what, when)        │
└──────▲──────────────────────────────▲───────────────────────────────────┘
       │ read and claim                │ results, evidence
┌──────┴───────────────────────────────┴──────────────────────────────────┐
│ tools/work.py: the orchestrator (extends core/dev_lab.py)                │
│  pick a ready task → check permissions → open a worktree → run its agent │
│  → run tests → attach evidence → independent review → approval queue     │
│  checkpoint after every step, so an interrupted task resumes             │
└──────┬──────────────┬───────────────┬──────────────────┬───────────────┘
   Claude Code     Codex CLI      Copilot (GitHub)     Ollama (local)
   (headless)     (if installed)  (via issues/PRs)     (MIA's models)
```

**How one task flows:**
1. A task file is created, by Zac, by an agent proposing one, or from a
   Fix-It issue.
2. It becomes **ready** once its dependencies are done.
3. The orchestrator **claims** it, recording the claim in activity.
4. It opens a branch and worktree.
5. It runs the assigned role's provider, with only that task's context.
6. It runs the checks and attaches the evidence.
7. A **different** provider or role reviews it.
8. It goes to the approval queue.
9. Zac approves, and it merges.

Each step is recorded, so a crash resumes from the last one.

## 6. Provider feasibility

| Provider | How it could join | On this PC now | Notes |
|---|---|---|---|
| **Claude Code** | Headless CLI in a worktree (the lab already does it) | **Installed** | Feasible today. Usage limits apply (hit twice on 2026-11-03) |
| **ChatGPT / OpenAI** | The Codex CLI (headless, signs in with a ChatGPT account), or the API with a key | Not installed | Feasible once Zac installs it and signs in. A key never goes in project files |
| **GitHub Copilot** | Copilot's coding agent works from GitHub issues and opens PRs; Copilot CLI is newer | Not installed; no GitHub login here | Feasible through GitHub once Issues are set up (blocked, as above) |
| **Ollama (MIA's models)** | Already integrated | **Running** | Good for cheap jobs: triage, summaries, first-pass reviews. Not for writing code to her standard |

Providers differ, so each adapter declares what it can do: write code, review,
research, or run only. Roles are matched to what's declared, never assumed.

## 7. Multi-agent workflow

**Roles** are configurable entries in `work/agents.json`: a role (Software
Engineer, QA Engineer, Security Auditor...), a provider and model, a
permission tier, and a context recipe (which docs it reads). The spec's twelve
start as entries; none is hardcoded.

**Rules:**
1. **One claim per task.** A claim lists the files it expects to touch;
   overlapping claims wait.
2. **The reviewer is never the author.** Different provider where possible,
   different role always. The security reviews done today (5 rounds, each
   finding what the last missed) are the model.
3. **Handoffs stay files.** An agent asks another through a task comment or a
   handoff, never a private channel.
4. **Escalation is a question.** Anything outside the task's scope becomes a
   `QUESTIONS.md` entry for Zac, and the task waits.

## 8. Security and permissions

The spec's tiers, mapped to what each can touch:

| Tier | Can | Can't |
|---|---|---|
| Read | Read the repo and docs | Anything else |
| Propose | Write task and handoff files | Code |
| Experiment | Change code in its own worktree; run tests | Push to master, touch secrets, reach production |
| Review | Comment and approve a **candidate** | Its own work |
| Approve | Zac only | — |
| Deploy | Run a named, approved procedure | Anything not in it |

**Plus:**
- **Secrets:** none in tasks, worktrees or agent context. `local.properties`,
  `config/config.json`, and Plaid's and Meta's keys stay where they are,
  outside what agents read.
- **Protected paths:** the lab already keeps a list. It extends to the
  safety floor, the relay, approvals, and permissions themselves.
- **Audit and recovery:** `activity.jsonl`, append-only; every change is a
  commit, so any of it can be reverted.

## 9. Roadmap (dependency-aware)

| Step | Builds | Unlocks | Size |
|---|---|---|---|
| **1. Tasks as records** | `work/tasks/`, the format, `tools/work.py list/new/claim/done`, the current queue migrated in | Everything below | Small |
| **2. Activity and evidence** | `activity.jsonl`; closing needs its evidence | Tracking, recovery | Small |
| **3. Agent registry and the loop** | `work/agents.json`; the orchestrator on the lab; Claude Code first; checkpoints | Delegation, resumption | Medium |
| **4. Independent review** | A reviewer role, run by a different model (local first, then Codex) | The review workflow | Medium |
| **5. Dashboard** | `web/dev.html`: tasks, agents, activity, the approval queue, history search | One view over contributors | Medium |
| **6. More providers** | Codex CLI; Copilot through GitHub | Mixed teams | Medium, needs Zac's sign-ins |
| **7. Intelligence lab** | Reproducible model runs: the three benchmarks, versioned settings, compare and roll back | Model work, fine-tuning | Medium |
| **8. Self-development** | MIA proposes tasks from her failure log, ratings and inspection | Her own improvement, behind approval | Medium |
| **9. Capability discovery** | Registry, sandbox, license and security review, revoke | New tools, safely | Large, last |

Pi staging slots in once there's a release to stage (DEC-0015).

## 10. MVP

Steps 1 to 5, Claude Code and Ollama only. That meets the spec's acceptance
list except "assignment to different AI providers" beyond those two, which
step 6 adds.

## 11. Acceptance tests

Integration tests, run in a scratch repo:
1. A task created, made ready by its dependency, claimed, worked in a
   worktree, closed with evidence.
2. An interrupted task resumes from its last checkpoint.
3. Two overlapping claims: the second waits.
4. Review by a different role; self-review refused.
5. Nothing reaches master without Zac's approval.
6. The dashboard shows every agent, task and handoff, and history is
   searchable.
7. No secret ever appears in task context or activity (a planted fake secret
   is checked for).

## 12. Decisions proposed (for Zac)

- **DEC-0068 (proposed):** MIA-DII builds on the repo as the one source of
  truth: tasks as files, an append-only activity log, and the orchestration
  loop on `core/dev_lab.py`. No new database or orchestration framework.
- **DEC-0069 (proposed):** the six permission tiers above for development
  agents; Approve is Zac's only; secrets and protected paths are never in an
  agent's context.
- **DEC-0070 (proposed):** the MVP is steps 1 to 5 with Claude Code and
  Ollama; Codex and Copilot join at step 6, once installed and signed in on
  this PC.

**Where I'd challenge the spec:**
- **The "universal development chat" and "agent-to-agent communication"
  should be files, not a live chat.** Live chats between agents are hard to
  review and easy to lose; files are what made today's work recoverable.
- **The Intelligence Laboratory's long list** (pruning, distillation,
  weight-space programming, speculative decoding) is research for later. The
  first real model work is the fine-tune from Zac's ratings, and that needs
  step 7's reproducible runs, not a broad lab.
