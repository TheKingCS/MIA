"""Tests for what MIA learned on her own (DEC-0282, LS-10, core/learned.py): each habit with its evidence and its own
reset, which never touches what he set himself or a break he asked for; and the daily budget for her own work."""
from datetime import datetime, timedelta
from types import SimpleNamespace

from core import learned
from core.communication_gate import ACT, CommunicationGate
from core.homeostasis import Homeostasis
from core.response_style import StyleBook

NOW = datetime(2026, 11, 18, 12, 0)


def _gate(tmp_path, entries):
    """A gate whose log holds `entries`, at a fixed time."""
    gate = CommunicationGate(SimpleNamespace(config=None, events=None, notifications=None), data_dir=tmp_path)
    gate.clock = lambda: NOW
    gate._log = entries
    return gate


def _sent(topic, days_ago, **marks):
    """One message she sent `days_ago` days ago, with what he did with it."""
    at = NOW - timedelta(days=days_ago)
    entry = {"action": ACT, "topic": topic, "title": topic.replace("_", " ").title(), "at": at.isoformat()}
    for key, after in marks.items():
        entry[key] = (at + timedelta(minutes=after)).isoformat()
    return entry


def test_a_learned_pace_is_shown_with_its_evidence_and_forgotten_alone(tmp_path):
    """Opened most of a kind: a faster pace, said with why; forgetting it leaves another kind's pace as it was."""
    entries = [_sent("good_news", d, opened_at=5) for d in (1, 2, 3, 4)] + \
              [_sent("tips", d, acted_at=5) for d in (1, 2, 3)]
    gate = _gate(tmp_path, entries)
    context = SimpleNamespace(communication=gate, response_style=None)
    found = {h.habit_id: h for h in learned.habits(context)}
    assert set(found) == {"pace:good_news", "pace:tips"}
    assert found["pace:good_news"].evidence == "You've opened or used most of these lately."
    assert learned._describe(context, {"habit_id": "pace:good_news"}).startswith("Forget what I learned: I offer Good News")
    learned._execute(context, {"habit_id": "pace:good_news"})
    assert set(h.habit_id for h in learned.habits(context)) == {"pace:tips"}


def test_a_break_she_took_is_forgettable_and_one_he_asked_for_isnt_listed(tmp_path):
    """Dismissed several in a row: her own break, listed and ended by a reset; a break he asked for stays off the list."""
    entries = [_sent("deals", d, dismissed_at=1) for d in (1, 2, 3, 4)] + [_sent("chores", 1)]
    gate = _gate(tmp_path, entries)
    gate.mute("chores", now=NOW)
    context = SimpleNamespace(communication=gate, response_style=None)
    breaks = [h.habit_id for h in learned.habits(context) if h.habit_id.startswith("break:")]
    assert breaks == ["break:deals"]
    learned._execute(context, {"habit_id": "break:deals"})
    assert not [h for h in learned.habits(context) if h.habit_id.startswith("break:")]
    assert any(p["topic"] == "chores" for p in gate.paused())  # his own break is untouched


def test_an_answer_style_learned_from_picks_resets_but_one_he_chose_never_shows(tmp_path):
    """A/B picks make a habit; a dimension he chose outright isn't hers to forget."""
    from core.response_style import DIMENSIONS

    dims = list(DIMENSIONS)
    book = StyleBook(data_dir=tmp_path)
    first, second = dims[0], dims[1]
    a, b = DIMENSIONS[first][:2]
    book.record_pick(first, a, b)
    book.record_pick(first, a, b)
    book.choose(second, DIMENSIONS[second][0])
    context = SimpleNamespace(communication=None, response_style=book)
    found = [h.habit_id for h in learned.habits(context)]
    assert found == [f"style:{first}"]
    learned._execute(context, {"habit_id": f"style:{first}"})
    assert learned.habits(context) == [] and book.tally(second)  # his own choice is kept


def test_her_own_work_waits_for_tomorrow_once_todays_budget_is_used():
    """Deferrable work counts against the day's budget; essential jobs never count or wait for it."""
    clear = {"cpu": 10.0, "memory_free": 80.0, "battery": None, "online": True, "disk_free": 50.0}
    home = Homeostasis(SimpleNamespace(config=SimpleNamespace(get=lambda k, d=None: 1 if "budget" in k else d)),
                       read=lambda: clear)
    assert home.defer_reason("night_school") == ""
    home.spend("night_school", 61)
    home.spend("alarms", 10_000)
    assert home.defer_reason("night_school") == "today's time for my own work is used up"
    assert home.defer_reason("alarms") == ""
    assert home.report()["budget"] == {"minutes_a_day": 1.0, "used_today": 1.0}
