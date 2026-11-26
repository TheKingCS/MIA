"""
tests.test_condition_watch
============================

"Tell me when..." (core/condition_watch.py, 2026-11-25): his words read in code into a watch on tonight's low,
tomorrow's rain, a pantry item, the feed or his supplies; checked each day and said once through the gate (every day
it's true when he said "whenever"); kept in his own folder, added and stopped by his words.
"""

from datetime import date, datetime
from types import SimpleNamespace

from core import condition_watch as cw

TODAY = date(2026, 11, 25)


def test_his_words_are_read_into_watches():
    assert cw.parse("tell me if it freezes tonight", TODAY) == {"kind": "freeze", "value": 32.0, "standing": False,
                                                                "until": "2026-11-25", "about": ""}
    assert cw.parse("let me know if it frosts", TODAY, celsius=True)["value"] == 0.0
    assert cw.parse("tell me when it gets below 20 degrees", TODAY)["value"] == 20.0
    assert cw.parse("warn me if it's going to rain tomorrow", TODAY)["kind"] == "rain"
    eggs = cw.parse("tell me when we're down to 2 dozen eggs", TODAY)
    assert (eggs["kind"], eggs["about"], eggs["value"]) == ("item", "eggs", 24.0)
    flour = cw.parse("tell me when the flour gets below 5", TODAY)
    assert (flour["kind"], flour["about"], flour["value"]) == ("item", "flour", 5.0)
    coffee = cw.parse("let me know when we're low on coffee", TODAY)
    assert (coffee["about"], coffee["value"]) == ("coffee", 1.0)
    assert cw.parse("tell me when the feed gets under 3 days", TODAY)["value"] == 3.0
    water = cw.parse("tell me when we're down to 3 days of water", TODAY)
    assert (water["kind"], water["about"], water["value"]) == ("supply", "water", 3.0)
    assert cw.parse("tell me whenever it freezes", TODAY)["standing"] is True
    assert cw.parse("tell me a joke", TODAY) is None
    assert cw.parse("tell me when we're out of gas", TODAY) == {"kind": "supply", "about": "fuel", "value": 0.0,
                                                                "standing": False, "until": "", "about": "fuel"}
    assert cw.parse("let me know when the chickens are out of feed", TODAY)["value"] == 0.0
    assert cw.parse("tell me if it gets below -5 degrees", TODAY)["value"] == -5.0
    assert cw.parse("tell me when we're down to a dozen eggs please", TODAY)["about"] == "eggs"


def test_what_isnt_a_watch_is_left_alone():
    for words in ("tell me when it stops raining", "let me know if the rain gauge breaks",
                  "tell me when the freezer is fixed", "tell me when the frosting is done",
                  "remind me if it rains tomorrow to bring in the laundry", "let me know if the dog food is low",
                  "remind me to water the plants in 3 days", "tell me when it gets under 20",
                  "tell me when the water bill is under 50 dollars", "let me know if you need anything"):
        assert cw.parse(words, TODAY) is None, words


def _pantry(*items):
    return SimpleNamespace(all_pantry_items=lambda: [SimpleNamespace(name=n, quantity=q, unit=u) for n, q, u in items])


def test_a_pantry_item_is_said_when_it_runs_low_then_done(tmp_path):
    context = SimpleNamespace(kitchen=_pantry(("Eggs", 10, "eggs"), ("Coffee beans", 3, "lb")))
    watches = cw.WatchList(context, data_dir=tmp_path)
    context.condition_watches = watches
    watches.add(cw.Watch("w1", "item", about="eggs", value=12.0, words="tell me when we're down to a dozen eggs"))
    said = cw.offer(context, datetime(2026, 11, 25, 9))
    assert len(said) == 1 and "Eggs is down to 10 eggs" in said[0].message and said[0].topic == "condition_watch"
    assert cw.offer(context, datetime(2026, 11, 26, 9)) == [], "a once-watch says itself once"
    assert cw.WatchList(context, data_dir=tmp_path).get("w1").told == "2026-11-25"


def test_a_pantry_watch_offers_the_grocery_list(monkeypatch):
    from core import actions as engine

    monkeypatch.setattr(engine, "_granted_ahead", lambda c, kind: False)
    proposed = []
    kitchen = SimpleNamespace(all_pantry_items=lambda: [SimpleNamespace(name="Coffee", quantity=1, unit="lb")],
                              all_grocery_items=lambda: [])
    actions = SimpleNamespace(propose=lambda c, kind, params, proposed_by="person":
                              proposed.append((kind, params, proposed_by)) or SimpleNamespace(status="proposed"))
    context = SimpleNamespace(kitchen=kitchen, actions=actions)
    watch = cw.Watch("w6", "item", about="coffee", value=1.0)
    assert cw.restock(context, watch) == ' Say "add coffee to my grocery list" and I will.'
    assert proposed == [], "no card no screen shows"
    monkeypatch.setattr(engine, "_granted_ahead", lambda c, kind: True)
    actions.propose = lambda c, kind, params, proposed_by="person": (proposed.append((kind, params, proposed_by))
                                                                     or SimpleNamespace(status="executed"))
    assert cw.restock(context, watch) == " I added Coffee to your grocery list (undo it if you don't want it)."
    assert proposed == [("grocery.add", {"name": "Coffee"}, "mia")]
    kitchen.all_grocery_items = lambda: [SimpleNamespace(name="coffee beans", checked=False)]
    assert cw.restock(context, watch) == " Coffee is already on your grocery list."
    assert len(proposed) == 1
    assert cw.restock(context, cw.Watch("w7", "freeze", value=32.0)) == ""


def test_a_dozen_in_the_pantry_counts_as_twelve(tmp_path):
    context = SimpleNamespace(kitchen=_pantry(("Eggs", 3, "dozen")))
    context.condition_watches = cw.WatchList(context, data_dir=tmp_path)
    watch = cw.Watch("w4", "item", about="eggs", value=24.0)
    assert cw.check(context, watch, TODAY) is None, "3 dozen is 36 eggs, over the 24 he said"


def test_a_standing_freeze_watch_says_each_night_it_freezes(monkeypatch, tmp_path):
    context = SimpleNamespace()
    watches = cw.WatchList(context, data_dir=tmp_path)
    context.condition_watches = watches
    watches.add(cw.Watch("w2", "freeze", value=32.0, standing=True))
    forecast = {"text": "Clear", "low": 40, "tomorrow": {"low": 28}, "unit": "°F"}
    from core import weather

    monkeypatch.setattr(weather, "card", lambda c, fetch=None: forecast)
    first = cw.offer(context, datetime(2026, 11, 25, 17))
    assert len(first) == 1 and "tonight's low is 28°F" in first[0].message and first[0].urgency == "timely"
    assert cw.offer(context, datetime(2026, 11, 25, 18)) == [], "once a day"
    assert first[0].expires.startswith("2026-11-26T09")
    assert len(cw.offer(context, datetime(2026, 11, 26, 17))) == 1


def test_a_watch_for_tonight_ends_after_tonight(tmp_path):
    watches = cw.WatchList(None, data_dir=tmp_path)
    watches.add(cw.Watch("w3", "freeze", value=32.0, until="2026-11-25"))
    assert [w.watch_id for w in watches.live(date(2026, 11, 25))] == ["w3"]
    assert watches.live(date(2026, 11, 26)) == []


def test_tomorrow_nights_freeze_waits_for_tomorrow(monkeypatch):
    from core import weather

    monkeypatch.setattr(weather, "card", lambda c, fetch=None: {"text": "x", "low": 40, "tomorrow": {"low": 20}})
    watch = cw.Watch("w5", "freeze", value=32.0, until="2026-11-26", created_at="2026-11-25T18:00:00")
    assert cw.check(None, watch, date(2026, 11, 25)) is None
    assert "20" in cw.check(None, watch, date(2026, 11, 26))
    assert cw.describe(watch) == "if tomorrow night's low gets down to 32°F (that night only)"


def test_his_whole_sentence_reaches_the_watch(monkeypatch):
    from core import assistant_turn, weather

    monkeypatch.setattr(weather, "unit_for", lambda c: "fahrenheit")
    ran = []
    actions = SimpleNamespace(execute=lambda c, name, args: ran.append((name, args)) or "kept")
    context = SimpleNamespace(assistant_actions=actions)
    for words in ("Let me know when we're low on coffee", "Tell me when the feed gets under 4 days",
                  "tell me if it freezes tonight"):
        assert assistant_turn._own_tool_reply(context, words) == "kept", words
        assert ran[-1] == ("watch_condition", {"question": words})
    assert assistant_turn._own_tool_reply(context, "What are you watching for me?") == "kept"
    assert ran[-1][0] == "list_watches"
    assert assistant_turn._own_tool_reply(context, "tell me a joke") is None
    assert assistant_turn._own_tool_reply(context, "let me know if you need anything") is None


def test_the_tools_keep_list_and_stop_watches(monkeypatch, tmp_path):
    from core import weather

    monkeypatch.setattr(weather, "unit_for", lambda c: "fahrenheit")
    context = SimpleNamespace(kitchen=_pantry(("Flour", 10, "lb")))
    context.condition_watches = cw.WatchList(context, data_dir=tmp_path)
    said = cw._watch_tool(context, {"question": "tell me when the flour gets below 5"})
    assert said.startswith("I'll tell you when the pantry's flour gets down to 5")
    assert "flour" in cw._list_tool(context, {})
    refused = cw._watch_tool(context, {"question": "tell me when we're out of saffron"})
    assert "I don't see saffron in your pantry" in refused
    assert "couldn't tell what to watch for" in cw._watch_tool(context, {"question": "tell me a story"})
    context.condition_watches.add(cw.Watch("w9", "freeze", value=32.0))
    assert "flour" in cw._stop_tool(context, {"question": "stop watching the flour"})
    assert "low" in cw._stop_tool(context, {"question": "stop telling me when it freezes"})
    assert cw._list_tool(context, {}).startswith("I'm not watching anything for you yet")
