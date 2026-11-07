"""
core.night_school
===================

Night School (DEC-0100; Zac, 2026-11-06: "MIAs night school module where she
spends time every night with Claude learning how to build herself into the
best version of herself, doing tests, building her skills and proving her
capabilities. I want that happening asap."). The full design is
`docs/NIGHT_SCHOOL.md`.

**A night** (`night()`), started by MIA's daily check inside its window
(`work/night_school.json`, 01:30 for four hours by default) in a process of
its own (`tools/night_school.py`), and stopped by `work/STOP`, by the end
of the window, or when her teacher is resting at a usage limit:

1. **She looks at her own progress**: her loops (core/loops.py), her row in
   the ledger (core/dev_ledger.py), her Night School report card.
2. **She chooses what to study** (`self_assessment()`), with her reasons:
   the loops below their floor, her weakest skills, the lessons she failed.
3. **The focus**: in `plan` mode, the next step of `docs/BUILD_PLAN.md`; in
   `self` mode, her own pick. She's trained in both: every night her
   teacher says whether her pick was the right one, and `choosing()` keeps
   score. Zac moves her to `self` mode when that score supports it.
4. **Her teacher** (Claude Code, read-only: it reads her code and never
   changes it; Codex if Claude is resting) sets the night's exercises for
   that focus: each one small, for files she may change, **with a test that
   fails now and passes when it's done**. One of them is always for her
   **curriculum** (core/curriculum.py, DEC-0107): the next objective in the
   area of computing she's furthest behind in (engineering, testing,
   documentation, design, web, apps, deploying, security, pen testing on
   herself only, monitoring), practised on her own code.
5. **She does them** (core/mia_coder.py, her local model, in the lab). Code
   grades her, not the teacher: the exercise's test first fails, then
   passes, and the full suite has nothing new failing. Her teacher reads
   what she did and writes the one lesson in it, which she's given the next
   time she works that skill.
5a. **Study hall** (core/specialists.py, DEC-0109): one of her specialists
   (construction, homesteading, radio, strategy, making, outdoors,
   research, testing, engineering), the one that studied longest ago,
   gets new sourced notes from her teacher for its open questions.
6. **She audits herself, weekly** (core/self_audit.py, DEC-0108): her
   code for what could be clearer or leaner, her parts for where they
   could connect better, and her best-practices series is rewritten
   from what the team has learned. The top finding of each opens a task.
6a. **She proves herself on real work**: one shadow attempt at a ready task
   (core/mia_coder.shadow), which is what the ledger counts.
7. **She spreads her loops** (core/loop_coverage.py): her teacher drafts a
   loop for the next family of processes no loop watches yet, and it
   becomes a task for the usual paths.
8. **The report**: the night is kept (`data/dev/night_school`), shown in
   the dev window's Night School panel and by `python -m tools.night_school`.

Practice never merges. An exercise her teacher marks as real progress on the
plan, which she passes, stays in the lab as a proposal for Zac
(`python -m tools.lab approve <id>`); every other attempt is rejected once
graded. This file is on the lab's protected list: she can't grade herself.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Optional

from core.atomic_write import atomic_write_text
from core.dev_store import DEV_DATA, DevStore

ROOT = Path(__file__).resolve().parent.parent
SETTINGS = ROOT / "work" / "night_school.json"
STOP_FILE = ROOT / "work" / "STOP"
PLAN = ROOT / "docs" / "BUILD_PLAN.md"
WHO = "MIA (night school)"
DEFAULTS = {"enabled": True, "start": "01:30", "hours": 4.0, "mode": "plan", "lessons": 3, "shadow": 1,
            "loop_families": 1, "teachers": ["claude-code", "codex"], "teacher_calls": 8, "benchmarks": True,
            "curriculum": True, "audit": True, "specialists": True}
MODES = ("plan", "self")
LESSON_MINUTES = 45  # a lesson isn't started with less of the window left than this
TEST_NAME = re.compile(r"^tests/test_night_[a-z0-9_]{3,60}\.py$")
NOTES_PER_SKILL = 5
CHOOSE_AFTER = 10  # nights of evidence before her own picks are trusted
CHOOSE_BOUND = 0.6


# ------------------------------------------------------------------ settings and records

def settings(path: Path = SETTINGS) -> dict:
    try:
        found = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        found = {}
    out = {**DEFAULTS, **{k: v for k, v in found.items() if k in DEFAULTS}}
    if out["mode"] not in MODES:
        out["mode"] = "plan"
    return out


def _store() -> DevStore:
    return DevStore(DEV_DATA / "night_school")


def nights(days: Optional[int] = None, store: Optional[DevStore] = None) -> list[dict]:
    rows = (store or _store()).tail(400)
    if days is None:
        return rows
    since = (datetime.now() - timedelta(days=days)).isoformat()
    return [r for r in rows if r.get("at", "") >= since]


def report_card(store: Optional[DevStore] = None) -> dict:
    """skill -> {lessons, passed, rate, bound} over every night."""
    from core.dev_ledger import wilson

    out: dict[str, dict] = {}
    for n in nights(store=store):
        for lesson in n.get("lessons", []):
            if lesson.get("outcome") not in ("pass", "fail"):
                continue
            row = out.setdefault(lesson.get("skill") or "engine changes", {"lessons": 0, "passed": 0})
            row["lessons"] += 1
            row["passed"] += lesson["outcome"] == "pass"
    for row in out.values():
        row["rate"] = round(row["passed"] / row["lessons"], 2)
        row["bound"] = round(wilson(row["passed"], row["lessons"]), 2)
    return out


def notes_for(skill: str, store: Optional[DevStore] = None, limit: int = NOTES_PER_SKILL) -> list[str]:
    """Her teacher's latest lessons for a skill, newest first: what she's given before working it again."""
    found = [l["note"] for n in nights(store=store) for l in n.get("lessons", [])
             if l.get("skill") == skill and l.get("note")]
    return found[::-1][:limit]


def choosing(store: Optional[DevStore] = None) -> dict:
    """How often her own pick of what to study matched her teacher's, and whether that's enough to trust."""
    from core.dev_ledger import wilson

    judged = [n for n in nights(store=store) if isinstance(n.get("pick_agreed"), bool)][-30:]
    agreed = sum(1 for n in judged if n["pick_agreed"])
    bound = wilson(agreed, len(judged)) if judged else 0.0
    return {"nights": len(judged), "agreed": agreed, "rate": round(agreed / len(judged), 2) if judged else 0.0,
            "bound": round(bound, 2), "ready": len(judged) >= CHOOSE_AFTER and bound >= CHOOSE_BOUND}


# ------------------------------------------------------------------ what she chooses (pure)

def plan_step(text: Optional[str] = None) -> Optional[dict]:
    """The next unfinished step of the build plan: {number, title, text}. A step marked ⏸ is skipped: what's left
    of it waits on someone (Zac's Plaid work, his document), so there's nothing to study yet."""
    if text is None:
        try:
            text = PLAN.read_text(encoding="utf-8")
        except OSError:
            return None
    lines = text.splitlines()
    for i, line in enumerate(lines):
        m = re.match(r"^(\d+)\.\s+(⬜|🔨)\s+\*\*(.+?)\*\*", line)
        if m:
            body = [line]
            for more in lines[i + 1:]:
                if re.match(r"^(\d+\.\s|#)", more):
                    break
                body.append(more)
            return {"number": int(m.group(1)), "title": m.group(3).rstrip(":"), "text": "\n".join(body).strip()}
    return None


def self_assessment(progress: list[dict], ledger_row: dict, card: dict, todo_loops: int = 0) -> list[dict]:
    """Pure logic. What she'd study, ranked, each with her reason."""
    from core.model_forge import specialists_for

    out = []
    for loop in progress:
        if loop.get("state") in ("below", "slid"):
            kinds = specialists_for(loop["id"])  # DEC-0106: a model of her own could be the fix
            model = (f" (a model of her own could help: a {kinds[0].kind} that {kinds[0].does}"
                     + ("" if kinds[0].built else ", not built yet") + ")") if kinds else ""
            out.append({"area": f"loop {loop['id']}", "score": 3 if loop["state"] == "below" else 2,
                        "why": f"{loop['what']}: {loop.get('why') or loop.get('detail')}{model}"})
    for skill, row in (ledger_row or {}).items():
        if skill == "reviewing":
            continue
        if not row.get("attempts"):
            out.append({"area": f"skill {skill}", "score": 1, "why": f"she has never tried {skill} on real work"})
        elif (row.get("rate") or 0) < 0.6:
            out.append({"area": f"skill {skill}", "score": 2.5 - (row.get("rate") or 0),
                        "why": f"{row['passed']} of {row['attempts']} of her attempts at {skill} passed"})
    for skill, row in card.items():
        if row["lessons"] >= 2 and row["rate"] < 0.5:
            out.append({"area": f"skill {skill}", "score": 2.2,
                        "why": f"she passed {row['passed']} of {row['lessons']} Night School lessons in {skill}"})
    if todo_loops:
        out.append({"area": "loop coverage", "score": 0.5, "why": f"{todo_loops} processes have no loop yet"})
    best: dict[str, dict] = {}
    for a in out:
        if a["area"] not in best or a["score"] > best[a["area"]]["score"]:
            best[a["area"]] = a
    return sorted(best.values(), key=lambda a: -a["score"])


def _json_in(text: str) -> dict:
    """The JSON object in a teacher's reply (it may wrap it in words or a fence)."""
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("no JSON in the reply")
    found = json.loads(text[start:end + 1])
    if not isinstance(found, dict):
        raise ValueError("the reply's JSON isn't an object")
    return found


def _paths(files) -> list[str]:
    out = []
    for f in files or []:
        f = str(f).replace("\\", "/")
        out.append(f[2:] if f.startswith("./") else f)
    return out


def valid_exercise(ex: dict, root: Path = ROOT) -> str:
    """Pure-ish. Why an exercise can't be done ("" when it can)."""
    from core.dev_lab import touches_protected
    from core.mia_coder import MAX_FILE, MAX_FILES

    files = _paths(ex.get("files"))
    if not str(ex.get("title", "")).strip() or not str(ex.get("task", "")).strip():
        return "it has no title or task"
    if not files or len(files) > MAX_FILES:
        return f"it needs 1 to {MAX_FILES} files"
    if touches_protected(files):
        return "it touches files she may never change: " + ", ".join(touches_protected(files))
    for f in files:
        path = (root / f).resolve()
        if root.resolve() not in path.parents:
            return f"{f} is outside MIA"
        if path.exists() and len(path.read_text(encoding="utf-8", errors="replace")) > MAX_FILE:
            return f"{f} is too long for her model"
    if not TEST_NAME.match(str(ex.get("test_name", ""))):
        return "its test isn't named tests/test_night_<name>.py"
    if (root / ex["test_name"]).exists():
        return "its test would replace one that's there"
    if "def test_" not in str(ex.get("test_code", "")):
        return "it has no test"
    return ""


# ------------------------------------------------------------------ the teacher

SYLLABUS_PROMPT = """You are MIA's teacher at Night School. MIA is a personal assistant (this repository; read CLAUDE.md
and anything you need). Tonight she studies, and you set her exercises. You only read; you never change a file.

Her coder is a local model (qwen3-coder:30b) with no tools: she's given a task and the full text of up to 4 files,
and replies with exact find-and-replace edits. She can't run anything, read other files or make new ones beyond the
files listed (a listed file that doesn't exist yet starts empty). Each file must be under 40,000 characters. She
may never change these: {protected}.

Tonight's focus: {focus}

What she chose to study, with her reasons:
{assessment}

Her report card so far: {card}
Her teacher's recent lessons for her: {notes}

Reply with only a JSON object:
{{"pick_agrees": true or false (was her own first choice the right thing to study tonight?),
  "better_pick": "if not, what she should have chosen, in a few words",
  "why": "one or two sentences",
  "exercises": [up to {count} of {{
     "title": "short", "skill": one of {skills},
     "files": ["the files she may change"],
     "task": "what to do, written for her: precise, small, one sitting",
     "test_name": "tests/test_night_<short_name>.py",
     "test_code": "a complete pytest file that FAILS on the code as it is now and PASSES once the task is done",
     "real": true if this is real progress on the focus that's worth keeping, false if it's practice,
     "objective": "the curriculum objective's id, on the curriculum exercise only"}}]}}

Make each exercise teach something the focus needs. Start where she is: if she's failing, smaller."""

GRADE_PROMPT = """You are MIA's teacher at Night School. She just did this exercise. Code already graded it: {outcome}
({check}). Below are the exercise and her change. Reply with only a JSON object: {{"note": "the one lesson she
should carry into the next time she works on {skill}: specific, two sentences at most"}}.

Exercise: {title}
{task}

What she said: {said}

Her change:
{diff}"""

LOOPS_PROMPT = """You are MIA's teacher. MIA keeps improvement loops (core/loops.py, docs/IMPROVEMENT_LOOPS.md): each
measures a number in code from what she already records, compares it with a floor and its own trend, and opens a
task when it's below. These processes have no loop yet:
{processes}

Read the code that runs them. Reply with only a JSON object:
{{"loops": [{{"id": "area.name", "covers": ["the process ids it watches"], "what": "what it counts",
   "measure": "exactly how, in code, from which records (name the file and function)",
   "better": "lower" or "higher", "floor": a number or null, "scope": "person" or "device"}}],
  "none": [{{"id": "a process id", "why": "why it needs no loop"}}]}}
One loop can cover several processes. Only propose what can be measured from records MIA already keeps; say what's
missing otherwise."""


def _teacher(order: list[str], used: int, budget: int) -> Optional[str]:
    """The first teacher who's installed and not resting at a usage limit, while the night's calls last."""
    import shutil

    from core import dev_usage
    from core.work_agents import load as load_agents

    if used >= budget:
        return None
    providers = load_agents().providers
    for name in order:
        spec = providers.get(name)
        if spec is None or (spec.command and not shutil.which(spec.command)):
            continue
        try:
            if dev_usage.state(name).get("state") == "cooling":
                continue  # resting at a usage limit
        except OSError:
            pass
        return name
    return None


def _default_ask(provider: str, prompt: str) -> str:
    from core.work_review import ask_provider

    return ask_provider(provider, prompt, purpose="night school")


# ------------------------------------------------------------------ a lesson

def _test_run(lab_folder: Path, test_name: str) -> tuple[bool, str]:
    """Whether the test file passes in that folder, and what pytest said."""
    from core.dev_lab import _python

    out = subprocess.run([_python(), "-m", "pytest", "-q", "-p", "no:cacheprovider", test_name], cwd=str(lab_folder),
                         capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    return out.returncode == 0, (out.stdout or "") + (out.stderr or "")


def _one_test(lab_folder: Path, test_name: str) -> bool:
    """True when the test file passes in that folder."""
    return _test_run(lab_folder, test_name)[0]


def lesson(ex: dict, *, lab=None, coder_ask=None, suite=None, one_test=_one_test, notes: list[str] = (),
           diff: Optional[Callable[[str], str]] = None,
           test_run: Optional[Callable[[Path, str], tuple[bool, str]]] = None) -> dict:
    """One exercise: the test is shown failing, she works it, code grades it. Returns the lesson's record
    (with her change under "_diff", for her teacher, read before the lab throws practice away). When her first
    try doesn't pass its own test, she gets one more with what pytest said (as anyone would read the error and
    fix it); the lab's full suite grades whatever she ends with."""
    if test_run is None and one_test is _one_test:
        test_run = _test_run
    if lab is None:
        from core import dev_lab as lab
    if diff is None:
        from core.work_review import lab_diff as diff
    from core.mia_coder import coder

    files = _paths(ex["files"])
    out = {"title": ex["title"][:120], "skill": ex.get("skill") or "engine changes", "files": files,
           "test": ex["test_name"], "real": bool(ex.get("real")), "outcome": "fail", "summary": ""}
    plan = f"Files: {', '.join(files)}"
    if notes:
        plan += "\n\nWhat your teacher taught you last time:\n" + "\n".join(f"- {n}" for n in notes)
    p = lab.create(f"Night School: {ex['title'][:80]}", ex["task"], evidence="Night School exercise", plan=plan)
    out["proposal"] = p.proposal_id
    where = Path(lab.folder(p))
    test = where / ex["test_name"]
    test.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(test, str(ex["test_code"]))
    try:
        if one_test(where, ex["test_name"]):
            out.update(outcome="invalid", summary="its test already passed before she began")
            lab.reject(p.proposal_id, "night school: the exercise's test already passed")
            return out
        p = lab.write(p.proposal_id, coder=coder(coder_ask))
    except Exception as problem:
        lab.reject(p.proposal_id, f"night school: {problem}"[:300])
        out["summary"] = f"couldn't write: {str(problem)[:200]}"
        return out
    out["said"] = (p.coder_said or "")[:600]
    if p.status != lab.WRITTEN or "(changed nothing)" in (p.coder_said or ""):  # the test alone isn't her work
        lab.reject(p.proposal_id, "night school: nothing changed")
        out["summary"] = p.note or "she changed nothing"
        return out
    if test_run is not None:
        ok, said = test_run(where, ex["test_name"])
        if not ok:
            out["retried"] = True
            try:
                p = lab.write(p.proposal_id, coder=coder(coder_ask),
                              again="It didn't pass its test yet. What pytest said:\n" + said[-1500:] + "\nFix it.")
                out["said"] = (p.coder_said or "")[:600]
            except Exception as problem:  # the first try stands
                out["retry_error"] = str(problem)[:200]
    p = lab.check(p.proposal_id, suite=suite)
    try:
        out["_diff"] = diff(p.proposal_id)[:20_000]
    except Exception:
        out["_diff"] = ""
    tests = getattr(p, "tests", {}) or {}
    passed = p.status == lab.READY
    out["outcome"] = "pass" if passed else "fail"
    out["summary"] = tests.get("summary", "") + ("" if passed else f" ({p.note})"[:300])
    if passed and out["real"]:
        out["kept"] = True  # real progress: waits in the lab for Zac
    else:
        lab.reject(p.proposal_id, "night school: graded, practice never merges")
    return out


def _cached_suite():
    """The lab's suite, with the starting point's result kept for the night (it doesn't change)."""
    from core.dev_lab import run_suite

    kept: dict[str, dict] = {}

    def run(cwd):
        name = Path(cwd).name
        if name.startswith("_base-"):
            if name not in kept:
                kept[name] = run_suite(cwd)
            return kept[name]
        return run_suite(cwd)
    return run


# ------------------------------------------------------------------ real work and loops

def _shadow_task(tasks: dict) -> Optional[object]:
    """A ready task she can attempt: unclaimed, up to 4 small files she may change. Loop and plan tasks first."""
    from core import work_tasks
    from core.dev_lab import touches_protected
    from core.mia_coder import MAX_FILE, MAX_FILES

    def fits(t) -> bool:
        if not t.files or len(t.files) > MAX_FILES or touches_protected(t.files):
            return False
        for f in t.files:
            path = ROOT / f
            if not path.exists() or path.is_dir() or len(path.read_text(encoding="utf-8", errors="replace")) > MAX_FILE:
                return False
        return True
    ready = [t for t in tasks.values() if work_tasks.ready(t, tasks) and fits(t)]  # open: nobody has claimed it
    ready.sort(key=lambda t: (not t.source.startswith(("loop:", "plan:")), t.id))
    return ready[0] if ready else None


def _loop_family(ask, teacher: str, family: list[dict], tasks_dir=None, log=None) -> dict:
    """The teacher drafts loops for a family of unwatched processes; a task carries them."""
    from core import loop_coverage, work_activity, work_tasks

    said = _json_in(ask(teacher, LOOPS_PROMPT.format(
        processes="\n".join(f"- {r['id']}: {r['what']}" for r in family))))
    ids = {r["id"] for r in family}
    drafted = [l for l in said.get("loops") or [] if isinstance(l, dict) and set(l.get("covers") or []) & ids]
    declined = [d for d in said.get("none") or [] if isinstance(d, dict) and d.get("id") in ids and d.get("why")]
    out = {"processes": sorted(ids), "drafted": len(drafted), "declined": len(declined), "task": ""}
    if drafted:
        tasks = work_tasks.load(tasks_dir) if tasks_dir else work_tasks.load()
        body = ("Drafted at Night School by MIA's teacher (core/loop_coverage.py, DEC-0101). Build each loop in "
                "core/loops.py with its `covers`; check each measure reads records MIA really keeps.\n\n" +
                "\n\n".join(f"- **{l.get('id')}** ({', '.join(l.get('covers') or [])}): {l.get('what')}. "
                            f"Measure: {l.get('measure')}. Better {l.get('better')}, floor {l.get('floor')}, "
                            f"scope {l.get('scope')}." for l in drafted))
        task = work_tasks.new(tasks, f"Loops for {', '.join(sorted(ids))[:90]}", role="Debugging Engineer",
                              source="night:loops", files=["core/loops.py"], body=body)
        work_tasks.save(task, tasks_dir) if tasks_dir else work_tasks.save(task)
        covered = sorted({c for l in drafted for c in l.get("covers") or []} & ids)
        loop_coverage.mark(covered, "proposed", task=task.id)
        out["task"] = task.id
        detail = f"drafted {len(drafted)} loop(s) for {', '.join(covered)}"
        work_activity.record(WHO, "night", task.id, detail, log) if log else work_activity.record(WHO, "night", task.id, detail)
    for d in declined:
        if not any(d["id"] in (l.get("covers") or []) for l in drafted):
            # only a proposal: "none" is decided by whoever reviews it, so it's kept as the teacher's reason
            loop_coverage.mark([d["id"]], "todo", why=f"teacher: {str(d['why'])[:200]}")
    return out


# ------------------------------------------------------------------ the night

def night(now: Optional[datetime] = None, *, ask: Optional[Callable[[str, str], str]] = None, coder_ask=None, lab=None,
          suite=None, one_test=_one_test, shadow=None, clock: Optional[Callable[[], datetime]] = None,
          config: Optional[dict] = None, store: Optional[DevStore] = None, tasks_dir=None, log=None) -> dict:
    """One night of school, as far as the window, the budget and her teacher allow. Returns the night's record."""
    from core import dev_ledger, loop_coverage, loops
    from core import work_tasks
    from core.dev_lab import PROTECTED

    cfg = config or settings()
    clock = clock or datetime.now
    start = now or clock()
    ends = start + timedelta(hours=float(cfg["hours"]))
    ask = ask or _default_ask
    store = store or _store()
    record: dict = {"at": start.isoformat(timespec="seconds"), "mode": cfg["mode"], "lessons": [], "notes": []}

    def left() -> float:
        return (ends - clock()).total_seconds() / 60

    def stopped() -> bool:
        return STOP_FILE.exists() or left() < LESSON_MINUTES

    # 1. Her progress
    try:
        loops.run(None, "device", now=start, tasks_dir=tasks_dir, log=log, heavy=True)  # the suite, the audit
    except Exception as problem:
        record["notes"].append(f"her loops couldn't run: {str(problem)[:120]}")
    progress = loops.summary(None, "device")
    ledger_row = dev_ledger.ledger().get("ollama-coder", {})
    card = report_card(store)
    coverage = loop_coverage.report()
    record["progress"] = {"loops_below": [l["id"] for l in progress if l["state"] in ("below", "slid")],
                          "coverage": coverage["share"], "card": card}

    # 2. What she'd study, 3. tonight's focus
    areas = self_assessment(progress, ledger_row, card, coverage["counts"].get("todo", 0))
    record["her_pick"] = areas[0] if areas else None
    step = plan_step()
    if cfg["mode"] == "self" and areas:
        record["focus"] = f"her own pick: {areas[0]['area']} ({areas[0]['why']})"
    elif step:
        record["focus"] = f"build plan step {step['number']}: {step['title']}"
        record["step"] = step["number"]
    else:
        record["focus"] = f"her own pick: {areas[0]['area']}" if areas else "general practice"

    # 3a. Her curriculum (core/curriculum.py): one lesson a night for her next objective
    objective = None
    if cfg.get("curriculum", True):
        from core import curriculum

        objective = curriculum.next_objective(curriculum.progress(
            l for n in nights(store=store) for l in n.get("lessons", [])))
        if objective is not None:
            record["objective"] = objective.id

    # 4. The teacher sets the night
    calls = 0
    teacher = _teacher(list(cfg["teachers"]), calls, int(cfg["teacher_calls"]))
    record["teacher"] = teacher or ""
    exercises = []
    if teacher and not STOP_FILE.exists():
        try:
            focus_text = record["focus"] + (f"\n\n{step['text']}" if step and cfg["mode"] == "plan" else "")
            if objective is not None:
                from core.curriculum import lesson_brief

                focus_text += (f"\n\nOne exercise tonight is for her curriculum instead of the focus; give it "
                               f"\"objective\": \"{objective.id}\". {lesson_brief(objective)}")
            said = _json_in(ask(teacher, SYLLABUS_PROMPT.format(
                protected=", ".join(PROTECTED), focus=focus_text,
                assessment="\n".join(f"{i + 1}. {a['area']}: {a['why']}" for i, a in enumerate(areas[:6])) or "(nothing yet)",
                card=json.dumps(card) if card else "no lessons yet",
                notes="; ".join(n for s in card for n in notes_for(s, store, 2)) or "none yet",
                count=int(cfg["lessons"]), skills=", ".join(s for s in dev_ledger.SKILLS if s != "reviewing"))))
            calls += 1
            if areas and isinstance(said.get("pick_agrees"), bool):
                record["pick_agreed"] = said["pick_agrees"]
                record["better_pick"] = str(said.get("better_pick") or "")[:200]
            record["teacher_why"] = str(said.get("why") or "")[:400]
            for ex in (said.get("exercises") or [])[:int(cfg["lessons"])]:
                problem = valid_exercise(ex) if isinstance(ex, dict) else "it isn't an exercise"
                if problem:
                    record["lessons"].append({"title": str((ex or {}).get("title", ""))[:120] if isinstance(ex, dict) else "",
                                              "outcome": "invalid", "summary": problem})
                else:
                    exercises.append(ex)
        except Exception as problem:
            calls += 1
            record["notes"].append(f"the teacher's syllabus didn't come through: {str(problem)[:160]}")
    elif not teacher:
        record["notes"].append("no teacher had time tonight: she practised on real work alone")

    # 5. Her lessons
    run_suite = suite or _cached_suite()
    for ex in exercises:
        if stopped():
            record["notes"].append("the night ended before every lesson")
            break
        done = lesson(ex, lab=lab, coder_ask=coder_ask, suite=run_suite, one_test=one_test,
                      notes=notes_for(ex.get("skill") or "engine changes", store))
        her_change = done.pop("_diff", "")
        if objective is not None and ex.get("objective") == objective.id:
            done["objective"] = objective.id  # what core/curriculum.progress() counts
        if done["outcome"] in ("pass", "fail") and done.get("proposal"):
            grader = _teacher(list(cfg["teachers"]), calls, int(cfg["teacher_calls"]))
            if grader:
                try:
                    graded = _json_in(ask(grader, GRADE_PROMPT.format(
                        outcome=done["outcome"], check=done["summary"][:300], skill=done["skill"], title=done["title"],
                        task=ex["task"][:3000], said=done.get("said", "")[:600], diff=her_change or "(no change)")))
                    done["note"] = str(graded.get("note") or "")[:400]
                except Exception as problem:
                    record["notes"].append(f"a lesson wasn't graded: {str(problem)[:120]}")
                calls += 1
        record["lessons"].append(done)

    # 6. Real work: a shadow attempt the ledger counts
    record["shadow"] = []
    for _ in range(int(cfg["shadow"])):
        if stopped():
            break
        task = _shadow_task(work_tasks.load(tasks_dir) if tasks_dir else work_tasks.load())
        if task is None:
            record["notes"].append("no ready task fits her yet for a shadow attempt")
            break
        try:
            if shadow is None:
                from core.mia_coder import shadow as shadow_fn
                result = shadow_fn(task.id, lab=lab, ask=coder_ask, suite=run_suite)
            else:
                result = shadow(task.id)
            record["shadow"].append({"task": task.id, "outcome": result.get("outcome"),
                                     "summary": str(result.get("summary", ""))[:200]})
        except Exception as problem:
            record["shadow"].append({"task": task.id, "outcome": "error", "summary": str(problem)[:200]})
        break

    # 7. Spreading her loops
    record["loops"] = []
    for _ in range(int(cfg["loop_families"])):
        family = loop_coverage.next_family()
        drafter = _teacher(list(cfg["teachers"]), calls, int(cfg["teacher_calls"]))
        if not family or not drafter or STOP_FILE.exists():
            break
        try:
            record["loops"].append(_loop_family(ask, drafter, family, tasks_dir, log))
        except Exception as problem:
            record["notes"].append(f"loops for {family[0]['id']} and its family weren't drafted: {str(problem)[:120]}")
        calls += 1

    # 7a. The weekly benchmarks (core/benchmarks.py): graded by code, on this PC only
    from core import benchmarks

    if benchmarks.due() and not STOP_FILE.exists() and left() > 60 and cfg.get("benchmarks", True):
        record["benchmarks"] = benchmarks.run_now(int(min(benchmarks.RUN_MINUTES, left() - 10)))
        bench_loops = tuple(l for l in loops.LOOPS if l.id.startswith("answers.") and l.scope == "device")
        try:
            loops.run(None, "device", loops=bench_loops, force=True, heavy=True, tasks_dir=tasks_dir, log=log)
        except Exception as problem:
            record["notes"].append(f"the benchmark loops couldn't run: {str(problem)[:120]}")

    # 7a2. Study hall (core/specialists.py, DEC-0109): one of her specialists studies, in turn
    teacher_now = _teacher(list(cfg["teachers"]), calls, int(cfg["teacher_calls"]))
    if cfg.get("specialists", True) and teacher_now and not STOP_FILE.exists() and left() > 20:
        from core import specialists

        try:
            record["specialist"] = specialists.study(lambda prompt: ask(teacher_now, prompt))
        except Exception as problem:
            record["notes"].append(f"study hall didn't finish: {str(problem)[:120]}")
        calls += 1

    # 7b. The weekly self-audit (core/self_audit.py, DEC-0108): her code, her connections, her practices
    from core import self_audit

    if cfg.get("audit", True) and not STOP_FILE.exists() and self_audit.due():
        try:
            found = self_audit.weekly(tasks_dir=tasks_dir, log=log)
            record["audit"] = {"code": found["code"]["findings"], "connections": found["connections"]["findings"],
                               "connected": found["connections"]["share"], "tasks": found["tasks"]}
        except Exception as problem:
            record["notes"].append(f"the weekly self-audit didn't finish: {str(problem)[:120]}")

    # 8. The report
    record["teacher_calls"] = calls
    record["ended"] = clock().isoformat(timespec="seconds")
    store.append(record)
    from core import work_activity

    passed = sum(1 for l in record["lessons"] if l.get("outcome") == "pass")
    tried = sum(1 for l in record["lessons"] if l.get("outcome") in ("pass", "fail"))
    line = f"{record['focus']}: passed {passed} of {tried} lessons"
    work_activity.record(WHO, "night", "", line, log) if log else work_activity.record(WHO, "night", "", line)
    return record


# ------------------------------------------------------------------ starting it at night

def _marker(day: str) -> Path:
    return DEV_DATA / "night_school" / f"started-{day}"


def due(now: datetime, cfg: Optional[dict] = None) -> bool:
    """Pure-ish. Inside tonight's window, enabled, not stopped, and not started yet tonight."""
    cfg = cfg or settings()
    if not cfg["enabled"] or STOP_FILE.exists() or not (ROOT / "work").exists():
        return False
    try:
        hour, minute = (int(x) for x in str(cfg["start"]).split(":"))
    except ValueError:
        return False
    opens = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if now < opens:
        opens -= timedelta(days=1)  # a window that crosses midnight
    if not opens <= now < opens + timedelta(hours=float(cfg["hours"])) - timedelta(minutes=LESSON_MINUTES):
        return False
    return not _marker(opens.date().isoformat()).exists()


def maybe_start(now: Optional[datetime] = None) -> bool:
    """Called by MIA's daily check every few minutes: starts tonight's school in a process of its own."""
    import os

    now = now or datetime.now()
    if os.environ.get("PYTEST_CURRENT_TEST") or not due(now):
        return False  # never from a test run: a night is a real process with real teachers
    cfg = settings()
    hour, minute = (int(x) for x in str(cfg["start"]).split(":"))
    opens = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if now < opens:
        opens -= timedelta(days=1)
    marker = _marker(opens.date().isoformat())
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(now.isoformat(timespec="seconds"), encoding="utf-8")
    launch()
    return True


def launch() -> None:
    """A night in a process of its own (MIA's check at night, or Zac's "Start a night now")."""
    from core.dev_lab import _python

    log = DEV_DATA / "night_school" / "last_night.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "w", encoding="utf-8") as out:
        subprocess.Popen([_python(), "-m", "tools.night_school", "run"], cwd=str(ROOT), stdout=out,
                         stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
                         | getattr(subprocess, "DETACHED_PROCESS", 0) if sys.platform == "win32" else 0)


def summary() -> dict:
    """For the dev window: the latest nights, her report card, her choosing, her loops' reach, the settings."""
    from core import loop_coverage

    cov = loop_coverage.report()
    return {"nights": [dict(n, text=describe(n)) for n in nights()[-5:]][::-1], "card": report_card(),
            "choosing": choosing(), "settings": settings(), "step": plan_step(),
            "coverage": {"counts": cov["counts"], "share": cov["share"], "total": cov["total"],
                         "next": [r["id"] for r in loop_coverage.next_family()]}}


def describe(record: dict) -> str:
    """A night in a few lines, for the terminal and the dev window."""
    lines = [f"Night of {record.get('at', '')[:10]}: {record.get('focus', '')}"]
    if record.get("objective"):
        lines.append(f"  Curriculum: {record['objective']}")
    if record.get("her_pick"):
        agreed = record.get("pick_agreed")
        lines.append(f"  She chose: {record['her_pick']['area']} ({record['her_pick']['why']})"
                     + ("" if agreed is None else " - her teacher agreed" if agreed
                        else f" - her teacher would have chosen {record.get('better_pick') or 'differently'}"))
    for l in record.get("lessons", []):
        lines.append(f"  [{l.get('outcome')}] {l.get('title')}: {l.get('summary', '')[:120]}"
                     + (" (kept for Zac in the lab)" if l.get("kept") else ""))
        if l.get("note"):
            lines.append(f"      Lesson: {l['note']}")
    for s in record.get("shadow", []):
        lines.append(f"  Real work, {s['task']}: {s['outcome']} ({s.get('summary', '')[:100]})")
    if record.get("specialist"):
        s = record["specialist"]
        lines.append(f"  Study hall: the {s['specialist']} specialist kept {len(s['kept'])} notes"
                     + (f" ({'; '.join(s['kept'])})" if s["kept"] else "")
                     + (f", {len(s['refused'])} refused" if s["refused"] else ""))
    if record.get("audit"):
        a = record["audit"]
        lines.append(f"  Self-audit: {a['code']} places to improve, {a['connections']} connections to make "
                     f"({a['connected']:.0%} connected)" + (f"; opened {', '.join(a['tasks'])}" if a["tasks"] else ""))
    if record.get("benchmarks"):
        lines.append(f"  Benchmarks: {record['benchmarks'][-200:]}")
    for f in record.get("loops", []):
        lines.append(f"  Loops drafted for {', '.join(f['processes'])}" + (f": {f['task']}" if f.get("task") else ""))
    for n in record.get("notes", []):
        lines.append(f"  Note: {n}")
    return "\n".join(lines)
