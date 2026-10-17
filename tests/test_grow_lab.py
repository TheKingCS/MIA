"""The grow lab (DEC-0030 phase D): batches, harvests and losses, readings
against the person's own ranges (only ever a warning), experiments that
compare batches, all undoable."""

from datetime import date

import pytest

from core.actions import ActionCenter, ActionError
from core.data_logger_manager import DataLoggerManager
from core.grow_lab import Batch, GrowLab, batch_figures, check_range, series_id
from tests.engine_world import build_world


def test_pure_logic():
    assert series_id("Tank  A", "ph") == "grow:tank a:ph"
    assert (check_range(7.6, 6.8, 7.2), check_range(6.5, 6.8, None), check_range(7.0, 6.8, 7.2)) == ("high", "low", "")
    b = Batch(batch_id="b", crop="Lettuce", planted="2026-09-01", count=10, lost=2,
              harvests=[{"date": "2026-10-06", "amount": 2.5, "unit": "lb"}, {"date": "2026-10-13", "amount": 1.5, "unit": "lb"}])
    f = batch_figures(b, date(2026, 10, 17))
    assert (f["days_growing"], f["days_to_harvest"], f["main_yield"], f["per_plant"], f["survival"]) == (46, 35, 4.0, 0.5, 80)


@pytest.fixture
def lab(tmp_path, monkeypatch):
    w = build_world(tmp_path, monkeypatch)
    w.grow_lab = GrowLab(w, data_dir=w.home_dir)
    w.data_logger = DataLoggerManager(w, data_dir=w.home_dir)
    w.actions = ActionCenter()
    return w


def do(w, kind, **params):
    p = w.actions.propose(w, kind, params)
    w.actions.approve(w, p.proposal_id)
    return p


def test_growing_measuring_and_comparing(lab):
    from core.web_grow import grow_page

    w = lab
    tank = w.maintenance.add_asset("Tank A", category="Garden/Plant").asset_id  # each tank is a Greenhouse asset (Zac)
    do(w, "batch.add", crop="Lettuce", variety="Butterhead", asset_id=tank, method="aquaponics", count=12, cost=4)
    do(w, "batch.add", crop="Lettuce", variety="Romaine", asset_id=tank, count=12)
    butter, romaine = w.grow_lab.batches
    assert butter.planted == date.today().isoformat() and butter.asset_id == tank and w.grow_lab.systems == []
    p = do(w, "grow.reading", place=tank, measure="ph", value=7.6)
    assert p.summary == "Tank A: pH 7.6 (that's high: your range is 6.8 to 7.2)"  # the starter range, until they set theirs
    do(w, "grow.range", place=tank, measure="ph", low=6.5, high=7.8)
    assert w.actions.propose(w, "grow.reading", {"place": tank, "measure": "ph", "value": 7.6}).summary == "Tank A: pH 7.6"
    with pytest.raises(ActionError):
        w.actions.propose(w, "grow.range", {"place": tank, "measure": "ph", "low": 8, "high": 7})
    with pytest.raises(ActionError):
        w.actions.propose(w, "grow.reading", {"place": "no-such-tank", "measure": "ph", "value": 7})

    do(w, "batch.harvest", batch_id=butter.batch_id, amount=3, unit="heads")
    do(w, "batch.lost", batch_id=romaine.batch_id, how_many=3, why="root rot")
    do(w, "experiment.add", question="Which lettuce does best in Tank A?")
    e = w.grow_lab.experiments[0]
    do(w, "experiment.include", experiment_id=e.experiment_id, batch_id=butter.batch_id)
    do(w, "experiment.include", experiment_id=e.experiment_id, batch_id=romaine.batch_id)
    do(w, "experiment.conclude", experiment_id=e.experiment_id, conclusion="Butterhead, by a mile")

    page = grow_page(w)
    here = page["places"][tank]  # everything about the tank, under the tank
    assert (here["name"], here["asset"], here["growing"]) == ("Tank A", True, 2)
    assert here["yield"] == [{"amount": 3.0, "unit": "heads"}] and len(here["batches"]) == 2
    ph = next(r for r in here["readings"] if r["measure"] == "ph")
    assert (ph["value"], ph["side"], ph["mine"]) == (7.6, "", True) and page["alerts"] == []
    exp = page["experiments"][0]
    assert exp["status"] == "Concluded" and [b["variety"] for b in exp["batches"]] == ["Butterhead", "Romaine"]
    assert exp["batches"][1]["figures"]["survival"] == 75
    assert page["harvests"] == [{"crop": "Lettuce", "unit": "heads", "amount": 3.0}]
    from core.chronicle import chronicle_page

    assert any("planted or harvested" in line for line in chronicle_page(w)["this_week"]["story"])


def test_alerts_and_undo(lab):
    from core.web_grow import grow_page

    w = lab
    do(w, "grow.reading", system="Tank B", measure="ammonia", value=2.0)  # a place typed by name still works
    alerts = [{k: v for k, v in a.items() if k != "when"} for a in grow_page(w)["alerts"]]
    assert alerts == [{"place": "Tank B", "system": "Tank B", "label": "Ammonia", "value": 2.0, "unit": "ppm", "side": "high",
                       "low": 0.0, "high": 1.0, "mine": False}]
    p = do(w, "batch.add", crop="Basil")
    w.actions.undo(w, p.proposal_id)
    assert w.grow_lab.batches == []


def test_a_tank_typed_by_name_joins_its_asset(lab):
    from core.web_grow import grow_page

    w = lab
    do(w, "grow.reading", system="Tank C", measure="ph", value=7.0)  # before Tank C was an asset
    do(w, "batch.add", crop="Kale", asset_id="Tank C")  # a typed name stays a typed place
    tank = w.maintenance.add_asset("Tank C", category="Garden/Plant").asset_id
    here = grow_page(w)["places"][tank]
    assert here["growing"] == 1 and next(r for r in here["readings"] if r["measure"] == "ph")["value"] == 7.0
    assert "Tank C" not in grow_page(w)["places"]  # one place, not two


def test_an_out_of_range_reading_becomes_one_note(lab):
    from core.grow_lab import alert_note
    from core.web_grow import grow_page

    w = lab
    tank = w.maintenance.add_asset("Tank A", category="Garden/Plant").asset_id
    do(w, "grow.reading", place=tank, measure="ammonia", value=2.0)
    [alert] = grow_page(w)["alerts"]
    title, message, fingerprint = alert_note(alert)
    assert title == "🌱 Tank A: Ammonia is high"
    assert message == "Tank A: Ammonia read 2 ppm, outside the starter range (set your own in the Greenhouse) of 0.0 to 1.0."
    assert alert_note(grow_page(w)["alerts"][0])[2] == fingerprint  # the same reading is the same note
    from core.communication_gate import Candidate

    a, b = (Candidate(topic="grow_alert", title=title, message=message, fingerprint=fingerprint) for _ in range(2))
    assert a.key() == b.key()  # the gate drops the repeat
