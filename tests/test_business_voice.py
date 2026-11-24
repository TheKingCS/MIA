"""
tests.test_business_voice
===========================

His business by voice (core/assistant_business_voice_actions.py, DEC-0125): the quotes still out, the open orders, a
customer's details, adding a customer, making a quote for a customer he has, a quote accepted (it becomes an order,
due when he says), an order marked delivered; each change through the Business page's own action, with "undo that".
A record is found by its exact title or customer name first; dates like "December 5" are read; the read-only tools
count as lookups by their observe tier (but a web search or a page read keeps a change's path, and a new tool's tier
is judged by its name); a record's name matches only as whole words, a plural allowed; a question naming another
app's record is never answered without the model (past the lookup's own words: "how many eggs this week?" stays the
egg count though eggs are in the pantry); a lookup is named when the message starts with its phrase, never for a
statement with a number ("egg count is 12 today"); and none of it is a child's.
"""

from datetime import date, timedelta

import pytest

from core import assistant_business_voice_actions as bv
from tests.test_business import shop  # noqa: F401  (the fixture: the crafting world with a business book)


@pytest.fixture
def biz(shop):  # noqa: F811
    """The crafting world with one customer and nothing quoted yet."""
    shop.business.add_customer("Dana Reyes", phone="555-0100", email="dana@example.com")
    return shop


def test_a_customer_is_added_and_read_back(biz):
    assert "Sam Ortiz" in bv._action_add_customer(biz, {"name": "Sam Ortiz", "phone": "555-0199"})
    assert bv._action_customer_details(biz, {"customer": "sam"}) == "Sam Ortiz: phone 555-0199."
    assert bv._action_add_customer(biz, {}) == "What's the customer's name?"


def test_a_quote_is_made_listed_accepted_and_delivered(biz):
    said = bv._action_make_quote(biz, {"title": "Cedar chest", "customer": "dana", "price": 900})
    assert "Cedar chest" in said
    assert bv._action_list_quotes(biz, {}).startswith("1 quote out: Cedar chest for Dana Reyes,")
    due = (date.today() + timedelta(days=3)).isoformat()
    assert "is an order now" in bv._action_accept_quote(biz, {"quote": "cedar", "due": due})
    assert bv._action_list_quotes(biz, {}) == "No quotes are out right now."
    assert "Cedar chest for Dana Reyes" in bv._action_list_orders(biz, {})
    bv._action_order_status(biz, {"order": "dana", "status": "delivered"})
    assert bv._action_list_orders(biz, {}) == "No open orders right now."


def test_a_customer_he_doesnt_have_is_said_not_made_up(biz):
    said = bv._action_make_quote(biz, {"title": "Bench", "customer": "Pat"})
    assert "I don't see a customer called pat" in said and not biz.business.quotes


def test_an_exact_title_wins_and_the_and_s_are_dropped(biz):
    bv._action_make_quote(biz, {"title": "Bench", "customer": "dana"})
    bv._action_make_quote(biz, {"title": "Bench Seat"})
    assert "is an order now" in bv._action_accept_quote(biz, {"quote": "the bench"})
    assert bv._action_customer_details(biz, {"customer": "dana's"}).startswith("Dana Reyes: phone 555-0100")


def test_a_month_and_day_is_a_due_day_and_ready_for_pickup_is_ready():
    today = date(2026, 11, 24)
    assert bv.due_day("December 5", today) == "2026-12-05" and bv.due_day("12/5", today) == "2026-12-05"
    assert bv.due_day("jan 3rd", today) == "2027-01-03" and bv.due_day("someday", today) is None


def test_the_read_only_tools_count_as_lookups_by_their_tier():
    from core.main_thread import changes_records

    for name in ("get_customer_details", "list_quotes", "who_owes_me", "emergency_kit", "canning_shelf"):
        assert not changes_records(name), name
    for name in ("make_quote", "order_status", "put_up_jars"):
        assert changes_records(name), name


def test_a_records_name_matches_only_as_whole_words():
    from core.assistant_actions import _whole

    assert _whole("sign", "the sign for the shop is done") and not _whole("sign", "i need to redesign my website")
    assert not _whole("ann", "my annual checkup is soon")


def test_business_is_never_a_childs():
    from core.child_accounts import CHILD_BLOCKED_DOMAINS

    assert "business" in CHILD_BLOCKED_DOMAINS


def test_what_reaches_outside_mia_keeps_a_changes_path_and_a_new_tools_tier_is_by_its_name():
    from core.grants import OBSERVE, default_tool_tier
    from core.main_thread import changes_records

    assert changes_records("look_up_online") and changes_records("browser_read")
    assert default_tool_tier("who_owes_me") != OBSERVE  # judged by its name, never by the tier it would confirm


def test_a_plural_of_a_records_name_still_matches():
    from core.assistant_actions import _whole

    assert _whole("atv", "the atvs need oil") and _whole("cow", "the cows got out")
    assert not _whole("ann", "my annual checkup")


def test_a_direct_lookup_never_takes_a_question_naming_another_apps_record():
    from tests.assistant_registry import build_desktop_registry, demo_context

    registry = build_desktop_registry()
    assert registry.direct_lookup("what's running on the pickup truck?", demo_context()) is None


def test_a_lookup_is_named_when_the_message_starts_with_its_phrase():
    from tests.assistant_registry import build_desktop_registry

    registry = build_desktop_registry()
    assert registry.named_action("wrap up my day", ["evening_wrap", "get_today"]) == "evening_wrap"


def test_the_egg_count_stays_a_direct_lookup_though_eggs_are_in_the_pantry():
    from types import SimpleNamespace

    from tests.assistant_registry import build_desktop_registry, demo_context

    registry = build_desktop_registry()
    context = demo_context()
    context.kitchen = SimpleNamespace(all_pantry_items=lambda: [SimpleNamespace(name="Eggs")],
                                      all_grocery_items=lambda: [], all_recipes=lambda: [])
    found = registry.direct_lookup("How many eggs this week?", context)
    assert found is not None and found.name == "get_eggs"


def test_a_statement_with_a_number_never_names_a_lookup():
    from tests.assistant_registry import build_desktop_registry

    registry = build_desktop_registry()
    assert registry.named_action("egg count is 12 today", ["get_eggs", "log_eggs"]) is None
