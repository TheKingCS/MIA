"""
core.curriculum
=================

What MIA studies to become good at everything a computer can be made to do
(Zac, 2026-11-07: "I want her very well trained on how to do all things
computer related, software engineering, design, apps, web pages,
deploying, cyber security, pen testing, monitoring etc and creating
documentation for use"). DEC-0107.

**Tracks**, each with **objectives** in three levels (foundation, working,
expert). An objective says what she can do once she has it, how she
practises it **on her own code** (so every exercise is real, and graded by
a test that fails before and passes after, the way Night School grades),
and where to look. Practising on herself means the work makes her better
twice: she learns, and the code she learns on improves.

**How it's used** (core/night_school.py): every night, one of her lessons
is for her next curriculum objective (`next_objective()`): the track she's
furthest behind in, its first objective she hasn't mastered. An objective
is mastered after `MASTERY` lessons for it passed. Her teacher sets that
lesson, as it sets the others.

**On the learning-path engine** (DEC-0112): she learns through the same code
a person does (core/paths.py). Each track is a `Program` (`PROGRAMS`, stages
by level, each objective a check verified "tested"); her own PathBook
(`mia_book()`, data/dev/mia_paths) keeps every lesson as practice and an
attempt (`record_lesson()`), each track's stage, and her stats, and
`progress_of()` reads what she has mastered from it.

**The security tracks have rules** (`SECURITY_RULES`, given to her teacher
with every security or pen-testing lesson): she attacks only herself: her
own code in the lab copy and her own server run in-process by a test
(FastAPI's TestClient), never a network address, never anyone else's
system, never a real credential. A weakness she finds becomes a test that
proves it and a fix, through the lab like any change: Zac approves it.

`python -m tools.night_school curriculum` shows where she stands.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

LEVELS = ("foundation", "working", "expert")
MASTERY = 2  # lessons passed for an objective before it counts as hers

SECURITY_RULES = (
    "Security practice is on MIA herself only: her own code in the lab copy, and her own server started in-process "
    "by the test (fastapi.testclient.TestClient on server.app), never a network address, never anyone else's system, "
    "never a real password, token or person's data (make up test values). The exercise's test proves the weakness "
    "exists before the change and is closed after it. No tool that attacks other systems is written.")


@dataclass(frozen=True)
class Objective:
    """One thing she can do once she has it: its id, track and level, what she can do, how she practises it on her
    own code, and the files to start from."""
    id: str
    track: str
    level: str
    can: str
    practice: str
    files: tuple[str, ...] = ()


@dataclass(frozen=True)
class Track:
    """One area of computing: its id and name, why it matters to her, and its objectives, foundation first."""
    id: str
    name: str
    why: str
    objectives: tuple[Objective, ...]


def _o(track: str, n: int, level: str, can: str, practice: str, *files: str) -> Objective:
    """An objective, its id made from its track and number (engineering.1)."""
    return Objective(f"{track}.{n}", track, level, can, practice, files)


TRACKS: tuple[Track, ...] = (
    Track("engineering", "Software engineering", "every change she makes to herself is software engineering", (
        _o("engineering", 1, "foundation", "read a function and say exactly what it does, including its edge cases",
           "add a test that pins down one function's behaviour on an empty, a missing and a wrong input",
           "core/region.py", "core/today.py"),
        _o("engineering", 2, "foundation", "make a small change without breaking anything around it",
           "fix a failing or missing behaviour in one function, changing nothing else", "core/"),
        _o("engineering", 3, "working", "refactor: make code clearer while every test stays green",
           "split one long function into named parts with the same behaviour, proved by its tests", "core/"),
        _o("engineering", 4, "working", "design a small module: its data, its functions, its tests",
           "build a small pure-logic helper the spec describes, with its own test file", "core/"),
        _o("engineering", 5, "expert", "keep her architecture's rules (core knows nothing of gui or modules)",
           "find and remove one layering break or duplicated logic, proved by a test", "core/", "docs/ARCHITECTURE.md"),
    )),
    Track("testing", "Testing and debugging", "a change is only as good as the test that proves it", (
        _o("testing", 1, "foundation", "write a pytest test that fails for the right reason",
           "write a test for a behaviour that's missing, so it fails now with a clear message", "tests/"),
        _o("testing", 2, "working", "find a bug's cause from its traceback and fix the cause, not the symptom",
           "given a failing test, fix the code (never the test) so it passes", "core/", "tests/"),
        _o("testing", 3, "expert", "test what's hard to test: time, files, failures, other services",
           "test a function that reads the clock or a file by passing them in, with tmp_path and a fixed date",
           "core/", "tests/"),
    )),
    Track("documentation", "Documentation", "so anyone, MIA included, can rebuild and use what's built (DEC-0104)", (
        _o("documentation", 1, "foundation", "write a docstring that says what a function is, does and how, truly",
           "document the undocumented functions of one small file (python -m tools.docs next); the test checks the "
           "count drops and each docstring names what the code really does", "core/", "tools/docs.py"),
        _o("documentation", 2, "working", "write a guide a person can follow: steps, examples, what can go wrong",
           "write or fix one section of a user guide so its steps match what the code does", "docs/user_help/"),
        _o("documentation", 3, "expert", "write a knowledge entry: what was built, how, why, what went wrong",
           "write a vault entry (core/dev_knowledge.py) for a finished task, citing its sources",
           "core/dev_knowledge.py", "work/knowledge/"),
    )),
    Track("design", "Design and user experience", "what people see of her has to be clear and kind to use", (
        _o("design", 1, "foundation", "use the theme's tokens, never a hard-coded colour (DEC-0023)",
           "replace a hard-coded colour in a page's CSS with its token; a test checks no literal colour is left",
           "web/tokens.css", "web/"),
        _o("design", 2, "working", "make a screen accessible: labels, contrast, keyboard, screen readers",
           "give a page's buttons and inputs labels and roles; a test parses the HTML and checks each has one", "web/"),
        _o("design", 3, "expert", "design a screen from its data: what matters first, what can wait",
           "lay out a page's data the way docs/design/STARK_INTERFACE.md describes, checked by a structure test",
           "docs/design/STARK_INTERFACE.md", "web/"),
    )),
    Track("web", "Web pages", "the web is all of her front end (DEC-0017)", (
        _o("web", 1, "foundation", "write a working page on the shared frame that reads her state",
           "add one field to an existing page from data core already assembles, with a test of the data", "web/",
           "core/web_surfaces.py"),
        _o("web", 2, "working", "build an API endpoint with its validation and its tests",
           "add or fix one /api endpoint in server/app.py and test it with TestClient", "server/app.py"),
        _o("web", 3, "expert", "keep pages fast and safe: no injected HTML, no blocking calls",
           "find one place a page puts text into the DOM unsafely and make it safe, with a test", "web/"),
    )),
    Track("apps", "Apps", "her desktop apps and her phone app are how people live with her", (
        _o("apps", 1, "foundation", "write a module that follows her module contract (docs/MODULE_SPEC.md)",
           "fix or extend one small module so the validator and its test pass", "modules/", "docs/MODULE_SPEC.md"),
        _o("apps", 2, "working", "move a Qt screen's logic into core so the web and phone can share it",
           "lift one calculation out of a module's widget into core, with a test", "modules/", "core/"),
        _o("apps", 3, "expert", "understand the phone app (Kotlin) well enough to change it safely",
           "explain and test one piece of the phone's API contract from the server side",
           "android-phone/", "server/app.py"),
    )),
    Track("deploying", "Deploying", "built isn't done until it runs where people use it", (
        _o("deploying", 1, "foundation", "say what a deploy needs: its packages, its settings, its start-up",
           "make one setup check (tools/pc_check.py) report something it misses today, with a test",
           "tools/pc_check.py", "requirements.txt"),
        _o("deploying", 2, "working", "read and fix a CI workflow", "fix or extend one check a workflow runs, "
           "with a test that runs the same check locally", ".github/workflows/"),
        _o("deploying", 3, "expert", "make an install reproducible and undoable",
           "make one install or setup step safe to run twice, proved by a test", "deploy/", "tools/"),
    )),
    Track("security", "Cyber security (defence)", "she holds a household's private life; it has to be safe", (
        _o("security", 1, "foundation", "spot the common weaknesses: injection, path traversal, secrets in code",
           "find one input that reaches a file path or a command and prove it's checked, with a test", "core/",
           "server/app.py"),
        _o("security", 2, "working", "check who's allowed: every endpoint and action asks the right person",
           "write a test proving one endpoint refuses a request without the right token or person",
           "server/app.py", "core/actions.py"),
        _o("security", 3, "expert", "review a change for security the way a reviewer would",
           "find a real weakness in one file, write the test that proves it, and close it", "core/", "server/"),
    )),
    Track("pentest", "Penetration testing (on herself only)", "finding her own weaknesses before anyone else does", (
        _o("pentest", 1, "foundation", "map her own attack surface: every endpoint, who can call it, what it takes",
           "write a test that lists server.app's routes and checks each one needs a token unless it's on the public "
           "list", "server/app.py"),
        _o("pentest", 2, "working", "attack her own API with bad input (oversized, malformed, traversal, injection)",
           "write tests that send hostile input to one endpoint in-process and prove it's refused cleanly",
           "server/app.py"),
        _o("pentest", 3, "expert", "chain small weaknesses into a real one, and close the chain",
           "find two small issues that together expose something, prove it with a test, and fix the weaker link",
           "server/", "core/"),
    )),
    Track("monitoring", "Monitoring", "she should know she's unwell before anyone tells her", (
        _o("monitoring", 1, "foundation", "read her own logs and loops and say what's wrong",
           "make one loop's detail line say more about what it measured, with a test", "core/loops.py"),
        _o("monitoring", 2, "working", "add a loop for a process that has none (DEC-0101)",
           "write the measure for one process that's still to do, with its test", "core/loops.py",
           "core/loop_coverage.py"),
        _o("monitoring", 3, "expert", "tell a real problem from noise: thresholds, trends, how much data",
           "tune one loop's floor or minimum readings from its own history, justified in the test", "core/loops.py"),
    )),
)

BY_ID = {o.id: o for t in TRACKS for o in t.objectives}


def progress(lessons: Iterable[dict]) -> dict[str, dict]:
    """Pure logic. For each objective, how many of its lessons were tried and passed, and whether it's mastered,
    from lesson records that carry an `objective`."""
    out = {o: {"tried": 0, "passed": 0, "mastered": False} for o in BY_ID}
    for lesson in lessons:
        row = out.get(str(lesson.get("objective") or ""))
        if row is None or lesson.get("outcome") not in ("pass", "fail"):
            continue
        row["tried"] += 1
        row["passed"] += lesson["outcome"] == "pass"
        row["mastered"] = row["passed"] >= MASTERY
    return out


def standing(rows: dict[str, dict]) -> list[dict]:
    """Pure logic. Each track with how many of its objectives are mastered and the level she has reached (the
    highest level with every objective mastered, or none)."""
    out = []
    for t in TRACKS:
        mastered = [o for o in t.objectives if rows.get(o.id, {}).get("mastered")]
        level = "none"
        for name in LEVELS:
            those = [o for o in t.objectives if o.level == name]
            if those and all(o in mastered for o in those):
                level = name
            else:
                break
        out.append({"track": t.id, "name": t.name, "mastered": len(mastered), "of": len(t.objectives),
                    "level": level})
    return out


def next_objective(rows: dict[str, dict]) -> Optional[Objective]:
    """Pure logic. What she studies next: in the track with the smallest share mastered, its first objective not yet
    mastered. On a tie, the track she has tried least, then the curriculum's order, so the tracks take turns even
    while she's failing one. None once everything is."""
    best = None
    for order, t in enumerate(TRACKS):
        left = [o for o in t.objectives if not rows.get(o.id, {}).get("mastered")]
        if not left:
            continue
        rank = (1 - len(left) / len(t.objectives), sum(rows.get(o.id, {}).get("tried", 0) for o in t.objectives),
                order)
        if best is None or rank < best[0]:
            best = (rank, left[0])
    return best[1] if best else None


def lesson_brief(objective: Objective) -> str:
    """What her teacher is told about tonight's curriculum lesson: the objective, how to practise it on her own
    code, where to start, and the security rules for a security or pen-testing objective."""
    t = next(t for t in TRACKS if t.id == objective.track)
    text = (f"Curriculum objective {objective.id} ({t.name}, {objective.level}): she can {objective.can}. "
            f"Practise it on her own code: {objective.practice}."
            + (f" Start from: {', '.join(objective.files)}." if objective.files else ""))
    if objective.track in ("security", "pentest"):
        text += " " + SECURITY_RULES
    return text


# ------------------------------------------------------------------ on the learning-path engine (DEC-0112)
#
# MIA learns through the same code a person does (core/paths.py): each track is a Program whose stages are its
# levels, each objective a check verified "tested" (Night School's test fails before and passes after), and her own
# PathBook (data/dev/mia_paths) keeps her practice, her attempts and the stage of each track, as a person's does.
# A check counts as passed once it's mastered (MASTERY lessons passed); every lesson before that is kept as an
# attempt not yet passed, its value the passes so far.

BOOK_DIR = Path(__file__).resolve().parent.parent / "data" / "dev" / "mia_paths"


def _tested(context, program, check, payload) -> dict:
    """The verifier for MIA's own checks: they're tested by Night School's grading, never by something sent."""
    raise ValueError("MIA's curriculum checks are tested by Night School: a test that fails before and passes after.")


def program_for(track: Track):
    """A track as a learning-path program: a stage for each level it has (in order), a lesson for each objective
    (how she practises it, and where to start), and a check for each, verified "tested"."""
    from core.paths import Check, Lesson, Program, Stage

    stages = []
    for level in LEVELS:
        mine = [o for o in track.objectives if o.level == level]
        if not mine:
            continue
        lessons = tuple(Lesson(f"{o.id}_practice", f"{o.id}: {o.can}",
                               (o.practice,) + ((f"Start from: {', '.join(o.files)}",) if o.files else ()), track.why)
                        for o in mine)
        checks = tuple(Check(o.id, f"She can {o.can}", "tested") for o in mine)
        stages.append(Stage(len(stages) + 1, level.capitalize(), f"{track.name}, {level}", lessons, checks))
    return Program(f"mia_{track.id}", track.name, "", "🧠", track.why, (), tuple(stages),
                   verifiers={"tested": _tested}, plan=(45, 7))


PROGRAMS = {t.id: program_for(t) for t in TRACKS}


def mia_book(folder: Optional[Path] = None):
    """MIA's own learning paths, every track started (her goal is the track's why; a lesson a night is her plan)."""
    from core.paths import PathBook

    book = PathBook(None, data_dir=folder or BOOK_DIR)
    for track in TRACKS:
        if book.path(PROGRAMS[track.id].id) is None:
            book.start(PROGRAMS[track.id], track.why, 45, 7)
    return book


def progress_of(book) -> dict[str, dict]:
    """For each objective, from her own book: how many lessons were tried and passed, and whether it's mastered."""
    out = {o: {"tried": 0, "passed": 0, "mastered": False} for o in BY_ID}
    for track in TRACKS:
        record = book.path(PROGRAMS[track.id].id) or {"attempts": []}
        for a in record["attempts"]:
            row = out.get(a["check"])
            if row is None:
                continue
            row["tried"] += 1
            row["passed"] += a.get("detail") == "lesson passed"
            row["mastered"] = row["mastered"] or bool(a["passed"])
    return out


def record_lesson(book, objective_id: str, passed: bool, minutes: float = 45, title: str = "") -> dict:
    """One Night School lesson for an objective, on her own path: a practice session, and an attempt, passed when
    this lesson brings the objective to MASTERY passes. Returns the attempt."""
    objective = BY_ID[objective_id]
    program = PROGRAMS[objective.track]
    book.log_practice(program, minutes, title or objective.can)
    passes = progress_of(book)[objective_id]["passed"] + (1 if passed else 0)
    mastered_now = passed and passes >= MASTERY and not book.passed(program.id, objective_id)
    return book.attempt(program, objective_id, mastered_now, value=float(passes), how="tested",
                        detail="lesson passed" if passed else "lesson failed")
