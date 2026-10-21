"""One system, not a collection of apps (DEC-0044): Presence ranks what
matters now across everything with why; the frame leads to five places;
World shows each app's status; the Path shows real wins only."""

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


def test_the_frame_leads_to_five_places_and_pins(life):
    from core.web_surfaces import shell

    s = shell(life)
    assert [d["name"] for d in s["destinations"]] == ["Presence", "Conversation", "My Hero's Path", "World", "System"]
    assert s["pinned"] == []
    do(life, "app.favorite", module_id="flock", favorite=True)
    assert [p["id"] for p in shell(life)["pinned"]] == ["flock"]


def test_world_shows_what_needs_you_per_app(life):
    from core.web_hubs import system_page, world_page

    life.obligations.add("Licence", kind="licence", due_date=(date.today() + timedelta(days=3)).isoformat())
    w = world_page(life)
    cards = {c["id"]: c for area in w["areas"] for c in area["cards"]}
    assert "web_home" not in cards and "assistant" not in cards
    assert cards["compliance"]["needs"] == 2 and cards["compliance"]["line"] == "2 things need you: Licence"
    s = system_page(life)
    assert s["capabilities"]["apps"] > 30 and any(x["href"] == "settings.html" for x in s["screens"])


def test_the_path_shows_wins_not_spending(life):
    from core.web_hubs import path_page

    life.budget.add_expense(amount=40, category="Groceries", description="Milk", date=date.today().isoformat())
    p = path_page(life)
    assert all("Spent" not in (w.get("summary") or "") for w in p["wins"])
    assert any(s["href"] == "missions.html" for s in p["screens"])
