"""
tests.test_trip_eve
=====================

"Before you go" (core/trip_eve.py, 2026-11-25): the afternoon before a planned trip, what isn't packed, tomorrow's
weather here and the checks for that kind of trip (telling someone where you're going first), once per trip through
the gate; "what do I need for my trip?" reaches it.
"""

from datetime import date, datetime
from types import SimpleNamespace

from core import assistant_turn, trip_eve

TODAY = date(2026, 11, 25)


def _trips(*trips):
    return SimpleNamespace(trips=SimpleNamespace(all_trips=lambda: list(trips)))


def _trip(name="Creek trip", start="2026-11-26", status="planned", activity="Fishing", gear=()):
    return SimpleNamespace(trip_id="t1", name=name, start_date=start, status=status, activity_type=activity,
                           gear=[SimpleNamespace(label=l, packed=p) for l, p in gear])


def test_tomorrows_trip_says_whats_not_packed_and_the_checks():
    context = _trips(_trip(gear=(("Rod", True), ("Tackle box", False), ("Waders", False))),
                     _trip(name="Later", start="2026-12-05"), _trip(name="Done", status="completed"))
    found = trip_eve.plan(context, TODAY)
    assert [f["name"] for f in found] == ["Creek trip"]
    said = trip_eve.words(found[0], "Tomorrow here: Clear, 50°F and 30°F.")
    assert said.startswith("Creek trip is tomorrow. Not packed yet: Tackle box, Waders. Tomorrow here: Clear")
    assert "Before you go: Tell someone where you're going and when you'll be back; your fishing license" in said


def test_it_is_offered_in_the_afternoon_once_per_trip(monkeypatch):
    monkeypatch.setattr(trip_eve, "_sky", lambda c: "")
    context = _trips(_trip(gear=(("Rod", True),)))
    assert trip_eve.offer(context, datetime(2026, 11, 25, 9)) == []
    said = trip_eve.offer(context, datetime(2026, 11, 25, 16))
    assert len(said) == 1 and said[0].topic == "trip_eve" and said[0].fingerprint == "trip-eve-t1"
    assert "Everything on its packing list is packed." in said[0].message
    assert said[0].expires.startswith("2026-11-26T12")


def test_no_trip_tomorrow_says_so():
    assert trip_eve.say(_trips(), TODAY).startswith("You don't have a trip starting tomorrow")


def test_the_words_reach_it(monkeypatch):
    monkeypatch.setattr(trip_eve, "say", lambda c, t=None: "the trip")
    for words in ("What do I need for my trip?", "am I ready for my trip tomorrow?", "what's left to pack",
                  "what do I need to bring on the trip"):
        assert assistant_turn._own_tool_reply(SimpleNamespace(), words) == "the trip", words
    assert assistant_turn._own_tool_reply(SimpleNamespace(), "what do I need for a trip to Japan") != "the trip"
