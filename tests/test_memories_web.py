"""Memories' web screen (core/memories_web.py): a recap per expedition, and on this day."""

from types import SimpleNamespace

from core.memories_web import screen
from core.memory_manager import ActivityStats, ExpeditionRecap


def test_recaps_and_on_this_day():
    e = SimpleNamespace(expedition_id="e1", name="Elk Creek", location="the high country", start_date="2025-11-06",
                        end_date="2025-11-08")
    recap = ExpeditionRecap(expedition=e, duration_days=3,
                            activity_breakdown={"hike": ActivityStats("hike", 2, 18.44, 6.0)},
                            waypoint_categories_visited={"Water": 2, "Camp": 3},
                            journal_highlights=[SimpleNamespace(title="Saw a moose")],
                            photo_filenames=[("t1", "a.jpg"), ("t1", "b.jpg")])
    book = SimpleNamespace(all_recaps=lambda: [recap], on_this_day=lambda today=None: [recap])
    data = screen(SimpleNamespace(memories=book))
    shown = data["recaps"][0]
    assert (shown["km"], shown["photos"], shown["days"]) == (18.4, 2, 3)
    assert shown["activities"] == [{"kind": "hike", "trips": 2, "km": 18.4, "kmh": 3.1}]
    assert [p["kind"] for p in shown["places"]] == ["Camp", "Water"] and shown["highlights"] == ["Saw a moose"]
    assert data["on_this_day"][0]["name"] == "Elk Creek"
    assert screen(SimpleNamespace(memories=None)) == {"recaps": [], "on_this_day": []}
