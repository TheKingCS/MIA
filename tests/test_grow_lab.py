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
    do(w, "batch.add", crop="Lettuce", variety="Butterhead", system="Tank A", method="aquaponics", count=12, cost=4)
    do(w, "batch.add", crop="Lettuce", variety="Romaine", system="Tank A", count=12)
    butter, romaine = w.grow_lab.batches
    assert butter.planted == date.today().isoformat() and w.grow_lab.systems == ["Tank A"]
    p = do(w, "grow.reading", system="Tank A", measure="ph", value=7.6)
    assert p.summary == "Tank A: pH 7.6 (that's high: your range is 6.8 to 7.2)"  # the starter range, until they set theirs
    do(w, "grow.range", system="Tank A", measure="ph", low=6.5, high=7.8)
    assert w.actions.propose(w, "grow.reading", {"system": "Tank A", "measure": "ph", "value": 7.6}).summary == "Tank A: pH 7.6"
    with pytest.raises(ActionError):
        w.actions.propose(w, "grow.range", {"system": "Tank A", "measure": "ph", "low": 8, "high": 7})

    do(w, "batch.harvest", batch_id=butter.batch_id, amount=3, unit="heads")
    do(w, "batch.lost", batch_id=romaine.batch_id, how_many=3, why="root rot")
    do(w, "experiment.add", question="Which lettuce does best in Tank A?")
    e = w.grow_lab.experiments[0]
    do(w, "experiment.include", experiment_id=e.experiment_id, batch_id=butter.batch_id)
    do(w, "experiment.include", experiment_id=e.experiment_id, batch_id=romaine.batch_id)
    do(w, "experiment.conclude", experiment_id=e.experiment_id, conclusion="Butterhead, by a mile")

    page = grow_page(w)
    tank = page["systems"][0]
    assert tank["name"] == "Tank A" and tank["growing"] == 2
    ph = next(r for r in tank["readings"] if r["measure"] == "ph")
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
    do(w, "grow.reading", system="Tank B", measure="ammonia", value=2.0)
    alerts = grow_page(w)["alerts"]
    assert alerts == [{"system": "Tank B", "label": "Ammonia", "value": 2.0, "unit": "ppm", "side": "high",
                       "low": 0.0, "high": 1.0, "mine": False}]
    p = do(w, "batch.add", crop="Basil")
    w.actions.undo(w, p.proposal_id)
    assert w.grow_lab.batches == []
