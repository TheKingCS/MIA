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
    monkeypatch.setattr(at, "_turn", lambda context, conversation, prompt: SimpleNamespace(replies=["hi"]))
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
