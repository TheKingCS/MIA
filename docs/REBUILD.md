# Rebuilding MIA from nothing

*Claude, 2026-11-06, for DEC-0104 (Zac: "so that if MIA ever needed to redo this entire process herself, she
could"). The order to build MIA in, what each stage is for, how to know it works, and where the detail lives.
The file-by-file map is `docs/ATLAS.md` (generated from the code); every file, class and function says what it
does and how in its own docstring or header comment. Keep this page in step when a stage changes.*

## 0. What MIA is, and the rules that shape everything

- **What:** an offline-first personal assistant for a person and their household, on their own computer first,
  then their phone, then glasses, later small devices (`docs/VISION.md`, `docs/ROADMAP.md`, DEC-0015).
- **The rules, before any code** (`CLAUDE.md`, `docs/ARCHITECTURE.md`):
  1. Layers point one way: `core/` knows nothing else; `modules/` and `gui/` know `core/`; the web knows the
     engine only through its API. Modules never import each other; they talk through the event bus.
  2. One shared object, `AppContext`, passed everywhere; no globals.
  3. Facts and arithmetic live in code; the language model only chooses and phrases (DEC-0052). A number she
     didn't look up is never said.
  4. Every change the Assistant makes is proposed, approved, executed, recorded and undoable (`core/actions.py`).
  5. Each person's data is their own (`core/personal_data.py`); nothing personal in the code or the repo.
  6. Anything said unprompted goes through one gate (`core/communication_gate.py`).
  7. Every process has a loop or a reason (DEC-0094, DEC-0101); every file and function is documented (DEC-0104).
- **Decisions** are the history of why: `docs/DECISIONS.md`, DEC-0001 onwards. Read them before changing a rule.

## 1. The kernel (core/, no screens)

Build in this order; each stage's tests (named in parentheses) prove it before the next.

1. **Writing safely and undoing:** `atomic_write.py` (a file is never half-written), `undo_log.py` (every change
   restorable), `logger.py`. (`test_atomic_write*`, `test_your_data_and_undo.py`)
2. **Config and context:** `config_manager.py` (defaults in `config/default_config.json`, the person's overrides
   merged on load), `app_context.py`, `event_bus.py` (synchronous publish/subscribe).
3. **People and households:** `profile_manager.py` (accounts by email), `household_manager.py`,
   `personal_data.py` (which store is a person's and which a household's; a person's view of the context),
   `person_settings.py`, `child_accounts.py`.
4. **Stores:** one manager per kind of thing (`budget_manager.py`, `kitchen_manager.py`, `maintenance_manager.py`,
   `mission_manager.py`, ...). Each loads its JSON, writes through `atomic_write_text`, and records meaningful
   changes in the history (`life_events.py`). `docs/ATLAS.md` lists every store under core/.
5. **The engine's read model:** `links.py` (how things relate), `context_assembler.py`
   (`assemble_life_state_v2()`, shaped by `docs/schema/life_state.schema.json`), `findings.py` (what two apps
   together show).
6. **The action contract:** `actions.py` and the `*_actions.py` files that register each kind (propose →
   approve → execute → record → undo), `corrections.py` (her changes the person fixed).
7. **The Assistant:** `assistant_actions.py` (the tool registry), `assistant_turn.py` (one turn: safety floor,
   quick commands, question plans, the model with tools), `question_plans.py` (detailed questions answered from
   a fact sheet built in code), `llm_manager.py` (the local model through Ollama), `safety_floor.py` (crisis
   handling that never waits on the model), `talk_it_out.py` (personal modes, the private journal).
8. **Speaking unprompted:** `communication_gate.py`, `message_reasons.py`, and the daily checks in
   `application.py` (`_check_*`).
9. **Learning about herself:** `failure_log.py` (the Fix-It Log), `turn_trace.py`, `answer_ratings.py`,
   `calibration.py`, `loops.py` (every improvement loop; `docs/LOOPS.md`), `loop_coverage.py`, `night_school.py`
   (`docs/NIGHT_SCHOOL.md`), `dev_lab.py` and `mia_coder.py` (changing her own code in a lab, tested, approved by
   the owner), `code_atlas.py` (this documentation, measured).

## 2. The faces

1. **The desktop (Qt):** `core/application.py` owns the boot order (splash, services, module discovery, first
   run or sign-in, the main window); `gui/` is the shell; `modules/<app>/module.py` is one app each, found
   automatically (`core/module_manager.py`, `docs/MODULE_SPEC.md`, `docs/ADDING_MODULES.md`).
2. **The web (phone, glasses, desktop web view):** `server/app.py` serves the API and `web/`; every page talks
   only through `web/mia.js`, builds on `web/shell.js`, and reads data assembled in core (DEC-0017;
   `docs/WEB_PARITY.md` tracks each screen). The look is the design team's (`web/tokens.css`, DEC-0023).
3. **The phone app:** `android-phone/` carries the same Python engine (Chaquopy) and the glasses' link
   (`docs/PHONE_FIRST_PLAN.md`, `docs/GLASSES_RELAY_PLAN.md`).

## 3. What runs around her

- **Daily:** the checks in `application.py`; loops (`loops.run`); the communication gate's limit.
- **Nightly:** Night School (lessons graded by tests, a shadow attempt, loop drafts, the weekly benchmarks), photo
  captions (`vault_captions.py`), the Chronicle's issue on Sundays.
- **The development platform:** tasks as files (`work/tasks/`), the activity log, the council of AI reviewers
  (`core/council.py`), the lab, the knowledge vault (`work/knowledge/`) (`docs/COLLABORATION.md`).

## 4. How to know a rebuild is right

1. `pytest`: the whole suite (every part's own tests say what it must do).
2. `python -m tools.weekly_bench`: the 112-question benchmark, the conversation corpus, the routing audit.
3. `python -m tools.work loops --run`: every loop, including the suite on the committed code and the dependency
   audit.
4. `python -m core.code_atlas`: the atlas regenerated; `tests/test_documentation.py` passes.

## 5. Keeping this true

Every change: its files keep their descriptions current; new classes and functions arrive documented (the ratchet
in `work/doc_baseline.json` refuses anything else); `docs/ATLAS.md` and `docs/LOOPS.md` are regenerated; this page
changes when a stage does. The backlog of older undocumented functions is watched by `dev.docs` and worked down
file by file.
