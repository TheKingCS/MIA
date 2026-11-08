"""
tests.test_environment
========================

The real-vs-fictional boundary (core/environment.py + life_events, DEC-0137): `require_real` guards a real-authority
sink (fictional/simulated raises DomainLeak); unknown/None normalises to real so nothing is fiction by accident; and a
life event carries its environment, so a real-life view can filter to `real` and never see a campaign's events;
the leaderboard never counts a story's win; and no module reads the history directly without checking.
"""

import json

import pytest

from core import environment as env
from core.environment import DomainLeak, require_real


def test_require_real_passes_real_and_rejects_fiction_and_simulation():
    require_real("real")  # no raise
    require_real(None)  # None is treated as real, never fiction by accident
    for bad in ("fictional", "simulated"):
        with pytest.raises(DomainLeak):
            require_real(bad, what="a reward")


def test_normalize_defaults_unknown_to_real():
    assert env.normalize("fictional") == "fictional" and env.normalize("simulated") == "simulated"
    assert env.normalize(None) == "real" and env.normalize("nonsense") == "real"
    assert env.is_real("real") and not env.is_real("fictional")


def test_a_life_event_carries_its_environment_and_a_real_view_excludes_fiction(tmp_path):
    from core import life_events
    from core.life_events import LifeEventLog

    log = LifeEventLog(data_dir=tmp_path)
    life_events.record(log, "bill_paid", "Paid the water bill")  # real by default
    life_events.record(log, "quest_completed", "Slew the dragon", environment="fictional")

    lines = [json.loads(x) for x in (tmp_path / "life_events.jsonl").read_text(encoding="utf-8").splitlines() if x]
    envs = {e["summary"]: e.get("environment") for e in lines}
    assert envs["Paid the water bill"] == "real" and envs["Slew the dragon"] == "fictional"
    # a real-life timeline keeps to environment == "real" and never shows the campaign event
    real_only = [e for e in lines if e.get("environment") == "real"]
    assert [e["summary"] for e in real_only] == ["Paid the water bill"]


def test_events_for_keeps_the_real_life_history_to_real_events(tmp_path):
    """The real dashboard (events_for) defaults to real-only, so a campaign's events never surface there; None asks
    for every domain (DEC-0137)."""
    from types import SimpleNamespace

    from core import life_events
    from core.life_events import LifeEventLog

    log = LifeEventLog(data_dir=tmp_path)
    life_events.record(log, "bill_paid", "Paid the water bill")
    life_events.record(log, "quest_completed", "Slew the dragon", environment="fictional")
    ctx = SimpleNamespace(life_events=log, personal_life_events=None, budget=None, config=None)
    assert [e.summary for e in life_events.events_for(ctx)] == ["Paid the water bill"]
    assert {e.summary for e in life_events.events_for(ctx, environment=None)} == {"Paid the water bill", "Slew the dragon"}


def test_a_win_in_a_story_never_counts_as_a_real_win(tmp_path):
    """The household's leaderboard (core/party.py) reads the history directly; a fictional or simulated event of a win's
    type still isn't counted (DEC-0137)."""
    from datetime import date
    from types import SimpleNamespace

    from core import life_events
    from core.life_events import LifeEventLog
    from core.party import _wins

    log = LifeEventLog(data_dir=tmp_path)
    with life_events.acting("test", "p1"):
        life_events.record(log, "mission_completed", "Cleared the gutters")
        life_events.record(log, "mission_completed", "Slew the dragon", environment="fictional")
        life_events.record(log, "mission_completed", "What if I built a barn", environment="simulated")
    today = date.today()
    counted = _wins(SimpleNamespace(life_events=log), [SimpleNamespace(profile_id="p1")], today, today)
    assert counted == {"p1": 1}


def test_every_real_life_view_reads_the_history_through_events_for():
    """events_for is the one reader that keeps real-life views to real events; a module reading a LifeEventLog
    directly must check the environment itself (party.py does). This catches a new direct reader that doesn't."""
    import re
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent / "core"
    direct = []
    for path in root.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        if path.name == "life_events.py" or "LifeEventLog(" not in text:
            continue
        if re.search(r"\b(?!calendar\b|store\b)\w+\.all_events\(\)", text) and "is_real(" not in text:
            direct.append(path.name)
    assert direct == []
