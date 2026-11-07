# MIA's Curriculum

*DEC-0107, 2026-11-07. Code: `core/curriculum.py` (the tracks and objectives), `core/night_school.py` (one lesson a
night for it). Where she stands: `python -m tools.night_school curriculum`.*

> "I want her very well trained on how to do all things computer related, software engineering, design, apps, web
> pages, deploying, cyber security, pen testing, monitoring etc and creating documentation for use." (Zac,
> 2026-11-07)

This is the guide that goes with the curriculum: for each track, what doing it well looks like **here**, in her own
code. The objectives themselves live in `core/curriculum.py`, so the guide never drifts from what she's graded on.
Every lesson is practised on her own code and graded by a test that fails before and passes after.

## How she studies

- **One lesson a night** is for her curriculum, beside the night's focus. It's for the next objective in the track
  she's furthest behind in; on a tie, the track she's tried least, so the tracks take turns even while one is hard.
- **Mastered** means two lessons for that objective passed. A track's level (foundation, working, expert) is the
  highest whose objectives are all mastered.
- **Her teacher** (Claude Code, read-only) writes each exercise and its test, then writes the one lesson in what she
  did. The latest lessons for a skill are given to her the next time she works it.
- **Practice never merges** by itself: a real piece of work she passes waits in the lab for Zac.

## The tracks

### Software engineering
- Read before writing: what a function takes, returns, and does on empty, missing and wrong input.
- The smallest change that does the job; nothing around it changes. Match the code around it: its naming, its
  comment density, its idiom.
- Her architecture's rule: `core/` knows nothing of `gui/` or `modules/`; modules talk through the event bus;
  stores write through `atomic_write_text` (so undo works and the web knows to re-read). `docs/ARCHITECTURE.md`.
- Pure logic where it can be (no clock, no files, no network inside): it's the part that's easy to test.

### Testing and debugging
- A test fails for the right reason first. A test that already passes proves nothing (Night School throws such an
  exercise out).
- Fix the code, never the test, unless the test is what's wrong; never skip or disable one to get green.
- Read a traceback from the bottom: the line that raised, then the call that led there. Fix the cause.
- What's hard to test is made easy by passing it in: the date (`today=`), the folder (`tmp_path`), the other
  service (a stand-in). `tests/` has many examples.

### Documentation
- Every file opens with what it is, what it does and how; every class, function and method has a docstring
  (DEC-0104). A docstring is a claim about the code: check it against the code.
- A guide for people: steps in order, an example, what can go wrong, written for someone who wasn't there.
- A knowledge entry (DEC-0105, `work/knowledge/`): what was built, how, why that way, what went wrong, citing its
  commit, task or decision.
- Tools: `python -m tools.docs next` lists what's undocumented; `docs/ATLAS.md` is the map of every file.

### Design and user experience
- One look (DEC-0023, `docs/design/STARK_INTERFACE.md`): `web/tokens.css` is the theme; never a hard-coded colour.
- What matters first: the thing a person came for is at the top; detail can wait a tap.
- Accessible: every control has a label and a role, contrast is enough, everything works from the keyboard.
- Kind words: plain, short, never blaming the person (`docs/design/MIA_VOICE.md`).

### Web pages
- The web is all of her front end (DEC-0017): pages only talk to the engine through `web/mia.js`: `/api/state`
  to read, `/api/actions` to change things, `/api/live` to know when to re-read. Logic lives in core, never in
  `web/`.
- An endpoint validates what it's given, asks who's calling (`require_profile_id` in `server/app.py`), and is tested
  in-process with FastAPI's TestClient.
- Text from a person or a document goes into the page as text, never as HTML.

### Apps
- A desktop module follows `docs/MODULE_SPEC.md`: one `ModuleBase` subclass, a cheap `__init__`, the work in
  `on_load()` or `get_widget()`. A broken module is skipped, never crashes her.
- Logic that the web and the phone need belongs in core, not in a widget.
- The phone app (Kotlin, `android-phone/`) talks to the same server API; its contract is the server's.

### Deploying
- A deploy says what it needs: packages (`requirements.txt`), settings (`config/default_config.json` merged with
  the person's own), and how it starts (`main.py` is two lines; `core/application.py` owns the start-up).
- Every install step is safe to run twice, and undoable (`deploy/install_kiosk.sh` and `uninstall_kiosk.sh`).
- CI (`.github/workflows/`) runs what a contributor would: the tests, the Windows install, the phone build.
- `tools/pc_check.py` says what's left to set up on a PC.

### Cyber security (defence)
- She holds a household's private life. Each person's data is their own (`data/profiles/<id>/`); nothing is
  shared without a household's approval.
- The common weaknesses: input reaching a file path (traversal), a command, a query or a page (injection); a
  secret in code or a log (logs are redacted the Fix-It Log's way, `core/failure_log.redact`); an endpoint that
  doesn't check who's asking.
- She never sends an email herself (only a person pressing Send does) and never runs a change she proposed until
  it's approved (`core/actions.py`).
- Dependencies are audited weekly (`dev.vulnerable`, `phone.vulnerable` loops).

### Penetration testing (on herself only)
- **The rules** (`SECURITY_RULES` in `core/curriculum.py`, given to her teacher with every such lesson): she
  attacks only herself, her own code in the lab copy and her own server started in-process by the test. Never a
  network address, never anyone else's system, never a real password, token or person's data. No tool that
  attacks other systems is written.
- Map the surface first: every route in `server/app.py`, who may call it, what it takes.
- Then hostile input: too big, malformed, a path with `..`, a value meant to be code. Each must be refused
  cleanly.
- A weakness found becomes a test that proves it and a fix, through the lab like any change; Zac approves it.

### Monitoring
- She watches herself with improvement loops (`core/loops.py`, `docs/LOOPS.md`): each has a signal, a floor or a
  trend, and what it does when it slips.
- Every process has a loop or a reason it needs none (`core/loop_coverage.py`, DEC-0101).
- Tell a real problem from noise: a small number of readings can't (`min_n`); one reading against her usual isn't
  a trend (lessons K-0045 and K-0048 in the vault).
- Logs: `logs/mia.log`; never anything personal in them.

## Growing the curriculum

New objectives go in `core/curriculum.py` (a test checks every file an objective points at exists). Add one when a
track has no objective for something she'll need, or when her teacher's lessons keep pointing at the same gap.
