# Adaptive Creation & Automation Framework (ACAF): Review and Plan

*Claude, 2026-11-04, for Zac's review. It answers the ACAF handoff (filed as
`docs/HANDOFFS/H-0082_chatgpt-to-claude_acaf.md`). As the handoff asks, it's an
audit and plan before any major change: nothing here is built. Decisions are
DEC-0088 to DEC-0093, proposed (section 9).*

**Where the evidence comes from:** the repo at `e1fbc79`.

---

## 1. The headline

1. **The key choice: MIA creates *specifications*, not code.** A new screen,
   tracker, report or workflow is a document (JSON): which building blocks, in
   what layout, showing what data. Fixed, tested code inside MIA renders and
   runs it. This is what makes her creations safe enough to make freely:
   - a spec can't run anything;
   - it can't reach data it isn't allowed;
   - it can't break MIA's look;
   - it is checked by code in milliseconds and undone in one step.

   It still allows **new combinations of blocks**, for kinds of information
   nobody planned, which is the handoff's central requirement.
2. **Real code still goes through what exists.** A new tool, a parser for a
   device nobody planned, or a module is code. It goes through the lab, the
   council's reviews and Zac's approval (DEC-0058, DEC-0068 to DEC-0076). ACAF
   gives that path templates and scaffolds, and doesn't build a second one.
3. **Much of the foundation exists already:**
   - the design system (`web/tokens.css`, `web/components.css`, the shared
     frame `web/shell.js`);
   - screens whose data is assembled in core (DEC-0013, DEC-0017);
   - an approval contract with undo (`core/actions.py`: 219 action kinds;
     Propose → Approve → Execute → Record → Undo);
   - versioned writes (`core/undo_log.py`, `atomic_write_text`);
   - a module validator (`core/module_validator.py`);
   - the lab and the council for code;
   - inspection for diagnostics (`core/inspection.py`);
   - the communication gate for anything unprompted.
4. **One missing primitive is what makes "new information" possible.** Every
   store today is purpose-built: bills, flock, workouts. A new category of
   information has nowhere to live. ACAF's first piece is **record sets**: a
   generic, typed store a spec can define (fields, types, who it belongs to),
   changed through generic action kinds, so even new data gets approval and
   undo.
5. **Local-first works here.** MIA writes the spec with qwen2.5:14b, using
   Ollama's structured outputs: the model's reply must match the spec's JSON
   schema. Code checks everything else, so no cloud is needed to create a
   screen.

## 2. What exists, and how ACAF uses it (sections 13.1 to 13.4)

| ACAF part | What exists | Use |
|---|---|---|
| Design system | `web/tokens.css` (one cyan accent, graphite layers, DEC-0023), `web/components.css` (`.glass`, `.strip .cell`, `.sect`, `.stat`, `.empty`, chips), `web/shell.js` (`MIAShell.start`, `el`, `act`, `form`, `confirm`), `web/icons.js` | **The source of truth.** Blocks are built from these, never new styling |
| Screens | One hand-written page per app (`web/*.html` + `.js`) over data assembled in core (`core/web_surfaces.py`); the sidebar from `APPS` and `/api/shell` | **One generic page**, `web/made.html`, renders any spec. Published creations join the sidebar |
| Changing data | `core/actions.py`: propose, approve, execute, record, undo; `GLASSES_KINDS`; `child_ok` | **Reuse**: record sets get generic kinds; publishing a creation is an action |
| History and rollback | `core/undo_log.py`, `atomic_write_text`, `core/live.py` | **Reuse**: every creation version is a write; rollback is undo or an earlier version |
| Reads | Life State (`core/context_assembler.py`, `docs/schema/life_state.schema.json`), the stores, the Assistant's read tools | **A catalogue of read sources** (section 3.3), each listed with its privacy |
| Validation | `core/module_validator.py`; the test suite; schema tests | **Reuse the pattern**: a spec validator plus a headless render check |
| Isolated code | `core/dev_lab.py`, the council, review, the runner (T-0026) | **The only path for code** (section 6) |
| Diagnostics | `core/inspection.py` METHODS with permission levels | Diagnostic procedures are workflows over PASSIVE methods |
| Unprompted messages | `core/communication_gate.py` | **Every workflow notification goes through it** |
| Starters | `core/starter_templates.py` (chores for a kind of life) | Later expressed as templates; kept as is now |
| Usage | `core/usage_tracker.py`, `core/answer_ratings.py`, the Fix-It Log | Evaluation (section 5) |

**Name clashes to avoid** (don't rename working code to match the handoff's
words):

| Word | Already means | ACAF uses instead |
|---|---|---|
| "skills" | the RPG skill tree (`core/skill_manager.py`) | **abilities** |
| "components" | the workshop's electronics parts (`core/component_manager.py`) | **blocks** |
| "templates" | starter sets (`core/starter_templates.py`) | **blueprints** |

## 3. The architecture (sections 2 and 3)

### 3.1 The parts, mapped

| Handoff component | Built as | Where |
|---|---|---|
| Template Registry | **Blueprints**: versioned JSON in the repo, each with purpose, inputs, blocks, layout, data needs, dependencies, validation, version; composable (a blueprint can include others) | `blueprints/` (repo), `core/blueprints.py` |
| Creation Engine | **Makers**, one per kind: screen, record set, report, workflow. A new maker is one file registered by kind | `core/makers/` |
| Validation Engine | **The checker**: schema, bindings, permissions, privacy, child safety, size, accessibility, a headless render | `core/creation_check.py` |
| Deployment Manager | **Creations**: draft → checked → published (an approval) → versions → rollback, each with id, source blueprint, dependencies, permissions, results and history | `core/creations.py` |
| Process Orchestrator | **The workflow runner**, phase 4: steps are read sources, action kinds and reports | `core/workflow_runner.py` |
| Learning & Optimization | **Evaluation**, phase 6: use, ratings, fixes; proposed blueprint improvements go through the lab | `core/creation_review.py` |

### 3.2 A screen spec

```json
{
  "kind": "screen", "id": "C-0007", "version": 3, "blueprint": "tracker@2",
  "title": "Seed Bank", "icon": "leaf", "owner": "household",
  "sources": {"seeds": {"record_set": "R-0003"}},
  "blocks": [
    {"block": "stats", "items": [
      {"label": "Varieties", "value": {"count": "seeds"}},
      {"label": "Oldest saved", "value": {"min": "seeds.saved_on"}}]},
    {"block": "chart", "type": "bar", "x": "seeds.variety", "y": {"avg": "seeds.germination"}},
    {"block": "table", "source": "seeds", "columns": ["variety", "from", "saved_on", "count"], "sort": "-saved_on"},
    {"block": "form", "adds_to": "seeds"}
  ]
}
```

There's no HTML, no script and no free formula. Values are a small fixed
vocabulary:
- `count`, `sum`, `avg`, `min`, `max`;
- `latest`, `group by`, `within days`.

The vocabulary is computed **in core**, which assembles the screen's data from
the spec (DEC-0013: no logic in `web/`). `web/made.js` only draws blocks.

### 3.3 Blocks and sources

- **Blocks**, first set: `header`, `stats` (the status strip), `list`,
  `table`, `cards`, `chart` (bar, line, sparkline: one small SVG chart on the
  tokens, the one new piece of drawing), `meter`, `timeline`, `form` (adds or
  edits through an action), `empty`, `note`. Each is one function in
  `web/made.js`, styled only by existing classes and tokens.
- **Sources** are a catalogue, not free queries:
  - the person's or household's record sets;
  - named read sources over existing stores (`life_state.money`,
    `flock.eggs_by_day`, `maintenance.due`...), each declaring whose data it
    is, whether a child may see it, and whether it holds money.

  A spec can only name sources from the catalogue the person viewing could
  already see.

### 3.4 Record sets (DEC-0089)

- A record set is a typed list: fields with types (text, number, money, date,
  choice, yes/no, link to another record, photo ref) and an owner (the person
  or the household).
- It's stored like every other store: personal or household folder (the
  DEC-0001 lists), `atomic_write_text`, undoable.
- It's changed through generic action kinds (`records.add`, `records.edit`,
  `records.remove`), so the screens, the phone, the glasses and "undo that"
  all work on it.
- It's recorded in life events, so it joins the history.
- Money fields format through `core.region.money()`.

### 3.5 How MIA makes one (the UI pipeline)

1. **Need.** Someone asks ("I want to keep track of the seeds I save"), or MIA
   notices something with no home: a repeated note, an import with no store,
   an inspection finding.
2. **Understand.** She lists the fields and their types from what was said or
   seen. If the data already has a store, she uses its source instead of
   making a record set.
3. **Choose.** Code picks the blueprints that fit the data's shape (a list of
   things over time → tracker; one number over time → meter and line). The
   local model picks among them and fills the spec, with its output held to
   the spec schema.
4. **Check** (section 4). A spec that fails is sent back to the model once,
   with the reason, then shown to the person as "couldn't make it".
5. **Preview.** The draft is private and works on real data, read-only, in
   `web/made.html?draft=…`.
6. **Publish.** On the person's approval, it joins their sidebar (and the
   glasses' cards, if they pin it).
7. **Watch.** How often it's opened, what's added, 👍/👎, the Fix-It Log.
   That feeds section 5.

## 4. Validation (section 2D)

Code checks every spec before it can be previewed:

- **Structure:** it matches the schema; blocks and fields exist; within size
  limits.
- **Data:** every source is in the catalogue and visible to its owner; fields
  exist with the right types; aggregations fit the types (no `sum` of text).
- **Permissions and privacy:**
  - personal sources only on a personal creation;
  - a household creation never shows anyone's personal store;
  - money never on a child's screen;
  - a child's creations draw only on `CHILD_APPS` sources.
- **Consistency:** blocks only, and styling only from tokens, so it can't look
  foreign by construction.
- **Accessibility:** every block has a label; charts carry a text equivalent;
  forms label every field.
- **Render:** headless (Qt WebEngine on the PC, as used for screenshots
  today): no errors, no horizontal scroll at 390 px.
- **Regression:** a published creation is re-checked whenever its blueprint or
  a source changes; one that no longer passes is held, and says why.

Generated **code** is checked the lab's way: tests first, the full suite, two
reviews, and Zac.

## 5. Deployment, history and learning (sections 2E, 2F, 10)

- **Every creation has:**
  - an id and a version;
  - its source blueprint and version;
  - its sources;
  - the permissions it needs;
  - its check results;
  - its status (draft, published, held, retired);
  - its history.

  "What is this and why did you make it?" is answered from that record
  (`@mia` and the Assistant).
- **Publishing is an action** (`creation.publish`), so it's approved, recorded
  and undoable. A new version publishes beside the old one; rollback is one
  step.
- **Nothing is overwritten silently.** A creation changes only through its own
  new version, and never touches a hand-built screen or a store it didn't
  create.
- **Learning.** For each creation: whether it's opened, whether it's used
  (records added), whether it's rated, whether it's fixed. A pattern across
  creations from one blueprint (people always add the same block, always hide
  one) becomes a proposed blueprint change, marked by evidence:
  - **observed:** counts;
  - **inferred:** the proposal;
  - **verified:** a test and a trial that show it's better.

  Blueprints are repo files, so a change to one goes through the lab and the
  council's review like code. Old versions stay, and creations keep the
  version they were made with until re-checked.

## 6. The other creation kinds (sections 4 to 8)

| Kind | As a spec (safe, fast) | Needs code (the lab) |
|---|---|---|
| **Workflows** (phase 4) | Trigger (a schedule; a life-event type; a bus event); steps from read sources, action kinds, reports and the gate. **Approving one is a standing approval for exactly its listed action kinds, within limits** ("add expenses under $50 to Seed Bank"). Runs are logged, a failed step retries once, and a dry run shows what it would do (the actions' own `describe`, without approving) | A step that needs a tool MIA doesn't have |
| **Reports** | A spec of blocks into a document (the Business Report's path, `core/business_report.py`) | — |
| **Abilities** ("skills") | A composite of existing tools and actions is a workflow, with no code | A new tool: the lab, with the Assistant registry's own rules |
| **Data pipelines** | Mapping a known format (CSV, JSON) into a record set: a spec | A parser for a new device or format: the lab |
| **Diagnostics** | Procedures over inspection's PASSIVE methods, with results as a report | ACTIVE methods stay asked-first (DEC-0056) |
| **Software** | Module blueprints (`docs/MODULE_SPEC.md`) as scaffolds for the lab's coder | Everything: lab, reviews, Zac (DEC-0058) |

The handoff's homestead-business example is a mix:
- record sets for purchases, revenue and inventory, if the existing budget
  and business stores don't fit;
- screens over them;
- a workflow that files and categorizes.

The tax preparation is a report over records MIA already has. Most of it is
specs. A new bank format would be the only code.

## 7. Autonomy and safety (section 9), mapped to what exists

| Tier | ACAF | Through |
|---|---|---|
| **Automatic** | Private drafts, previews, reports, dry runs, proposed blueprint changes | The person's own draft space; no sidebar change |
| **Automatic, versioned** | Refreshing a published creation's data; running an approved workflow within its listed kinds; editing the person's own records (which still goes through actions) | Versions, undo log, run log |
| **Approval** | Publishing or changing a creation; a workflow's first approval or any new kind in it; a new record set shared with the household; a blueprint change; anything unprompted (the gate's rules and 5-a-day limit) | `core/actions.py`; the communication gate |
| **Zac only** | Code, new integrations, permissions, security, core architecture | The lab, review, the keyboard (DEC-0058, DEC-0069) |

The ACAF code itself goes on the lab's protected list: the checker, the
catalogue of sources, the creation and workflow runners. MIA can't loosen the
rules her creations are checked by.

## 8. Roadmap (section 11), with a working demonstration first

| Step | Builds | Accept when |
|---|---|---|
| **1. Foundation and the flagship** | Record sets with their action kinds; blueprints (tracker, overview, log); the spec schema; the blocks in `web/made.js`, with the chart; the screen assembler in core; the checker; drafts, publish, versions, rollback; the source catalogue's first entries; the local model making specs | **The demonstration:** from one sentence about information MIA has no screen for, she makes a record set and a screen. It passes the checker, previews on real data, is published on approval, appears in the sidebar on the PC and the phone, takes a new record from its form ("undo that" removes it), and rolls back to its earlier version. A spec with a bad source, a money block on a child's screen, or a personal store on a household screen is refused, naming why |
| 2. More blueprints and blocks | Dashboards over existing sources, reports, the glasses' card view of a creation | A creation over an existing store (eggs by hen) needs no record set |
| 3. Workflows | The runner, triggers, standing approval by kind, dry run, run log, retry, the gate | The homestead example's filing step runs on a schedule, within its kinds, and stops at an unapproved one |
| 4. Data mappings and diagnostics | CSV and JSON into record sets; diagnostic procedures over PASSIVE methods | An import with no store becomes a record set and a screen |
| 5. Evaluation and blueprint evolution | Use and ratings per creation; proposals marked observed, inferred or verified; blueprint changes through the lab | A blueprint change is tested against the creations made from the old version |
| 6. Code creations | Module and tool blueprints as scaffolds for the lab's coder and MIA's own coder (DEC-0074) | A proposed tool goes lab → reviews → Zac like any other change |

Step 1 is one task of a day or two of work. It doesn't wait for anything else,
and it doesn't touch the hand-built screens.

## 9. Decisions

- **DEC-0088 (proposed):** ACAF creations are specifications, not code.
  Screens, record sets, reports and workflows are JSON documents built from a
  fixed catalogue of blocks and sources, assembled in core and drawn by one
  generic page in MIA's design system. Anything needing new code goes through
  the lab, the council and Zac.
- **DEC-0089 (proposed):** record sets, a generic typed store for kinds of
  information MIA has no store for. Personal or household, changed through
  generic action kinds (approval, undo, history), money through `region.money`.
- **DEC-0090 (proposed):** blueprints. Versioned JSON in the repo
  (`blueprints/`), composable. Changes go through the lab and review, and
  creations keep the version they were made with.
- **DEC-0091 (proposed):** the creation lifecycle and its tiers (section 7).
  Private drafts are automatic; publishing and changes are approved actions,
  versioned, with one-step rollback. Every creation explains its blueprint,
  sources and permissions. The checker, the source catalogue and the runners
  are protected from the lab.
- **DEC-0092 (proposed):** workflows (step 3). Triggers and steps from the
  catalogue; approving one is a standing approval for exactly its listed
  action kinds within limits; unprompted messages go through the
  communication gate; runs are logged; a dry run comes first.
- **DEC-0093 (proposed):** evaluation. Creations are judged by use, ratings
  and fixes. Improvements are marked observed, inferred or verified, and a
  blueprint changes only when verified, through the lab.

If approved, step 1 is next: the flagship demonstration.
