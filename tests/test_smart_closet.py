"""Smart Closet (DEC-0162): pieces and outfits, ratings, the day's suggestion
worked out in code (weather, occasion, rest, colour), insights, the actions
with undo, the page and the voice tools."""

from datetime import date, timedelta

import pytest

from tests.test_crafting import do, shop  # noqa: F401  (the fixture)

TODAY = date(2026, 11, 16)  # a Monday


@pytest.fixture
def closet(shop):  # noqa: F811
    """The test household with a closet in the person's folder."""
    from core.smart_closet import ClosetBook

    shop.closet = ClosetBook(shop, data_dir=shop.my_dir)
    return shop


def _stock(book):
    """A small wardrobe: two tops, jeans, shorts, a dress, boots, sandals, a rain jacket, a sweater."""
    add = book.add_piece
    return {
        "tee": add("White tee", category="top", color="white", warmth="light"),
        "flannel": add("Red flannel", category="top", color="red", warmth="warm", occasions="everyday, work"),
        "jeans": add("Jeans", category="bottom", color="denim", warmth="medium", occasions="everyday, work"),
        "shorts": add("Shorts", category="bottom", color="khaki", warmth="light"),
        "boots": add("Work boots", category="shoes", color="brown", occasions="everyday, work, outdoors"),
        "sandals": add("Sandals", category="shoes", color="tan", warmth="light"),
        "rain": add("Rain shell", category="outerwear", color="navy", waterproof="yes"),
        "sweater": add("Grey sweater", category="layer", color="grey", warmth="warm"),
    }


def test_a_cold_wet_work_day_gets_warm_clothes_and_the_rain_shell(closet):
    from core.smart_closet import suggest

    book = closet.closet
    s = _stock(book)
    plan = suggest(book.pieces, book.outfits, {"temp": 38, "high": 41, "unit": "°F", "words": "Light rain"}, "work", TODAY)
    assert plan["wet"] and plan["outerwear"] and plan["picks"]
    best = set(plan["picks"][0]["piece_ids"])
    assert s["rain"].piece_id in best and s["flannel"].piece_id in best and s["jeans"].piece_id in best
    assert s["shorts"].piece_id not in best and s["tee"].piece_id not in best


def test_a_hot_day_gets_light_pieces_and_no_jacket(closet):
    from core.smart_closet import suggest

    book = closet.closet
    s = _stock(book)
    plan = suggest(book.pieces, book.outfits, {"temp": 88, "high": 92, "unit": "°F", "words": "Sunny"}, "everyday", TODAY)
    best = set(plan["picks"][0]["piece_ids"])
    assert {s["tee"].piece_id, s["shorts"].piece_id} <= best
    assert s["rain"].piece_id not in best and not plan["outerwear"]


def test_without_weather_it_says_so_and_still_dresses_the_day(closet):
    from core.web_closet import closet_page, suggestion_sentence

    _stock(closet.closet)
    page = closet_page(closet, TODAY)
    assert page["suggestion"]["weather_known"] is False and page["suggestion"]["picks"]
    assert "don't have today's weather" in suggestion_sentence(page)


def test_a_piece_worn_yesterday_rests_and_one_in_the_wash_is_left_out(closet):
    from core.smart_closet import suggest

    book = closet.closet
    s = _stock(book)
    book.wear([s["jeans"].piece_id], (TODAY - timedelta(days=1)).isoformat())
    book.laundry([s["shorts"].piece_id], in_wash=True)
    plan = suggest(book.pieces, book.outfits, {"temp": 70, "high": 72, "unit": "°F", "words": "Clear"}, "everyday", TODAY)
    for pick in plan["picks"]:
        assert s["shorts"].piece_id not in pick["piece_ids"]
    assert book.laundry() == 1 and not book.get_piece(s["shorts"].piece_id).in_wash  # laundry's done: all clean


def test_a_low_rated_outfit_isnt_suggested_and_a_loved_one_comes_first(closet):
    from core.smart_closet import suggest

    book = closet.closet
    s = _stock(book)
    meh = book.add_outfit("Meh", [s["tee"].piece_id, s["shorts"].piece_id, s["sandals"].piece_id])
    book.rate_outfit(meh.outfit_id, 1, "too much")
    loved = book.add_outfit("Weekend", [s["flannel"].piece_id, s["jeans"].piece_id, s["boots"].piece_id])
    book.rate_outfit(loved.outfit_id, 5)
    plan = suggest(book.pieces, book.outfits, {"temp": 48, "high": 50, "unit": "°F", "words": "Cloudy"}, "everyday", TODAY)
    ids = [p["outfit_id"] for p in plan["picks"]]
    assert meh.outfit_id not in ids and ids[0] == loved.outfit_id
    assert "you rated it 5 stars" in plan["picks"][0]["why"]


def test_the_day_occasion_comes_from_the_calendar_and_the_loop(closet):
    from core.smart_closet import occasion_for

    assert occasion_for(["Gym with Sam"], work_day=True) == "gym"
    assert occasion_for(["Anniversary dinner"], work_day=False) == "date"
    assert occasion_for([], work_day=True) == "work"
    assert occasion_for([], work_day=False) == "everyday"


def test_insights_find_the_unworn_the_most_worn_and_the_gaps(closet):
    from core.smart_closet import insights

    book = closet.closet
    old = book.add_piece("Old blazer", category="layer", color="black")
    book.update_piece(old.piece_id, last_worn=(TODAY - timedelta(days=400)).isoformat())
    tee = book.add_piece("Fave tee", category="top")
    for i in range(3):
        book.wear([tee.piece_id], (TODAY - timedelta(days=i + 2)).isoformat())
    got = insights(book.pieces, book.outfits, TODAY)
    assert got["unworn"][0]["name"] == "Old blazer" and got["most_worn"][0] == {"piece_id": tee.piece_id, "name": "Fave tee", "times": 3}
    assert {"shoes", "a jacket or coat", "gym clothes"} <= set(got["gaps"])


def test_the_actions_add_save_wear_rate_and_undo(closet):
    from core.actions import ACTION_TYPES, ActionError

    w = closet
    do(w, "closet_piece.add", name="Navy hoodie", category="top", color="navy", warmth="medium")
    do(w, "closet_piece.add", name="Black jeans", category="bottom", color="black")
    book = w.closet
    assert len(book.pieces) == 2
    p = do(w, "closet.outfit", pieces="navy hoodie, black jeans", name="")
    outfit = book.outfits[0]
    assert outfit.name == "Navy hoodie + Black jeans" and p.status == "executed"
    do(w, "closet.wore", outfit_id=outfit.outfit_id)
    assert book.get_piece(outfit.piece_ids[0]).times_worn == 1 and outfit.times_worn == 1
    do(w, "closet.rate", outfit_id=outfit.outfit_id, stars=4, note="comfy")
    assert outfit.stars == 4
    with pytest.raises(ActionError):
        ACTION_TYPES["closet.rate"].describe(w, {"outfit_id": outfit.outfit_id, "stars": 9})
    with pytest.raises(ActionError):
        ACTION_TYPES["closet.outfit"].describe(w, {"pieces": "navy hoodie"})  # one piece isn't an outfit
    last = do(w, "closet_piece.delete", piece_id=book.find_piece("navy hoodie").piece_id)
    assert len(book.pieces) == 1 and not book.outfits  # the outfit went with its last pair
    w.actions.undo(w, last.proposal_id)
    assert len(book.pieces) == 2 and len(book.outfits) == 1


def test_a_bad_value_is_refused_in_plain_words(closet):
    book = closet.closet
    with pytest.raises(ValueError, match="category"):
        book.add_piece("Hat", category="headwear")
    with pytest.raises(ValueError, match="Occasions"):
        book.add_piece("Hat", category="accessory", occasions="party")


def test_the_page_and_the_voice_tools_agree(closet):
    from core.assistant_actions import AssistantActionRegistry
    from core.assistant_closet_actions import register_closet_actions
    from core.web_closet import closet_page

    reg = AssistantActionRegistry()
    register_closet_actions(reg)
    assert "closet is empty" in reg.execute(closet, "what_to_wear", {})
    _stock(closet.closet)
    page = closet_page(closet, TODAY)
    assert page["available"] and page["count"] == 8 and [g["category"] for g in page["groups"]][0] == "top"
    assert page["form"]["noun"] == "piece"
    said = reg.execute(closet, "what_to_wear", {})
    assert said.startswith("I don't have today's weather") and "Try " in said
    assert "8 pieces" in reg.execute(closet, "closet_report", {})
    assert [a.name for a in reg.matching_actions("what should I wear today?")][:1] == ["what_to_wear"]


def test_the_closet_is_sealed_and_kept_per_person():
    from core.at_rest import SEALED
    from core.personal_data import PERSONAL_STORES

    assert "smart_closet.json" in SEALED
    assert ("closet", __import__("core.smart_closet", fromlist=["ClosetBook"]).ClosetBook) in PERSONAL_STORES


def test_a_saved_outfit_that_doesnt_suit_the_day_isnt_offered_after_a_better_one(closet):
    from core.smart_closet import suggest

    book = closet.closet
    s = _stock(book)
    summer = book.add_outfit("Summer", [s["tee"].piece_id, s["shorts"].piece_id, s["sandals"].piece_id])
    book.rate_outfit(summer.outfit_id, 5)
    plan = suggest(book.pieces, book.outfits, {"temp": 30, "high": 34, "unit": "°F", "words": "Snow"}, "everyday", TODAY)
    assert plan["picks"] and summer.outfit_id not in [p["outfit_id"] for p in plan["picks"]]
