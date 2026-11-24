"""
tests.test_firewood
=====================

Firewood for the winter (core/firewood.py): cords read from his inventory (full cords, face cords and ricks at about a
third), against his own winter figure (set with set_preparedness), what's short said; without his figure the usual
range said as only that and his number asked for; a pile with no measure named, never guessed.
"""

from types import SimpleNamespace

from core import firewood as fw


def _item(name, quantity=0):
    """An inventory record."""
    return SimpleNamespace(name=name, quantity=quantity, unit="")


def test_cords_face_cords_and_ricks_are_counted():
    have, unread = fw.cords_on_hand([_item("Firewood (cords)", 3), _item("Face cord oak", 3), _item("Firewood 2 cords"),
                                     _item("Wood pile by the barn", 1), _item("Wood screws", 200), _item("Oak dining table", 1)])
    assert have == 6.0 and unread == ["Wood pile by the barn"]


def test_his_winter_figure_says_whats_short_and_none_asks_for_it(monkeypatch):
    from core import person_settings

    kept = {"prepared.firewood_cords": 5}
    monkeypatch.setattr(person_settings, "get", lambda context, key, default=None: kept.get(key, default))
    ctx = SimpleNamespace(inventory=SimpleNamespace(all_items=lambda: [_item("Firewood (cords)", 3)]))
    assert "you're 2 short" in fw.say(ctx)
    kept.clear()
    assert "How many cords does a winter take you?" in fw.say(ctx)
