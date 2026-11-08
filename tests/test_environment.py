"""
tests.test_environment
========================

The real-vs-fictional boundary (core/environment.py + life_events, DEC-0137): `require_real` guards a real-authority
sink (fictional/simulated raises DomainLeak); unknown/None normalises to real so nothing is fiction by accident; and a
life event carries its environment, so a real-life view can filter to `real` and never see a campaign's events.
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
