"""
tests.test_trip_packing
=========================

A trip's packing list from the last one (core/trip_packing.py, brainstorm round 17): a new trip names the last trip
of the same kind with a list, and "copy the packing list" puts its items on, unpacked, never twice.
"""

from types import SimpleNamespace

from core import trip_packing


class _Trips:
    """Three trips: an old and a newer fishing trip with lists, and a hike."""

    def __init__(self):
        g = lambda *labels: [SimpleNamespace(label=l, item_id=None, packed=True) for l in labels]  # noqa: E731
        self.trips = [
            SimpleNamespace(trip_id="a", name="Spring creek", activity_type="Fishing", start_date="2026-04-01",
                            created_at="2026-03-01", gear=g("Rod"), status="completed"),
            SimpleNamespace(trip_id="b", name="Lake day", activity_type="Fishing", start_date="2026-09-01",
                            created_at="2026-08-01", gear=g("Rod", "Tackle box", "Waders"), status="completed"),
            SimpleNamespace(trip_id="c", name="Ridge hike", activity_type="Hiking", start_date="2026-10-01",
                            created_at="2026-09-01", gear=g("Boots"), status="completed"),
            SimpleNamespace(trip_id="d", name="Fall creek", activity_type="Fishing", start_date="2026-12-01",
                            created_at="2026-11-25", gear=[SimpleNamespace(label="Rod", item_id=None, packed=False)],
                            status="planned")]

    def all_trips(self):
        """Every trip."""
        return self.trips

    def add_gear_item(self, trip_id, label, item_id=None):
        """Adds an unpacked item to a trip."""
        next(t for t in self.trips if t.trip_id == trip_id).gear.append(SimpleNamespace(label=label, item_id=item_id,
                                                                                         packed=False))


def test_a_new_trip_names_the_last_like_one_and_copies_it_on_his_word():
    context = SimpleNamespace(trips=_Trips())
    new = context.trips.trips[3]
    assert trip_packing.last_like(context, new).name == "Lake day"
    assert "Your last fishing trip, Lake day, packed: Rod, Tackle box, Waders. Say \"copy the packing list to Fall " \
        "creek\"" in trip_packing.offer_line(context, new)
    said = trip_packing._copy_tool(context, {})
    assert said == "Copied 2 items from Lake day to Fall creek: Tackle box, Waders."
    assert [g.label for g in new.gear] == ["Rod", "Tackle box", "Waders"]
    assert trip_packing._copy_tool(context, {}) == "Fall creek already has everything from Lake day's packing list."


def test_a_finished_trip_named_alone_is_copied_from_never_onto():
    context = SimpleNamespace(trips=_Trips())
    said = trip_packing._copy_tool(context, {"trip_name": "Spring creek"})
    assert said == "Copied 1 item from Spring creek to Fall creek: Rod." or "already has everything" in said
    assert [g.label for g in context.trips.trips[0].gear] == ["Rod"], "the finished trip is left as it was"
    assert "Copied 2 items from Lake day" in trip_packing._copy_tool(context, {"trip_name": "Lake day"})


def test_no_earlier_trip_of_that_kind_says_so():
    context = SimpleNamespace(trips=_Trips())
    context.trips.trips = [t for t in context.trips.trips if t.activity_type != "Fishing" or t.trip_id == "d"]
    assert trip_packing.offer_line(context, context.trips.trips[-1]) == ""
    assert trip_packing._copy_tool(context, {}).startswith("There's no earlier fishing trip")
