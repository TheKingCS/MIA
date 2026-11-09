"""
tests.test_momentum
=====================

Natural Momentum (core/momentum.py, DEC-0148): runs of things done found in the history, what they have in common
said as counts once there are enough, what tends to follow what, whether the person is in flow (and the gate holding
her non-urgent messages then), one easy start in their usual hour, and tomorrow's prep before a work day.
"""

from datetime import datetime, timedelta
from types import SimpleNamespace

from core import momentum
from core.communication_gate import AMBIENT, DEFER, TIMELY, URGENT, Candidate, GateState, decide_batch

NOW = datetime(2026, 11, 20, 9, 0)


def _e(at: datetime, what: str, kind: str = "did"):
    """A done thing in the history."""
    from core.did_it import key

    return SimpleNamespace(at=at.isoformat(timespec="seconds"), type=kind, summary=f"Did: {what}",
                           payload={"key": key(what)})


def _mornings(days=(3, 2, 1), start_hour=8):
    """Three mornings that each went dishes, laundry, kitchen, ten minutes apart."""
    out = []
    for d in days:
        t = (NOW - timedelta(days=d)).replace(hour=start_hour, minute=0)
        out += [_e(t, "put away the dishes"), _e(t + timedelta(minutes=10), "started the laundry"),
                _e(t + timedelta(minutes=25), "picked up the kitchen")]
    return out


def _world(monkeypatch, events, work=(), sleep=()):
    """A context whose history is `events`, with shifts on `work` days and these nights of sleep."""
    monkeypatch.setattr(momentum, "done_events", lambda context, now=None: list(events))
    return SimpleNamespace(dungeon=SimpleNamespace(runs=[SimpleNamespace(date=d) for d in work]),
                           health=SimpleNamespace(sleep=list(sleep)))


def test_runs_are_three_or_more_things_done_close_together():
    """Each within RUN_GAP of the last; a long gap ends a run; two things aren't a run."""
    t = NOW.replace(hour=8)
    events = [_e(t, "a thing"), _e(t + timedelta(minutes=20), "b thing"), _e(t + timedelta(minutes=50), "c thing"),
              _e(t + timedelta(hours=4), "d thing"), _e(t + timedelta(hours=4, minutes=5), "e thing")]
    assert [len(r) for r in momentum.windows(events)] == [3]


def test_what_the_runs_share_is_said_as_counts_once_there_are_enough(monkeypatch):
    """Nothing before three runs; then what started them, the time of day, a day off, and a full night before."""
    assert momentum.findings(_world(monkeypatch, _mornings(days=(2, 1)))) == []
    days = [(NOW - timedelta(days=d)).date().isoformat() for d in (3, 2, 1)]
    nights = [{"night": (NOW - timedelta(days=d + 1)).date().isoformat(), "hours": 8.0} for d in (3, 2)]
    found = momentum.findings(_world(monkeypatch, _mornings(), work=[days[0]], sleep=nights), NOW)
    assert found == ["3 of your 3 runs of getting things done began with put away the dishes.",
                     "3 of 3 began in the morning.", "2 of 3 were on a day off.",
                     "2 of the 2 with sleep logged came after a full night."]


def test_what_usually_follows_is_known_and_said_only_when_it_has_happened_enough(monkeypatch):
    """Laundry followed the dishes three mornings of three: that's a chain; once isn't."""
    from core.did_it import key

    context = _world(monkeypatch, _mornings())
    assert momentum.next_in_chain(context, key("put away the dishes"), NOW) == "started the laundry"
    assert momentum.next_in_chain(_world(monkeypatch, _mornings(days=(1,))), key("put away the dishes"), NOW) is None


def test_two_things_done_in_half_an_hour_is_flow_and_the_gate_holds_everything_but_the_urgent(monkeypatch):
    """In flow, timely and ambient messages wait (not dropped); urgent ones still go."""
    recent = [_e(NOW - timedelta(minutes=20), "started the laundry"), _e(NOW - timedelta(minutes=5), "made coffee")]
    assert momentum.in_flow(_world(monkeypatch, recent), NOW)
    assert not momentum.in_flow(_world(monkeypatch, recent[:1]), NOW)
    batch = [Candidate("tip", "A tip", "x", AMBIENT), Candidate("calendar", "Soon", "y", TIMELY),
             Candidate("alarm", "Now", "z", URGENT)]
    decisions = decide_batch(batch, NOW, GateState(in_flow=True), {})
    assert [d.action for d in decisions[:2]] == [DEFER, DEFER] and decisions[2].action != DEFER
    assert all(d.candidate.not_before for d in decisions[:2])


def test_an_easy_start_in_their_usual_hour_and_tomorrows_prep_before_a_work_day(monkeypatch):
    """At 8 with nothing done yet, the usual first thing; not at 3 in the afternoon or once something's done. The
    evening before a shift, the prep they've done on two such evenings; not once it's done tonight."""
    context = _world(monkeypatch, _mornings())
    assert "put away the dishes" in momentum.easy_start(context, NOW.replace(hour=8))
    assert momentum.easy_start(context, NOW.replace(hour=15)) is None
    busy = _world(monkeypatch, _mornings() + [_e(NOW.replace(hour=7), "fed the cat")])
    assert momentum.easy_start(busy, NOW.replace(hour=8)) is None
    evening = NOW.replace(hour=20)
    preps = [_e((evening - timedelta(days=d)), "made tomorrow's coffee") for d in (3, 1)]
    tomorrow = (evening + timedelta(days=1)).date().isoformat()
    line = momentum.tomorrow_prep(_world(monkeypatch, preps, work=[tomorrow]), evening)
    assert line == ("You work tomorrow. Last times you made tomorrow's coffee the night before. "
                    "Want to do that tonight?")
    done = preps + [_e(evening - timedelta(minutes=30), "made tomorrow's coffee")]
    assert momentum.tomorrow_prep(_world(monkeypatch, done, work=[tomorrow]), evening) is None
    assert momentum.tomorrow_prep(_world(monkeypatch, preps), evening) is None  # no shift tomorrow
