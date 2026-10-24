"""What matters now across every app, with why (core/presence.py): it
feeds every turn so MIA answers knowing the person's world. The
five-places frame it came with (DEC-0044) was undone by Zac, 2026-10-24;
the apps are the layout again."""

from datetime import date, timedelta

import pytest

from tests.test_crafting import do, shop  # noqa: F401  (the fixture)


@pytest.fixture
def life(shop):  # noqa: F811
    from core.business_book import BusinessBook
    from core.flock import FlockBook
    from core.obligations import ObligationBook

    w = shop
    w.business, w.flock = BusinessBook(w, data_dir=w.home_dir), FlockBook(w, data_dir=w.home_dir)
    w.obligations = ObligationBook(w, data_dir=w.home_dir)
    return w


def test_presence_ranks_across_apps_with_why(life):
    from core.presence import presence

    w, t = life, date.today()
    w.obligations.add("Sales tax return", kind="tax filing", due_date=(t - timedelta(days=1)).isoformat(),
                      status="applies", verified_on=t.isoformat())
    w.obligations.add("Licence renewal", kind="licence", due_date=(t + timedelta(days=5)).isoformat())
    do(w, "flock.add", name="Layers", hens=10)
    do(w, "flock.eggs", flock_id=w.flock.flocks[0].flock_id, count=13)
    p = presence(w, t)
    titles = [i["title"] for i in p["now"]]
    assert titles[0] == "Sales tax return" and p["next"]["title"] == "Sales tax return"
    assert "Licence renewal" in titles and "13 loose eggs from Layers" in titles
    licence = next(i for i in p["now"] if i["title"] == "Licence renewal")
    assert licence["kind"] == "deadline" and "Not verified yet" in licence["why"] and licence["href"] == "compliance.html"
    eggs = next(i for i in p["now"] if i["title"].endswith("Layers"))
    assert eggs["kind"] == "suggestion" and eggs["href"] == "flock.html"
    assert p["line"].startswith(f"{len(p['now'])} things need you; start with: Sales tax return")
    assert p["path"] == [] and any(i["title"] == "Set up your freedom plan" and i["kind"] == "suggestion" for i in p["now"])


def test_a_failing_source_never_empties_presence(life, monkeypatch):
    import core.presence as presence_module

    life.obligations.add("Licence", kind="licence", due_date=(date.today() + timedelta(days=3)).isoformat())
    monkeypatch.setattr(presence_module, "_flock", lambda c, t: 1 / 0)
    assert presence_module.presence(life)["now"][0]["title"] == "Licence"


def test_home_wins_are_wins_not_spending(life):
    from core.web_surfaces import dashboard

    life.budget.add_expense(amount=40, category="Groceries", description="Milk", date=date.today().isoformat())
    assert all("Spent" not in (w.get("summary") or "") for w in dashboard(life)["wins"])


def test_every_turn_knows_their_world(life):
    from core.assistant_chat import build_system_message
    from core.presence import context_lines

    w = life
    goal = w.intents.add_intent("Time back on the homestead")
    w.intents.set_primary(goal.intent_id)
    w.intents.update_intent(goal.intent_id, reason="So the days are mine")
    w.obligations.add("Licence renewal", kind="licence", due_date=(date.today() + timedelta(days=2)).isoformat())
    block = context_lines(w)
    assert "- Working toward: Time back on the homestead (why, in their words: So the days are mine)" in block
    assert "Licence renewal (Due in 2 days" in block
    assert block in build_system_message(w, is_action_request=False, prompt="What should I focus on?")
    assert block not in build_system_message(w, is_action_request=True, prompt="Add milk")  # the action path stays lean
