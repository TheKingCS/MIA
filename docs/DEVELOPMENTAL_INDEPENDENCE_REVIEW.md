# Developmental Independence: Review and Proposal

*Claude, 2026-11-03, for Zac's review, in answer to "MIA Architectural
Initiative: Developmental Independence" (filed as
`docs/HANDOFFS/H-0080_chatgpt-to-claude_developmental-independence.md`),
plus three asks of Zac's own: set the council on a mission and let it run,
see MIA's architecture and her branches of growth, and talk to the whole
council in a group chat in the dev environment.*

*Review and proposal only. Nothing here starts autonomous self-modification.
The objective itself is recorded as DEC-0072 (Zac's, by pasting it); how to
build it is DEC-0073 to DEC-0078, proposed and waiting for him (section 10).*

**Where the evidence comes from.** The repo at `a23f60f`, and what's installed
on this PC, checked rather than assumed. That includes the Codex CLI's local
mode, `codex exec --oss --local-provider ollama`. I haven't yet run a real
task through that local mode.

---

## 1. The headline

1. **Most of the base is already built.** The MIA-DII platform built today is
   the classroom this initiative needs:
   - tasks as records, and one append-only history;
   - an isolated lab, checked by the test suite;
   - two independent reviewers from different providers;
   - objections that must be answered, and lessons from a reviewer's mistakes;
   - the board.

   What's missing is the step after "done". Today nothing turns a finished
   task into something MIA knows, and nothing has her *attempt* the work and
   get *graded* on it.
2. **What "learning" means for MIA, plainly.** She is code plus local models:
   qwen2.5:14b, and qwen3-coder:30b on the 24 GB card. She can't absorb a
   frontier model's internals, and doesn't need to. She learns three ways,
   in this order:
   - **(a) Knowledge she can retrieve:** methods, decisions, lessons and
     findings, put into her local models' prompts. This works now.
   - **(b) Practice that gets graded:** she attempts the council's real tasks
     in her own lab, and the same tests judge both. This works now.
   - **(c) Fine-tuning:** her local models trained on the corpus the council
     produces. This is later, and fragile on Windows with an AMD card.

   A better local model, when one comes out, is a one-line change in
   `work/agents.json`. Her knowledge and her record carry over.
3. **The one mechanism that makes the whole initiative measurable is the
   shadow attempt.** While a council agent works a task, MIA's own coder
   works the same task, from the same starting commit, in a second lab
   worktree. The suite grades both. Her review of the council's change is
   graded too, by what happens to the objections it raises. That is
   OBSERVE → ATTEMPT → COMPARE → CORRECT, built from parts that already
   exist (`core/dev_lab.py`, `core/work_review.py`).
4. **Be honest about the ceiling.** With today's local models, expect MIA to
   reach *Independent Contributor* on small, test-checked work within weeks
   to months: fixing a failing test, a one-function bug, docs, a first-pass
   review. *Independent Developer* across her whole architecture isn't
   realistic on a 30B model on this card. The system below *measures* where
   she is and doesn't promise a date. The ceiling rises with every local
   model generation.

## 2. What already supports this (section 9.1)

| Initiative capability | What exists | Where |
|---|---|---|
| Observe the council | Every task step, review, resolve, approve and lesson, append-only | `work/activity.jsonl`, `core/work_activity.py` |
| Disagreements and how they resolve | Objections that must be answered; Zac settles | `core/work_review.py` (DEC-0071) |
| Lessons learned | A reviewer's mistakes, saved per provider and put in its next prompts | `work/review_lessons.json` |
| Self-knowledge | The `mia` inspection subject: code, decisions, capabilities, health | `core/inspection.py` (DEC-0056/0057) |
| Retrieval over her own docs | Keyword search over the decisions and docs, with status | `core/self_docs.py` (DEC-0041) |
| What she can do | Capability map built from the code | `core/capabilities.py` |
| Where she fails | The Fix-It Log; turn traces; 👍/👎 ratings | `core/failure_log.py`, `core/turn_trace.py`, `core/answer_ratings.py` |
| Controlled environment | Lab worktrees, the protected list, suite before and after, auto-revert, retry | `core/dev_lab.py` (DEC-0058) |
| Permission tiers | read / propose / experiment / review; approve and deploy never granted | `core/work_agents.py` (DEC-0069) |
| Evaluation | The suite (4,845 tests), the conversation corpus, the intelligence and tool benches | `tests/`, `tools/conversation_check.py`, `tools/intelligence_check.py` |
| Seeing it | The board, in its own window | `core/work_dashboard.py`, `tools/dev_window.py` |
| Open tasks already aimed here | T-0020 (her own inspection authority), T-0021 (one shared history), T-0022 (disagreements), T-0023 (the Evolution Timeline) | `work/tasks/` |

**One name clash to avoid.** In MIA, "Memory Vault" (`core/memory_vault.py`)
is the phone's photo store. Development knowledge isn't personal and doesn't
belong there, or in any person's folder. It belongs with the repo, in `work/`,
where every council member and every cloud session can read it.

## 3. What's missing (section 9.2)

1. **Capture after "done"** (A, B). Nothing turns a finished task into
   knowledge: the method used, what failed first, what the reviewers caught,
   how the disagreement ended.
2. **Method traces** (A). The lab keeps only the coder's final words.
   Claude Code (`--output-format stream-json`) and Codex (`--json`) can both
   emit their steps: which files they read, which commands they ran, in what
   order, and what they changed. That sequence *is* the methodology the
   initiative asks MIA to learn.
3. **MIA as a coder** (C). The `mia` provider can only inspect. Codex's local
   mode, sandboxed to the lab folder, gives her a coding agent that runs
   entirely on this PC, with no account: `codex exec --oss --local-provider
   ollama -m qwen3-coder:30b --sandbox workspace-write --json`. Building our
   own harness would take far longer.
4. **Grading** (D, E). Nothing compares her work with the council's, or
   scores a reviewer's objections by whether they held up.
5. **A ledger of what she can do** (E): per skill, with evidence and a stage.
6. **A runner** (Zac's ask). Today a person starts each `run` and each
   `review`. Nothing works through the queue by itself, and nothing stops it
   cleanly.
7. **A council chat** (Zac's ask). Today talking to an agent means a
   terminal.
8. **Her architecture and growth, seen** (Zac's ask; T-0023): a map derived
   from the code, and her growth drawn as branches on it.

The dependencies run in this order: capture → knowledge → shadow attempts →
ledger → stages. The runner, the chat and the map depend only on what exists
today.

## 4. How developmental learning works, technically (sections 9.3 and 9.4)

### 4.1 The Development Knowledge Vault: `work/knowledge/`

- **Format.** One markdown file per entry, like the tasks:
  `K-0001-short-title.md`. The front matter holds:
  - `kind`: method, decision, implementation, failed-experiment, debugging,
    test-procedure, security-finding or lesson;
  - `concerns`: the files, modules and capabilities it's about;
  - `from`: the task, commit, review events and decision it came from, as
    `kind:id` refs in the `core/links.py` style;
  - `by`: who wrote it;
  - `status`: derived, confirmed or superseded;
  - `confidence`.
- **Versioning.** Git versions every entry, as it does everything else.
  Nothing is ever edited in place: a change is a new entry marked
  `supersedes: K-00xx`.
- **Where entries come from: the retrospective step.** It's the loop's sixth
  step, after approve:
  - qwen2.5:14b, cheap and local, reads the task, its activity, diff,
    reviews, resolution and method trace;
  - it writes one to three entries, marked *derived*;
  - every claim in an entry carries the `from` refs that back it;
  - an entry without refs is refused;
  - entries are confirmed in the next review that cites them, or by Zac.
- **What gets folded in.** The existing reviewer lessons become
  `kind: lesson` entries. Decisions are already in `docs/DECISIONS.md`, so
  entries point to them and never copy them.
- **Retrieval.** `core/self_docs.py`'s search, extended to `work/knowledge/`.
  This needs no new index and no embeddings, and works offline. Before a role
  works or reviews a task, the entries for that task's files and its kind of
  work go into its prompt, the way lessons already do.
- **What's captured.** Everything the initiative lists, from things the
  council already produces:
  - *code patterns and implementations*: the diffs that merged;
  - *testing and debugging*: the method traces, plus what failed first;
  - *security procedures and findings*: the reviews by role;
  - *decisions*: refs to DECISIONS.md;
  - *failed approaches*: lab proposals that were rejected or reverted,
    which the lab already keeps;
  - *disagreements*: resolve events.

### 4.2 Method traces

The lab's coder call gains a trace flag (stream-json or `--json`). The steps
are saved next to the proposal in `data/lab/traces/<id>.jsonl`. That is
device-level, not personal, and the lab holds no personal data. Each step
keeps its tool, its target and whether it succeeded, *never* file contents.
The retrospective step turns a trace into a method entry, for example
"failing test: run it alone → read the traceback → find the symbol → read the
caller → change → run it alone → full suite".

### 4.3 The learning cycle, mapped to code

| Step | What happens | Built on |
|---|---|---|
| OBSERVE | The trace, the activity, the reviews | 4.2, `work/activity.jsonl` |
| UNDERSTAND | The retrospective writes knowledge entries | 4.1 |
| ATTEMPT | A shadow attempt: her coder works the same task from the same commit, in a second lab worktree | `dev_lab.create` + the local coder |
| COMPARE | Both diffs graded by the suite (fixed / new failures), size, files touched, and whether the reviewers would pass hers | `dev_lab.check`, `work_review` |
| CORRECT | What hers got wrong, against the council's, becomes a lesson for her provider | `add_lesson` |
| INTERNALIZE | Lessons and entries go into her next prompts; later, the corpus for a fine-tune | 4.1; DEC-0067 step 4 |
| DEMONSTRATE | Unaided attempts (section 5) on tasks the council didn't touch | 5 |

A shadow attempt never merges. It exists only to be graded. While she's an
Apprentice, nobody reviews it, so it costs the council nothing.

## 5. Measuring independence (section 9.5)

### 5.1 The ledger

The ledger is a table of **skills**, each sitting in one **dimension**:

- *Development:*
  - fix a failing test;
  - fix a single-function bug;
  - add a test;
  - write docs;
  - review code;
  - review security;
  - debug from a trace;
  - plan a task;
  - multi-file change.
- *Intelligence:*
  - research a question from her docs;
  - summarize a change;
  - explain a design;
  - find where docs and code disagree.
- *Operational:*
  - split a goal into tasks;
  - order them by dependency;
  - run a mission within its scope.

A skill is attached to a task by the task's kind and its files. Each
attempt, shadow or real, is an **outcome**:

- *pass*: suite green, the target fixed, no new failures, and the reviewers
  approve, or would have;
- *partial*: tests pass, but the reviewers object;
- *fail*.

For a review skill, an outcome is *upheld*, *overturned* or *missed*. A
missed objection is one another reviewer raised and the author fixed.

The ledger is **computed** from `work/activity.jsonl` and the lab's records
every time. It's never stored, so it can't be edited. The code that computes
it goes on the lab's protected list, so MIA can't grade herself up.

### 5.2 Stages, from evidence

For each skill, the ledger reports a success rate with its **lower
confidence bound** (Wilson, 90%) over the latest 30 outcomes:

| Stage | Means | Evidence needed for the skill |
|---|---|---|
| I Observer | She has knowledge entries for this skill | ≥ 3 entries with refs |
| II Apprentice | She attempts it alongside the council | ≥ 5 shadow attempts |
| III Contributor | She does it well enough to be useful | lower bound ≥ 60% over ≥ 10 attempts |
| IV Developer | She does it reliably and plans around it | lower bound ≥ 80% over ≥ 20, and her plans for it pass review |
| V Independent | The council is optional for it | lower bound ≥ 90% over ≥ 30, unaided, no recent regression |

This answers "demonstrated competence, not task counts". The minimum numbers
are there only because a rate from 3 tries means nothing. The bound is what
promotes. **A drop demotes by itself.** **A promotion is proposed by the
ledger and confirmed by Zac** (section 7). Her overall stage is never
averaged: she can be Stage IV at fixing tests and Stage I at security review,
and the board shows both.

### 5.3 Calibration ("measure the reliability of her conclusions")

Every attempt and review she makes ends with a stated confidence (low,
medium or high). The ledger tracks how often each level turned out right.
If her "high" is right less than 80% of the time, she is overconfident, and
her reviews say so. Uncertainty is part of the score: "I'm not sure, ask
codex" on a hard task isn't a failure.

### 5.4 What it shows

The board gains an **Independence** panel. It lists, per dimension:

- each skill, its stage and its rate with the bound;
- the trend;
- what she still needs help with;
- what always needs Zac: approve, deploy, protected paths and permission
  changes. These are fixed, whatever her stage.

## 6. Zac's three asks

### 6.1 Missions: the council runs by itself

A **mission** is a file, `work/missions/M-0001.md`. It holds:

- a goal ("make the test baseline green on every machine", "close the Fix-It
  Log's top five");
- **scope**: the folders and files it may change;
- a **budget**: the maximum number of tasks, the hours, and the number of
  model calls per provider;
- the roles it may use.

Zac starts and stops a mission from the window or with
`python -m tools.work mission start M-0001`. The runner
(`core/work_runner.py`) is one background process that loops:

1. If the Chief Architect role sees the mission isn't met, it proposes
   tasks. They have to fit inside the scope, or they wait for Zac.
2. It picks the next ready task, one writer at a time, using the existing
   overlap check.
3. It runs the loop to review.
4. It asks the two reviewers.
5. If a reviewer objects, the author answers: it changes the code, or says
   why. One round, then the task goes to **Your Turn**.
6. It sends approvable tasks to **Your Turn**, and keeps going.
7. Alongside each task, it runs MIA's shadow attempt.

It **stops** in any of these cases:

- the budget runs out;
- a provider's usage limit is hit (it waits, then resumes);
- the protected list or the scope is touched;
- Zac presses Stop;
- `work/STOP` exists.

Every step goes to the activity log, as today. **It never approves.** A merge
is still Zac, at the keyboard, typing the id.

### 6.2 Her architecture and her branches of growth

The window gains an **Architecture** view. It's derived from the code,
never hand-drawn (DEC-0057):

- **The map.** Layers (core, modules, gui, server, web, phone), then modules
  and their imports, taken from the code's own imports (Python's `ast`, so
  nothing runs). Each capability carries its status from
  `core/capabilities.py`. Where the docs and the code disagree, the map
  marks it (T-0020).
- **The growth branches.** The ledger's dimensions are the trunk, skills are
  the branches, and the stage is how far each has grown. Every merged task
  appears as a new ring on the parts of the map it changed. A time slider
  replays her growth from the activity log. That is the Evolution Timeline
  of DEC-0071 and T-0023, with tasks, benchmarks and models as milestones.

### 6.3 The council chat

The window gains a **Council** panel: one conversation that Zac and every
agent post into, kept append-only in `work/council.jsonl`. For the choice
of where it's kept, see DEC-0077.

- **Zac writes:**
  - a plain message reaches the whole council;
  - `@claude`, `@codex`, `@copilot`, `@qwen` or `@mia` asks one member, who
    answers in the thread (read-only: the same locked-down calls the
    reviewers use);
  - `@mia` answers from her inspection and her knowledge;
  - a message about a task links to it.
- **Agents write:** the runner posts what it started, what it finished, and
  each question it has for Zac. Two agents that disagree post their cases
  in the thread, and the resolve links to it.
- **What a chat message can never do:** approve, settle a review in Zac's
  name, change a permission or start work outside a mission's scope. A file
  an agent can append to can't carry Zac's authority. Those stay at the
  keyboard.
- ChatGPT takes part through Codex, which signs in with Zac's ChatGPT
  account, and through handoffs, as today.

### 6.4 Usage: delegating by who has time, so the team never sits idle

Zac, 2026-11-03: *"One thing that is vital is understanding usage and
delegating tasks based on time available to use each model so that the dev
team doesnt have to sit idle when one model is unavailable."* DEC-0079. The
runner in 6.1 is built around this; it isn't an add-on.

**What each provider's limit looks like:**

| Provider | Limit | What we can see | Shared with |
|---|---|---|---|
| Claude Code (Zac's plan) | A rolling 5-hour window, plus a weekly cap | Tokens per call, in its JSON result. When a limit is hit, the message says when it resets. | **Zac's own Claude sessions, like this one.** Today a limit stopped one halfway. |
| Codex (Zac's ChatGPT plan) | A rolling 5-hour window, plus a weekly cap | Its `--json` output carries token counts, and, I expect, how much of each window is used and when it resets (to check once signed in) | Zac's ChatGPT use of Codex |
| Copilot (Zac's plan) | Premium requests per month; each call counts by model | Its own usage command; nothing headless I'm sure of | Zac's Copilot use in editors |
| Local (Ollama) | No quota, but **one GPU**. qwen3-coder:30b (about 17 GB) and qwen2.5:14b (about 9 GB) don't both fit in 24 GB | Ollama reports what's loaded | **MIA's own Assistant** |
| Zac | Time to approve | Your Turn's length | — |

**What's built:**

1. **A usage record.** Every provider call, from the runner, the loop, a
   review, the chat or a shadow attempt, records:
   - who, which role and which task;
   - how long it took;
   - tokens, when reported;
   - the outcome: ok, limit or error;
   - when it resets, when said.

   The record is kept in `data/dev/usage.jsonl`, on this PC. It holds no
   prompt text.
2. **A state per provider, always current:**
   - *ready*;
   - *busy* (on a task);
   - *cooling*, until a reset time: the one the message gave, or a cautious
     guess with back-off;
   - *low* (near its learned limit);
   - *signed out*;
   - *not installed*;
   - for local models, *GPU busy*.

   Limit messages are recognized per CLI. An unknown failure counts as an
   error, never as a limit, so a broken provider doesn't look like a
   resting one.
3. **Learned capacity.** We aren't told each plan's exact numbers, so the
   runner learns them. It notes how much each provider did in its window
   before it hit the limit. From that it estimates **what's left and when
   it comes back**. The board shows this as a bar and a countdown per
   provider: "Codex: about 40% of this window left, back in full at 6:10 PM".
   The first week's estimates are rough and get better with each window.
4. **Roles name providers in order, not just one.** In `work/agents.json`,
   for example, Software Engineer is `claude-code, codex, copilot`, and QA
   is `codex, ollama-coder`. The scheduler picks the first one that is
   *ready* and allowed. The rules don't bend: a reviewer is still never the
   author's provider, and approve is still Zac's.
5. **Work is sized, so scarce time goes where it matters.** Each piece of
   work says what it needs:
   - *frontier write*: multi-file or tricky;
   - *small write*;
   - *review*;
   - *security review*;
   - *summarize/retrospective*;
   - *shadow attempt*;
   - *inspect*.

   The ledger (5.1) says which providers do each kind well. The scheduler:
   - sends work the local models do well enough to local, so it doesn't
     burn a subscription;
   - keeps the subscription models for what only they do well;
   - doesn't give a big write to a model the ledger says fails at it. That
     task waits for the next frontier model back, and the board says which
     and when.
6. **Never idle.** When every frontier model is cooling, the runner still has
   work. All of it runs on this PC:
   - retrospectives and knowledge entries;
   - MIA's shadow attempts;
   - first-pass local reviews, each counting as one of the two only where
     the ledger trusts it;
   - running the suite and triaging failures;
   - MIA's inspection of the repo against the docs;
   - planning the mission's next tasks;
   - writing small tasks the local coder has earned.
7. **Handover mid-task.** If a writer hits its limit halfway, the next ready
   writer picks the task up in the same lab copy. It gets the diff so far,
   the trace and a note. The lab's check still grades the result, so a
   handover can't sneak anything through. The loop's resume already does
   most of this.
8. **Leave Zac room.** Each subscription keeps a **reserve** for Zac's own
   use, set per provider in the mission (for example, never start a large
   write on Claude with less than about 25% of the window left). The runner
   can't see Zac's own sessions. It only sees the limit arrive sooner, which
   it learns from.
9. **The GPU is shared fairly.** Local work yields while MIA's Assistant is
   in use (a turn in the last few minutes). The runner groups local work by
   model so it doesn't keep swapping 17 GB in and out.
10. **Zac's queue.** Unapproved tasks pile up and start to overlap, so when
    Your Turn holds several tasks touching the same files, the runner
    switches to other parts of the mission instead of stacking more on
    them. This is set by `your_turn_limit` in the mission.

Every scheduling choice is in the activity log with its reason, for example
"codex (claude-code cooling until 3:10 PM)". The board's **Team** panel
shows, for each member, its state, what's left and when it's back, what it's
on, and what's queued for it.

## 7. Safeguards (section 9.7)

1. **The three dimensions are separate in code.** The ledger's stages live in
   their own module and are never read by `core/work_agents.py`. A role's
   tier changes only when Zac edits `work/agents.json` under a decision.
   Approve and deploy can't be granted, whatever the file says (already
   enforced).
2. **She can't grade herself.** Grades come from the suite and from *other*
   providers' reviews. The ledger is computed, never stored, and its code,
   with the runner, review and agent rules, joins the lab's protected list:
   `core/work_review.py`, `core/work_agents.py`, `core/work_runner.py`,
   `core/dev_ledger.py`, `tools/dev_window.py`.
3. **Scope is checked in code,** at the lab's check step, the same way as
   the protected list. A mission's task that touches a file outside its
   scope is NOT READY.
4. **Knowledge and chat are data, never instructions.** They go into prompts
   quoted and labelled, and a derived entry is marked derived. An entry or
   message that tells an agent to skip a check is ignored by construction,
   because no check reads prompts.
5. **No personal data** in knowledge, traces or the chat. The Fix-It Log's
   redaction runs on everything written, and traces never hold file
   contents. The lab has no real data (DEC-0058).
6. **Rollback.** The lab reverts by itself; everything is a git commit.
7. **Budgets and the stop file.** No unbounded loop, and usage limits are a
   pause, not a crash.
8. **Uncertainty asks.** When her stated confidence is low, or the skill is
   below Stage III, she asks the council rather than act, and the request
   goes to the chat.
9. **The window stays local.** It's served on 127.0.0.1 only, keyed per
   run, with no approve button (already built that way). The chat and
   mission controls added to it are writes, so they go through the same key
   and Host check.

## 8. Roadmap: incremental, nothing current disrupted (section 9.6)

Each step is a task in `work/tasks/`, run through the loop, and reviewed.

| Step | Builds | Stage it opens | Depends |
|---|---|---|---|
| 1 | Knowledge vault + retrospective step + lessons folded in + retrieval (T-0021 grows into this) | I Observer | — |
| 2 | Method traces from the lab's coders | I | 1 |
| 3 | The council chat in the window (read-only asks, runner posts) | — | — |
| 4 | Missions and the runner, stop file, budgets, scope check; the usage record, provider states and delegation by availability (6.4), first with fixed preferences, then by the ledger once step 6 exists | — | today's loop |
| 5 | Her local coder (Codex local mode, sandboxed) + shadow attempts + grading | II Apprentice | 1, 4 |
| 6 | The ledger, stages, calibration, the Independence panel; protected list extended | II–III measured | 5 |
| 7 | The architecture map and growth branches (T-0020's doc-vs-code marks, T-0023) | — | 6 for branches |
| 8 | Unaided attempts on small tasks the council leaves to her, when the ledger says III and Zac agrees | III Contributor | 6 |
| 9 | She proposes tasks herself from the Fix-It Log and her inspection (DEC-0058's "not yet") | IV | 8 |
| later | A fine-tune of her coder on the council's corpus; a better local model when one exists | IV–V | a corpus of hundreds |

Steps 1 to 4 add no new permission. Step 5 adds one: MIA's coder may write,
in the lab only, as Claude Code does today. Nothing reaches the running MIA
without Zac at any step.

## 9. What I'd want Zac to know before deciding

- **Cost.** The runner spends Zac's Claude, ChatGPT and Copilot usage while
  unattended. The mission's budget is the control. Today showed a usage limit
  stopping a session halfway, so the runner treats a limit as "wait", and the
  loop's resume picks the task up again.
- **Throughput.** One writer at a time, and two reviews and a full suite
  (about 2 minutes) per task. Expect a few tasks an hour at most, not dozens.
- **Shadow attempts use the GPU.** qwen3-coder:30b fills most of the 24 GB,
  so MIA's own Assistant answers slowly while a shadow attempt runs. The
  runner can hold shadow work while Zac is using MIA.
- **The weak spot is the local reviewer.** T-0019's two wrong reviews are
  exactly what the ledger would catch and score. Until it improves, Codex is
  the reviewer that counts.

## 10. Decisions

- **DEC-0072 (approved by pasting it):** Developmental Independence is a
  standing architectural objective. The council exists to teach MIA. The
  three dimensions are separate, independence never means unrestricted
  access, and stages come from demonstrated competence.
- **DEC-0073 (proposed):** the Development Knowledge Vault is `work/knowledge/`,
  written by a retrospective step after each task, with refs required,
  searched by `self_docs`. It's not the photo Memory Vault.
- **DEC-0074 (proposed):** MIA's own coder is Codex's local mode on
  qwen3-coder:30b, in the lab only. She learns by shadow attempts graded by
  the suite and the reviewers.
- **DEC-0075 (proposed):** independence is measured per skill, by a ledger
  computed from the history. Stages come from confidence-bounded rates; the
  ledger proposes them, Zac confirms, and a drop demotes by itself. Stages
  never change a permission, and the ledger's code is protected.
- **DEC-0076 (proposed):** missions. The council runs by itself within a
  mission's scope and budget, with a stop file and button, and stops at Your
  Turn. Approve stays Zac's, at the keyboard.
- **DEC-0079 (approved as a requirement, Zac's):** the dev team never
  sits idle because one model is unavailable. Usage is recorded, each
  provider's state and remaining time is known, and work goes to whoever
  has time and does it well, with a reserve kept for Zac (6.4). The design
  goes with DEC-0076.
- **DEC-0077 (proposed; one choice):** the council chat. **Where it's kept:**
  (a) in the repo, `work/council.jsonl`, redacted, so every council member
  and cloud session shares it (recommended: it is the shared history), or
  (b) on this PC only (`data/dev/`), with task-linked messages copied into
  the history. A chat message never carries Zac's authority.
- **DEC-0078 (proposed):** the architecture map and growth branches, derived
  from the code and the history, in the dev window. This folds in T-0020's
  doc-vs-code marks and T-0023.

If approved, the order is section 8: steps 1, 3 and 4 first. They don't
depend on each other.
