"""
tests/test_assistant_screen_tools.py — voice for screens that had none (core/assistant_screen_tools.py, DEC-0125):
looking something up online through the person's own engine (and saying why not when it can't), what isn't working,
past conversations listed and searched, and the sensors listed with their last readings.
"""

from types import SimpleNamespace

from core import assistant_screen_tools as t
from core import online_lookup


def test_looking_it_up_online_searches_their_own_engine_and_says_the_sources(monkeypatch):
    sent = {}

    def fake_search(context, words):
        """Stands in for the person's own SearXNG."""
        sent["words"] = words
        return {"query": words, "at": "2026-11-09T10:00", "results": [
            {"title": "Fence posts", "source": "extension.example.edu", "url": "https://extension.example.edu/posts",
             "snippet": "Set posts a third of their length deep.", "published": ""}]}

    monkeypatch.setattr(online_lookup, "search", fake_search)
    said = t._look_up(SimpleNamespace(), {"words": "how deep do fence posts go"})
    assert sent["words"] == "how deep do fence posts go"
    assert "extension.example.edu" in said and "not from your records" in said
    assert t._look_up(SimpleNamespace(), {"words": " "}) == "What should I look up?"


def test_when_it_cant_look_it_up_it_says_why(monkeypatch):
    def unavailable(context, words):
        """The engine isn't running."""
        raise online_lookup.LookupUnavailable("My search engine (SearXNG) isn't answering on this computer.")

    monkeypatch.setattr(online_lookup, "search", unavailable)
    assert "SearXNG" in t._look_up(SimpleNamespace(), {"words": "frost dates"})


def test_what_isnt_working_comes_from_her_own_capability_list(monkeypatch):
    import core.capabilities

    monkeypatch.setattr(core.capabilities, "status_summary", lambda context=None, here="pc": "40 of my apps are fully working.")
    assert t._app_status(SimpleNamespace(), {}) == "40 of my apps are fully working."


def _conversations():
    """A context with two kept conversations."""
    msg = lambda role, content: SimpleNamespace(role=role, content=content)  # noqa: E731
    convs = [SimpleNamespace(conversation_id="c2", title="Coop plans", updated_at="2026-11-08T09:00", created_at="",
                             messages=[msg("user", "How big should the chicken coop be?"), msg("assistant", "4 sq ft a hen.")]),
             SimpleNamespace(conversation_id="c1", title="", updated_at="2026-11-01T20:00", created_at="",
                             messages=[msg("user", "What's for dinner?")])]
    return SimpleNamespace(conversations=SimpleNamespace(all_conversations=lambda: convs))


def test_past_conversations_are_listed_newest_first():
    said = t._past(_conversations(), {})
    assert said.startswith("2 kept") and said.index("Coop plans") < said.index("Untitled")


def test_a_conversation_is_found_by_what_was_said_in_it():
    said = t._find(_conversations(), {"words": "chicken coop"})
    assert "Coop plans" in said and "How big" in said
    assert "didn't find" in t._find(_conversations(), {"words": "tractor"})
    assert "don't keep" in t._find(SimpleNamespace(), {"words": "coop"})


def test_the_sensors_are_listed_with_their_last_reading(tmp_path, monkeypatch):
    import core.person_settings
    from core.sensors import SensorStore

    monkeypatch.setattr(core.person_settings, "person_id", lambda context: "p1")
    ctx = SimpleNamespace()
    ctx.sensors = SensorStore(ctx, data_dir=tmp_path)
    assert "No sensors yet" in t._sensors(ctx, {})
    s, _key = ctx.sensors.add("p1", "Bench probe", "lab", {"series": "soil moisture"})
    ctx.sensors.get(s["id"]).update(last_at="2026-11-09T08:15:00", last_value=41.5)
    assert t._sensors(ctx, {}) == "Bench probe → The Lab: soil moisture: 41.5 at 08:15 on 2026-11-09."
    assert "aren't on this MIA" in t._sensors(SimpleNamespace(), {})
