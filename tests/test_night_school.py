"""Night School (DEC-0100, core/night_school.py): she chooses what to study, her teacher sets exercises
with a test that fails first, code grades her, the teacher's lesson comes back the next time, practice never
merges, and her picks are scored against her teacher's before she's trusted to choose."""

import json
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from core import night_school as ns
from core.dev_store import DevStore

PLAN = """### Phase A
1. ✅ **The loop registry**: done.
2. ⬜ **The development loops that need running**: the weekly suite,
   reverts per merge.
3. ⬜ **The remaining usage loops**: more.
"""


def test_the_next_step_of_the_plan():
    step = ns.plan_step(PLAN)
    assert step["number"] == 2 and step["title"] == "The development loops that need running"
    assert "reverts per merge" in step["text"] and "remaining usage" not in step["text"]
    assert ns.plan_step("1. ✅ **Done**") is None
    assert ns.plan_step("1. ⏸ **Waits on Zac**: the rest.\n2. 🔨 **Next**: this.")["number"] == 2


def test_what_she_chooses_and_why():
    progress = [{"id": "dev.knowledge", "what": "write-ups withdrawn", "state": "below", "why": "0.97 is above 0.3"},
                {"id": "pc.disk", "what": "free space", "state": "ok"}]
    ledger = {"screens": {"attempts": 0}, "engine changes": {"attempts": 4, "passed": 1, "rate": 0.25},
              "reviewing": {"attempts": 0}}
    areas = ns.self_assessment(progress, ledger, {}, todo_loops=12)
    assert areas[0]["area"] == "loop dev.knowledge"
    assert [a["area"] for a in areas][1:3] == ["skill engine changes", "skill screens"]
    assert areas[-1]["area"] == "loop coverage" and not any(a["area"] == "skill reviewing" for a in areas)


def exercise(**kw):
    base = {"title": "Count the stuck tasks", "skill": "engine changes", "files": ["core/work_dungeon.py"],
            "task": "Add a function.", "test_name": "tests/test_night_stuck_count.py",
            "test_code": "def test_it():\n    assert False\n", "real": False}
    return {**base, **kw}


def test_an_exercise_she_can_do():
    assert ns.valid_exercise(exercise()) == ""
    assert "never change" in ns.valid_exercise(exercise(files=["core/night_school.py"]))
    assert "never change" in ns.valid_exercise(exercise(files=["core/loops.py"]))
    assert "1 to 4" in ns.valid_exercise(exercise(files=["a.py", "b.py", "c.py", "d.py", "e.py"]))
    assert "named" in ns.valid_exercise(exercise(test_name="tests/test_loops.py"))
    assert "outside" in ns.valid_exercise(exercise(files=["../elsewhere.py"]))
    assert "no test" in ns.valid_exercise(exercise(test_code="x = 1"))


class FakeLab:
    WRITTEN, READY = "written", "ready"

    def __init__(self, root, passes=True, writes=True):
        self.root, self.passes, self.writes, self.rejected, self.n = root, passes, writes, [], 0

    def create(self, title, problem, evidence="", plan=""):
        self.n += 1
        self.plan = plan
        return SimpleNamespace(proposal_id=f"p{self.n}", status="drafted", note="", coder_said="")

    def folder(self, p):
        return self.root / p.proposal_id

    def write(self, pid, coder=None):
        return SimpleNamespace(proposal_id=pid, status=self.WRITTEN if self.writes else "not ready",
                               note="" if self.writes else "The coder changed nothing.", coder_said="added it")

    def check(self, pid, suite=None):
        return SimpleNamespace(proposal_id=pid, status=self.READY if self.passes else "not ready",
                               note="" if self.passes else "New failures: tests/test_night_stuck_count.py::test_it",
                               tests={"summary": "4950 passed"})

    def reject(self, pid, why=""):
        self.rejected.append(pid)


def test_a_lesson_is_graded_by_code_and_practice_never_merges(tmp_path):
    lab = FakeLab(tmp_path)
    done = ns.lesson(exercise(), lab=lab, one_test=lambda where, name: False, notes=["Read the whole function first."])
    assert done["outcome"] == "pass" and lab.rejected == ["p1"]  # practice: graded, then thrown away
    assert (tmp_path / "p1" / "tests" / "test_night_stuck_count.py").exists()  # the teacher's test, in her lab only
    assert "Read the whole function first." in lab.plan and "Files: core/work_dungeon.py" in lab.plan
    kept = ns.lesson(exercise(real=True), lab=lab, one_test=lambda where, name: False)
    assert kept.get("kept") and "p2" not in lab.rejected  # real progress she passed waits for Zac
    failed = ns.lesson(exercise(real=True), lab=FakeLab(tmp_path, passes=False), one_test=lambda w, n: False)
    assert failed["outcome"] == "fail" and not failed.get("kept")
    idle = FakeLab(tmp_path)
    idle.write = lambda pid, coder=None: SimpleNamespace(proposal_id=pid, status="written", note="",
                                                          coder_said="Nothing to do. (changed nothing)")
    nothing = ns.lesson(exercise(), lab=idle, one_test=lambda w, n: False)
    assert nothing["outcome"] == "fail" and idle.rejected == ["p1"]  # the teacher's test alone isn't her work
    early = FakeLab(tmp_path)
    invalid = ns.lesson(exercise(), lab=early, one_test=lambda where, name: True)
    assert invalid["outcome"] == "invalid" and early.rejected == ["p1"]  # a test that passes already proves nothing


@pytest.fixture
def school(tmp_path, monkeypatch):
    from core import dev_ledger, loop_coverage, loops, work_review

    monkeypatch.setattr(ns, "STOP_FILE", tmp_path / "STOP")
    monkeypatch.setattr(ns, "PLAN", tmp_path / "BUILD_PLAN.md")
    (tmp_path / "BUILD_PLAN.md").write_text(PLAN, encoding="utf-8")
    monkeypatch.setattr(ns, "_teacher", lambda order, used, budget: "claude-code" if used < budget else None)
    monkeypatch.setattr(loops, "run", lambda *a, **k: [])
    monkeypatch.setattr(loops, "summary", lambda c, s: [{"id": "dev.knowledge", "what": "write-ups withdrawn",
                                                         "state": "below", "why": "too many"}])
    monkeypatch.setattr(dev_ledger, "ledger", lambda *a, **k: {})
    monkeypatch.setattr(loop_coverage, "report", lambda *a, **k: {"share": 0.1, "counts": {"todo": 3}, "rows": []})
    monkeypatch.setattr(loop_coverage, "next_family", lambda *a, **k: [])
    monkeypatch.setattr(work_review, "lab_diff", lambda pid: "+def stuck(): ...")
    return SimpleNamespace(tmp=tmp_path, store=DevStore(tmp_path / "nights"), tasks=tmp_path / "tasks",
                           log=tmp_path / "activity.jsonl")


def teacher(agrees=True):
    asked = []

    def ask(provider, prompt):
        asked.append(prompt)
        if "set her exercises" in prompt:
            return "Here it is:\n" + json.dumps({"pick_agrees": agrees, "better_pick": "" if agrees else "screens",
                                                 "why": "the plan needs it",
                                                 "exercises": [exercise(files=["core/loops.py"]), exercise()]})
        return json.dumps({"note": "Name the edge case in the test before the fix."})
    return ask, asked


def test_a_night_of_school(school):
    ask, asked = teacher()
    clock = iter([datetime(2026, 11, 7, 1, 30) + timedelta(minutes=10 * i) for i in range(40)])
    night = ns.night(datetime(2026, 11, 7, 1, 30), ask=ask, lab=FakeLab(school.tmp), one_test=lambda w, n: False,
                     shadow=lambda tid: {"outcome": "pass", "summary": "ok"}, clock=lambda: next(clock),
                     config=dict(ns.DEFAULTS), store=school.store, tasks_dir=school.tasks, log=school.log)
    assert night["focus"].startswith("build plan step 2") and night["her_pick"]["area"] == "loop dev.knowledge"
    assert "The development loops that need running" in asked[0] and "dev.knowledge" in asked[0]
    outcomes = [l["outcome"] for l in night["lessons"]]
    assert outcomes == ["invalid", "pass"]  # the protected one was refused before she began
    assert night["lessons"][1]["note"] == "Name the edge case in the test before the fix."
    assert night["pick_agreed"] is True and night["teacher_calls"] == 2
    assert ns.report_card(school.store) == {"engine changes": {"lessons": 1, "passed": 1, "rate": 1.0, "bound": 0.27}}
    assert ns.notes_for("engine changes", school.store) == ["Name the edge case in the test before the fix."]
    assert "night" in school.log.read_text(encoding="utf-8")
    assert "Lesson: Name the edge case" in ns.describe(night)


def test_she_is_trusted_to_choose_only_on_evidence(school):
    for i in range(12):
        school.store.append({"at": f"2026-11-{i + 1:02d}T02:00:00", "pick_agreed": i != 3, "lessons": []})
    c = ns.choosing(school.store)
    assert c["nights"] == 12 and c["agreed"] == 11 and c["ready"]
    few = DevStore(school.tmp / "few")
    for i in range(4):
        few.append({"at": f"2026-11-{i + 1:02d}T02:00:00", "pick_agreed": True, "lessons": []})
    assert not ns.choosing(few)["ready"]  # four out of four is too little to go on


def test_the_night_stops_when_told(school):
    (school.tmp / "STOP").write_text("", encoding="utf-8")
    ask, asked = teacher()
    night = ns.night(datetime(2026, 11, 7, 1, 30), ask=ask, lab=FakeLab(school.tmp), one_test=lambda w, n: False,
                     shadow=lambda tid: {"outcome": "pass"}, clock=lambda: datetime(2026, 11, 7, 1, 30),
                     config=dict(ns.DEFAULTS), store=school.store, tasks_dir=school.tasks, log=school.log)
    assert asked == [] and night["lessons"] == [] and night["shadow"] == []


def test_when_school_starts(tmp_path, monkeypatch):
    monkeypatch.setattr(ns, "STOP_FILE", tmp_path / "STOP")
    monkeypatch.setattr(ns, "DEV_DATA", tmp_path)
    cfg = dict(ns.DEFAULTS)
    assert not ns.due(datetime(2026, 11, 6, 23, 0), cfg)
    assert ns.due(datetime(2026, 11, 7, 1, 31), cfg)
    assert not ns.due(datetime(2026, 11, 7, 5, 10), cfg)  # too little of the window left for a lesson
    late = dict(cfg, start="23:30")
    assert ns.due(datetime(2026, 11, 7, 0, 15), late)  # a window across midnight belongs to the night before
    (tmp_path / "night_school").mkdir()
    (tmp_path / "night_school" / "started-2026-11-06").write_text("x", encoding="utf-8")
    assert not ns.due(datetime(2026, 11, 7, 0, 15), late)  # once a night
    assert not ns.due(datetime(2026, 11, 7, 1, 31), dict(cfg, enabled=False))


def test_a_test_run_never_starts_a_real_night(monkeypatch):
    monkeypatch.setattr(ns, "due", lambda now, cfg=None: True)
    monkeypatch.setattr(ns, "launch", lambda: pytest.fail("a test started a real night"))
    assert ns.maybe_start(datetime(2026, 11, 7, 2, 0)) is False



def test_a_first_try_that_fails_its_test_gets_one_more_with_what_pytest_said(tmp_path):
    lab = FakeLab(tmp_path)
    asked = []

    def write(pid, coder=None, again=""):
        asked.append(again)
        return SimpleNamespace(proposal_id=pid, status="written", note="", coder_said="second" if again else "first")

    lab.write = write
    runs = iter([(False, "E   AttributeError: type object 'datetime' has no attribute 'timedelta'"), (True, "")])
    done = ns.lesson(exercise(), lab=lab, one_test=lambda w, n: False, test_run=lambda w, n: next(runs))
    assert done["retried"] and done["outcome"] == "pass" and done["said"] == "second"
    assert asked[0] == "" and "has no attribute 'timedelta'" in asked[1] and asked[1].endswith("Fix it.")
    asked.clear()
    passed_first = ns.lesson(exercise(), lab=lab, one_test=lambda w, n: False, test_run=lambda w, n: (True, ""))
    assert not passed_first.get("retried") and asked == [""]  # passing the first time: no second try
