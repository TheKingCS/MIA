"""Step 3's leftovers: turns traced by device, so glasses.voice can watch the glasses' turns; and a durable record of
when a linked phone last reached the PC (core/phone_link.py), for phone.link."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from core import loops, phone_link

BY_ID = {l.id: l for l in loops.LOOPS}


def test_a_turn_is_traced_with_its_device(monkeypatch):
    import core.assistant_turn as at
    import core.turn_trace as tt

    seen = []
    monkeypatch.setattr(at, "_turn", lambda context, conversation, prompt: SimpleNamespace(replies=["hi"], route="model"))
    monkeypatch.setattr(tt, "record", lambda context, conversation, prompt, turn, seconds, surface="": seen.append(surface))
    at.run_assistant_turn(None, None, "hello", "glasses")
    at.run_assistant_turn(None, None, "hello")
    assert seen == ["glasses", ""]


def test_the_glasses_voice_loop():
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    turns = ([{"at": now, "surface": "glasses", "seconds": 4, "model_answered": True}] * 8
             + [{"at": now, "surface": "glasses", "seconds": 40, "model_answered": True},
                {"at": now, "surface": "glasses", "seconds": 3, "model_answered": False}]
             + [{"at": now, "surface": "phone", "seconds": 90, "model_answered": False}] * 5)
    person = SimpleNamespace(traces=SimpleNamespace(recent=lambda n: turns))
    reading = BY_ID["glasses.voice"].measure(person)
    assert (reading.value, reading.n) == (0.2, 10) and loops.judge(BY_ID["glasses.voice"], reading, [])["state"] == "below"


def test_when_the_phone_last_reached_the_pc(tmp_path, monkeypatch):
    path = tmp_path / "phone_link.json"
    monkeypatch.setattr(phone_link, "_written", {})
    start = datetime(2026, 11, 6, 12, tzinfo=timezone.utc).timestamp()
    phone_link.seen("p1", path, now=start)
    phone_link.seen("p1", path, now=start + 60)  # a minute later: not written again
    assert phone_link.last(path)["p1"] == "2026-11-06T12:00:00+00:00"
    phone_link.seen("p1", path, now=start + 600)
    assert phone_link.last(path)["p1"] == "2026-11-06T12:10:00+00:00"
    later = datetime(2026, 11, 7, 0, 10, tzinfo=timezone.utc)
    assert phone_link.hours_since("p1", path, later) == 12.0 and phone_link.hours_since("p2", path, later) is None


def test_the_loops_predictions_against_what_happened():
    """Step 4: the work days the Loop planned, against the days actually worked."""
    from datetime import date

    from core.the_loop import predictions

    today = date(2026, 11, 20)
    r = SimpleNamespace(kind="work", rhythm_id="r1", ref="d1")
    made = ["2026-11-02", "2026-11-03", "2026-11-04", "2026-11-09", "2026-11-10", "2026-11-11", "2026-11-21"]
    runs = [SimpleNamespace(dungeon_id="d1", date=d, status="cleared") for d in
            ("2026-11-02", "2026-11-03", "2026-11-09", "2026-11-10", "2026-11-11", "2026-11-12")]
    runs.append(SimpleNamespace(dungeon_id="d1", date="2026-11-04", status="planned"))  # planned, never worked
    person = SimpleNamespace(loop=SimpleNamespace(rhythms=[r], made={"r1": made}), dungeon=SimpleNamespace(runs=runs))
    found = predictions(person, today)
    assert found == {"planned": 6, "missed": 1, "extra": 1, "off": 0.29}  # the 21st is still ahead: not counted
    assert predictions(SimpleNamespace(loop=SimpleNamespace(rhythms=[r], made={}), dungeon=SimpleNamespace(runs=runs)),
                       today) is None  # nothing planned yet: nothing to judge


def test_a_search_is_noted_when_it_ends_never_its_words(tmp_path, monkeypatch):
    from core import dev_store
    from core.search_manager import SearchManager

    monkeypatch.setattr(dev_store, "DEV_DATA", tmp_path)
    monkeypatch.setattr(loops, "DEV_DATA", tmp_path)
    monkeypatch.setattr(loops, "_has_repo", lambda: True)
    search = SearchManager(None)
    search.register_provider("broken", lambda q: 1 / 0)
    search.register_provider("notes", lambda q: [])
    search.search("grandmother's recipe")
    search.finished(0, False)
    search.finished(3, True)
    kept = dev_store.DevStore(tmp_path / "search").tail(10)
    assert [(r["found"], r["chosen"], r["failed"]) for r in kept] == [(0, False, ["broken"]), (3, True, [])]
    assert "recipe" not in str(kept)
    reading = BY_ID["search.empty"].measure(None)
    assert (reading.value, reading.n) == (0.5, 2) and "broken" in reading.detail


def test_every_check_that_speaks_through_the_gate_is_in_checks_dismissed():
    """A daily check that offers a message under a topic the loop can't place would go unwatched."""
    import re
    from pathlib import Path

    text = (Path(__file__).resolve().parents[1] / "core" / "application.py").read_text(encoding="utf-8")
    for name, fn in re.findall(r'\("([a-z_]+)", self\.(_check_[a-z_]+)\)', text):
        body = re.search(r"\n    def " + fn + r"\(.*?(?=\n    def |\Z)", text, re.S).group(0)
        for topic in re.findall(r'topic=f?["\']([a-z_]+)', body):
            if topic != "birthday":  # a greeting once a year: declined in work/loop_coverage.json
                assert loops._check_of(topic) == name, (name, topic)


def test_which_check_is_dismissed_most():
    entries = ([{"topic": "pattern_insight", "action": "act", "dismissed_at": "x"}] * 5
               + [{"topic": "pattern_insight", "action": "act"}]
               + [{"topic": "finding_budget", "action": "act", "dismissed_at": "x"}] * 2
               + [{"topic": "finding_rent", "action": "act"}] * 3
               + [{"topic": "checkin", "action": "act", "dismissed_at": "x"}] * 3  # 3 sent: too few to judge
               + [{"topic": "grow_alert", "action": "act", "urgency": "urgent", "dismissed_at": "x"}] * 9
               + [{"topic": "unknown", "action": "act", "dismissed_at": "x"}] * 9)
    context = SimpleNamespace(communication=SimpleNamespace(entries_since=lambda since: entries))
    reading = BY_ID["checks.dismissed"].measure(context)
    assert (reading.value, reading.n) == (0.83, 11)
    assert reading.detail == "dismissed most: pattern insight 5 of 6, findings 2 of 5"


def test_recurring_missions_missed():
    """The recurring-missions loop counts the past days' occurrences not done (not today's, not old ones, not one-offs) and names the one most often missed."""
    today = datetime.now(timezone.utc).date()
    day = lambda n: (today - timedelta(days=n)).isoformat()
    m = lambda name, n, status, tid="t1": SimpleNamespace(name=name, occurrence_key=day(n), status=status,
                                                         recurring_template_id=tid)
    found = ([m("Stretch", n, "completed") for n in range(1, 9)] + [m("Run", n, "active", "t2") for n in range(1, 5)]
             + [m("Run", 0, "active", "t2"), m("Run", 40, "active", "t2"), m("One-off", 2, "active", None)])
    context = SimpleNamespace(missions=SimpleNamespace(all_missions=lambda: found))
    reading = BY_ID["missions.recurring"].measure(context)
    assert (reading.value, reading.n) == (0.33, 12)  # today, 40 days ago and the one-off aren't counted
    assert reading.detail == "4 of 12 not done; most often missed: Run (4 of 4)"


def test_an_app_that_breaks_on_opening_is_noted_not_fatal(monkeypatch):
    from gui.main_window import MainWindow
    import core.child_accounts as ca
    import core.failure_actions as fa

    noted, said = [], []
    monkeypatch.setattr(ca, "app_allowed", lambda context, module_id: True)
    monkeypatch.setattr(fa, "page_error", lambda context, page, message: noted.append((page, message)))

    class Broken:
        def on_load(self):
            raise ValueError("no data file")

    window = SimpleNamespace(module_manager=SimpleNamespace(get=lambda mid: Broken()), context=None,
                             _module_widgets={}, statusBar=lambda: SimpleNamespace(showMessage=lambda *a: said.append(a)))
    window._note_broken = lambda mid, problem: MainWindow._note_broken(window, mid, problem)
    MainWindow.open_module(window, "garage")
    assert noted == [("app:garage", "ValueError: no data file")] and window._module_widgets == {} and said


def test_the_screens_that_broke(monkeypatch):
    found = [{"kind": "page_error", "page": "app:garage"}, {"kind": "page_error", "page": "budget"},
             {"kind": "page_error", "page": "app:garage"}]
    monkeypatch.setattr(loops, "_failures", lambda context, kinds, days=7: [e for e in found if e["kind"] in kinds])
    reading = BY_ID["screens.broken"].measure(SimpleNamespace(failures=object()))
    assert (reading.value, reading.n, reading.detail) == (3, 3, "3 in 7 days: app:garage, budget")
    assert "module:garage" in BY_ID["screens.broken"].covers and "module:module_browser" in BY_ID["screens.broken"].covers


def test_photos_still_only_on_the_phone(monkeypatch):
    import core.memory_vault as mv

    monkeypatch.setattr(mv, "is_on", lambda context: True)
    old, new = "2026-01-02T10:00:00", datetime.now().isoformat(timespec="seconds")
    items = {f"s{n}": {"taken_at": old, "sources": [f"p{n}"], "on_pc": n < 18} for n in range(20)}
    items["fresh"] = {"taken_at": new, "sources": ["pf"], "on_pc": False}  # under a week: not judged yet
    items["gone"] = {"taken_at": old, "sources": ["px"], "on_pc": False}  # no longer on the phone
    vault = SimpleNamespace(items=items, status={"state": "waiting_wifi"},
                            on_phone=lambda i: [p for p in i["sources"] if p != "px"])
    reading = BY_ID["vault.coverage"].measure(SimpleNamespace(memory_vault=vault))
    assert (reading.value, reading.n) == (0.1, 20) and reading.detail.endswith("the vault is waiting wifi")
    monkeypatch.setattr(mv, "is_on", lambda context: False)
    assert BY_ID["vault.coverage"].measure(SimpleNamespace(memory_vault=vault)) is None  # switched off: nothing to judge



def test_the_lab_loop_counts_real_proposals_only(monkeypatch):
    """T-0049: Night School's exercises and the shadow attempts are rejected by design; they never count."""
    import core.dev_lab as lab

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    p = lambda status, evidence="": SimpleNamespace(status=status, evidence=evidence, created_at=now)  # noqa: E731
    found = [p("merged"), p("merged"), p("rejected"), p("reverted"), p("ready"),
             p("rejected", "Night School exercise"), p("rejected", "Task T-0007 (shadow)")]
    monkeypatch.setattr(lab, "all_proposals", lambda: found)
    reading = BY_ID["dev.lab"].measure(None)
    assert (reading.value, reading.n, reading.detail) == (0.5, 4, "2 of 4 went in; 1 turned down, 1 reverted")



def test_the_phones_own_packages_are_audited(tmp_path, monkeypatch):
    from core import dev_checks

    for name in ("cryptography-42.0.8.dist-info", "typing_extensions-4.16.0.dist-info", "pip-25.3.dist-info"):
        (tmp_path / "python" / "env" / name).mkdir(parents=True)
    found = dev_checks.phone_packages(tmp_path)
    assert found == {"cryptography": "42.0.8", "typing-extensions": "4.16.0"}  # pip only installs, never runs
    assert dev_checks.phone_packages(tmp_path / "never built") == {}
    monkeypatch.setattr(loops, "_has_repo", lambda: True)
    monkeypatch.setattr(dev_checks, "phone_packages", lambda: found)
    monkeypatch.setattr(dev_checks, "vulnerable", lambda packages: {"checked": 2, "packages": {"cryptography": ["A", "B"]}})
    reading = BY_ID["phone.vulnerable"].measure(None)
    assert (reading.value, reading.n) == (1, 2) and reading.detail.endswith("cryptography 42.0.8 (2)")



def test_courses_under_way_that_stalled():
    recent = datetime.now(timezone.utc).isoformat(timespec="seconds")
    lesson = lambda done, at="": SimpleNamespace(completed=done, completed_at=at)  # noqa: E731
    courses = {"c1": SimpleNamespace(course_id="c1", name="Welding"), "c2": SimpleNamespace(course_id="c2", name="Spanish"),
               "c3": SimpleNamespace(course_id="c3", name="Done one"), "c4": SimpleNamespace(course_id="c4", name="Not begun")}
    lessons = {"c1": [lesson(True, "2026-01-02T10:00:00"), lesson(False)], "c2": [lesson(True, recent), lesson(False)],
               "c3": [lesson(True, "2026-01-02T10:00:00")], "c4": [lesson(False)]}
    room = SimpleNamespace(all_subjects=lambda: [SimpleNamespace(subject_id="s1")],
                           courses_for_subject=lambda sid: list(courses.values()),
                           lessons_for_course=lambda cid: lessons[cid])
    reading = BY_ID["classroom.stalled"].measure(SimpleNamespace(classroom=room))
    assert (reading.value, reading.n) == (0.5, 2) and reading.detail.endswith(": Welding")
