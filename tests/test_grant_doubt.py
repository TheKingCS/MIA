"""
tests.test_grant_doubt
========================

Learned, then asked (core/corrections._doubt, brainstorm round 17): his second correction within a week of a kind
she makes on her own offers, through the gate, to ask him first again; she never takes his yes back herself, and
"ask me first for grocery" finds that standing yes (core/grants.find).
"""

from datetime import datetime, timedelta
from types import SimpleNamespace

from core import corrections, grants, kind_grants

NOW = datetime(2026, 11, 26, 10)


def test_a_second_correction_of_a_granted_kind_offers_to_ask_first(monkeypatch, tmp_path):
    offered = []
    context = SimpleNamespace(communication=SimpleNamespace(offer=lambda c, now=None: offered.append(c)))
    monkeypatch.setattr(corrections, "_folder", lambda c: tmp_path)
    monkeypatch.setattr(kind_grants, "has", lambda c, kind, now=None: kind == "grocery.add")
    monkeypatch.setattr(kind_grants, "live", lambda c, now=None: {"grocery.add": {"given": "2026-11-20T00:00:00"}})
    for i in range(2):
        corrections.mia_changed(context, "grocery.add", {"item_id": f"g{i}"}, NOW - timedelta(minutes=30))
        assert corrections.person_changed(context, "grocery.delete", {"item_id": f"g{i}"}, NOW) is not None
    assert len(offered) == 1, "the first correction asks nothing"
    said = offered[0]
    assert said.topic == "grant_doubt" and 'Say "ask me first for grocery add"' in said.message
    assert said.fingerprint == "grant-doubt-grocery.add-2026-W48"


def test_a_kind_she_asks_about_anyway_never_offers(monkeypatch, tmp_path):
    offered = []
    context = SimpleNamespace(communication=SimpleNamespace(offer=lambda c, now=None: offered.append(c)))
    monkeypatch.setattr(corrections, "_folder", lambda c: tmp_path)
    monkeypatch.setattr(kind_grants, "has", lambda c, kind, now=None: False)
    monkeypatch.setattr(kind_grants, "live", lambda c, now=None: {})
    for i in range(3):
        corrections.mia_changed(context, "grocery.add", {"item_id": f"g{i}"}, NOW - timedelta(minutes=30))
        corrections.person_changed(context, "grocery.delete", {"item_id": f"g{i}"}, NOW)
    assert offered == []


def test_ask_me_first_for_grocery_finds_that_standing_yes(monkeypatch):
    listed = [grants.Grant("kind:grocery.add", "kind", "Add", "each time", "you pressed it"),
              grants.Grant("kind:grocery.check", "kind", "Check off", "each time", "you pressed it"),
              grants.Grant("kind:pantry.add", "kind", "Add", "each time", "you pressed it")]
    monkeypatch.setattr(grants, "standing", lambda c: listed)
    assert grants.find(None, "grocery add").grant_id == "kind:grocery.add"
    assert grants.find(None, "pantry").grant_id == "kind:pantry.add"
    assert grants.find(None, "grocery") is None, "two grocery yeses: which one?"
    assert grants.find(None, "add") is None, "two named Add: which one?"
    listed.append(grants.Grant("skill:s1", "skill", "Pantry restock", "steps", "learned"))
    assert grants.find(None, "pantry") is None, "a skill's name and a yes's kind both fit"


def test_undoing_her_change_twice_offers_too(monkeypatch, tmp_path):
    offered = []
    context = SimpleNamespace(communication=SimpleNamespace(offer=lambda c, now=None: offered.append(c)))
    monkeypatch.setattr(corrections, "_folder", lambda c: tmp_path)
    monkeypatch.setattr(kind_grants, "has", lambda c, kind, now=None: True)
    monkeypatch.setattr(kind_grants, "live", lambda c, now=None: {"grocery.add": {"given": "2026-11-20T00:00:00"}})
    for i in range(2):
        corrections.mia_changed(context, "grocery.add", {"item_id": f"g{i}"}, NOW - timedelta(minutes=30))
        assert corrections.undone(context, "action_grocery.add", NOW) is not None
    assert len(offered) == 1


def test_corrections_from_before_his_yes_dont_count(monkeypatch, tmp_path):
    offered = []
    context = SimpleNamespace(communication=SimpleNamespace(offer=lambda c, now=None: offered.append(c)))
    monkeypatch.setattr(corrections, "_folder", lambda c: tmp_path)
    monkeypatch.setattr(kind_grants, "has", lambda c, kind, now=None: True)
    monkeypatch.setattr(kind_grants, "live", lambda c, now=None: {"grocery.add": {"given": "2026-11-26T09:45:00"}})
    corrections.mia_changed(context, "grocery.add", {"item_id": "g0"}, NOW - timedelta(hours=2))
    corrections.person_changed(context, "grocery.delete", {"item_id": "g0"}, NOW - timedelta(hours=1))
    corrections.mia_changed(context, "grocery.add", {"item_id": "g1"}, NOW - timedelta(minutes=10))
    corrections.person_changed(context, "grocery.delete", {"item_id": "g1"}, NOW)
    assert offered == [], "the first came before he said yes from now on"
