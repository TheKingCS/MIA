"""
tests.test_web_surfaces_life
==============================

The Dashboard's life cards (DEC-0129, core/web_surfaces.life_cards): which trip it shows and how its dates read, and
each card from its own source, a missing source leaving its card out.
"""

from datetime import date
from types import SimpleNamespace as NS

from core.web_surfaces import life_cards, pick_trip, span_text

TODAY = date(2026, 11, 8)


def trip(i, status, start, end=""):
    """A stand-in trip."""
    return NS(trip_id=i, name=f"Trip {i}", status=status, start_date=start, end_date=end)


def test_a_trip_under_way_beats_the_next_one_which_beats_one_just_finished():
    planned, done = trip("p", "planned", "2026-11-14", "2026-11-16"), trip("d", "completed", "2026-11-01", "2026-11-03")
    assert pick_trip([done, planned, trip("a", "active", "2026-11-07")], TODAY)["words"] == "Under way"
    shown = pick_trip([done, planned], TODAY)
    assert (shown["id"], shown["words"], shown["when"]) == ("p", "In 6 days", "Nov 14 – 16")
    assert pick_trip([done], TODAY)["words"] == "Just back"
    assert pick_trip([trip("o", "completed", "2026-09-01")], TODAY) is None


def test_trip_dates_in_words():
    assert span_text("2026-11-30", "2026-12-02") == "Nov 30 – Dec 2"
    assert span_text("2026-11-14", "") == "Nov 14"
    assert span_text("", "") == ""


def test_each_card_comes_from_its_own_source_and_missing_ones_are_left_out():
    music = NS(now_playing=lambda: NS(title="Harvest Moon", artist="Neil Young", is_playing=True))
    vault = NS(items={"a": {"sha": "a", "kind": "photo", "on_pc": True, "taken_at": "2026-11-06T10:00"},
                      "b": {"sha": "b", "kind": "video", "on_pc": True, "taken_at": "2026-11-07T10:00"},
                      "c": {"sha": "c", "kind": "photo", "on_pc": False, "taken_at": "2026-11-07T11:00"}})
    cards = life_cards(NS(music=music, memory_vault=vault, trips=None), TODAY)
    assert cards["music"] == {"title": "Harvest Moon", "artist": "Neil Young", "playing": True}
    assert [p["sha"] for p in cards["pictures"]] == ["a"]
    assert cards["trip"] is None
    assert life_cards(NS(), TODAY)["pictures"] == []
