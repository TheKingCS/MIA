"""A heads-up before a warranty ends (core/warranty_watch.py)."""

from datetime import date, datetime
from types import SimpleNamespace

from core.warranty_watch import due_notices, warranty_message, warranty_stage

TODAY = date(2026, 9, 28)


def test_stages():
    assert warranty_stage("2026-12-01", TODAY) is None  # far off
    assert warranty_stage("2026-10-27", TODAY) == ("month", 29)
    assert warranty_stage("2026-10-03", TODAY) == ("week", 5)
    assert warranty_stage("2026-09-01", TODAY) is None  # already over
    assert warranty_stage("", TODAY) is None and warranty_stage("soon", TODAY) is None


def test_message():
    assert warranty_message("Riding Mower", "2026-10-27", 29) == (
        "The Riding Mower's warranty ends Oct 27 (in 29 days). If anything's been acting up, now's the time "
        "to get it looked at while it's covered.")
    assert "(tomorrow)" in warranty_message("Truck", "2026-09-29", 1)


def test_each_stage_is_said_once():
    mower = SimpleNamespace(asset_id="m", name="Riding Mower", warranty_until="2026-10-27")
    assert [(a.asset_id, s) for a, s, _ in due_notices([mower], TODAY, {})] == [("m", "month")]
    assert due_notices([mower], TODAY, {"m": "2026-10-27|month"}) == []
    assert [s for _, s, _ in due_notices([mower], date(2026, 10, 21), {"m": "2026-10-27|month"})] == ["week"]
    # A new warranty date (extended) starts over.
    mower.warranty_until = "2027-10-27"
    assert due_notices([mower], date(2027, 10, 1), {"m": "2026-10-27|month,2026-10-27|week"})


def test_the_daily_check(tmp_path, monkeypatch):
    import core.config_manager as config_module
    from core.application import MIAApplication
    from core.config_manager import ConfigManager

    monkeypatch.setattr(config_module, "_CONFIG_FILE", tmp_path / "config.json")
    offered = []
    mower = SimpleNamespace(asset_id="m", name="Riding Mower", warranty_until="2026-10-27")
    app = SimpleNamespace(context=SimpleNamespace(config=ConfigManager(), maintenance=SimpleNamespace(all_assets=lambda: [mower])),
                          _offer=lambda **kw: offered.append(kw))
    for _ in range(2):
        MIAApplication._check_warranties(app, datetime(2026, 9, 28, 9), "2026-09-28")
    assert len(offered) == 1 and offered[0]["topic"] == "warranty" and "Oct 27" in offered[0]["message"]
