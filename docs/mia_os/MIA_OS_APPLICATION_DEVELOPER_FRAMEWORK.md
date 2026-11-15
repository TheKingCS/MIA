# MIA OS: building applications for MIA (Prompt 03 §12)

*Claude (Opus), 2026-11-15. Planning; nothing built. Part of [MIA_OS_APPLICATION_FRAMEWORK.md](MIA_OS_APPLICATION_FRAMEWORK.md).*

## 1. What a developer has today (exists)

| Need | Today |
|---|---|
| The contract | `docs/MODULE_SPEC.md` (checklist), `docs/ADDING_MODULES.md` (walkthrough), CLAUDE.md's rules |
| Validation | `core/module_validator.py` (folder, one ModuleBase, id format, instantiable) |
| Running one app alone | `python tests/run_module.py <id>` |
| Tests that keep the whole coherent | layering, documentation (`tests/test_documentation.py`), parity, loop coverage, at-rest, the Living System invariants |
| Generated maps | `docs/ATLAS.md`, `docs/PARITY.md`, `docs/LOOPS.md`, `docs/EVENTS.md`, `docs/MIA_MAP.md` |
| An isolated place to build | the development lab: a worktree with no real data (`core/dev_lab.py`) |
| Review | another model reviews (DEC-0174: Fable reviews Opus); Zac approves the merge |
| Knowledge for whoever comes next | `work/knowledge/` (DEC-0105), `for_task()` |
| MIA building for herself | Night School, capability gaps → lab tasks, "Build A Skill" (DEC-0167) |

## 2. What's missing

1. **A scaffold** (`tools/new_app.py`, proposed): asks for the id, name, area, tool domain and store, and writes the
   store with its epistemic contract, the action module, the tool module, the screen data, the page and its script,
   the tests, the registrations in the shared lists (app catalogue, personal data, actions, runtime, loop coverage),
   and a knowledge entry stub. Today each new app is written by copying the newest one (Smart Closet, World): about
   fifteen files touched, every one of which a test checks.
2. **The capability contract's fields** (MIA_OS_AI_APPLICATION_INTEGRATION.md §2) with a test.
3. **The manifest** and its test (MIA_OS_APPLICATION_MODEL.md §3).
4. **An extension SDK** (only once the extension host exists): a small client for the local API and the contract.

## 3. The standard lifecycle for a new app

Describe → (MIA drafts a plan from her own capabilities, DEC-0167) → scaffold → build in the lab → the suite passes →
review (Fable) → Zac approves the merge → it's in the next image → its loop watches it. AI-generated code meets the same
deterministic gates (validation, tests, documentation, review, approval); nothing skips them because a model wrote it.

## 4. No native app builder yet

A visual app builder isn't recommended now: MIA's apps are the person's records with screens and tools, and "Make
Something" (ACAF) already lets her make trackers and screens from her own parts. A builder would duplicate it.
