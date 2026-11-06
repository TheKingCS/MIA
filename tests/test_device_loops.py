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
