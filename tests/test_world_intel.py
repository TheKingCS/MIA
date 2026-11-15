"""
tests.test_world_intel
========================

World Intelligence, phase W1 (DEC-0170; core/world_intel.py, core/world_sources.py, core/world_intel_actions.py,
core/web_world_intel.py): a watch's words are matched phrase by phrase; the same find is kept once however it's
linked; a run reads each source through its kind's adapter and records one that refuses; the worker thread only
reads and the store changes when its results are collected; new finds go to the gate under one kind, each naming its
source; saving a find counts as engaging; the actions, the page and the voice tools agree; nothing runs while it's
off; and no test goes online (every source is a stand-in).
"""

from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from core import world_intel, world_sources
from core.world_intel import Watch, WorldBook, dedupe_key, matches, phrases, run_watch

NOW = datetime(2026, 11, 15, 9, 0)
FEED = """<?xml version="1.0"?><rss version="2.0"><channel><title>t</title>
<item><title>Cheap polycarbonate greenhouse panels compared</title><link>https://example.org/panels?utm_source=x</link>
<description>Twin-wall panels for small greenhouses.</description><pubDate>Sun, 15 Nov 2026 07:00:00 +0000</pubDate></item>
<item><title>A new llama.cpp release</title><link>https://example.org/llama</link><description>Faster.</description></item>
</channel></rss>"""


def _watch(words="greenhouse panels", **kw):
    """A watch on these words."""
    return Watch("w1", kw.pop("name", "Panels"), words, **kw)


def test_a_watch_matches_every_word_of_one_of_its_phrases_plurals_included():
    assert phrases("Greenhouse panels, PVC") == [["greenhouse", "panels"], ["pvc"]]
    w = _watch("greenhouse panel, solar pump")
    assert matches(w, {"title": "Greenhouse panels on sale", "summary": ""}) == ["greenhouse panel"]
    assert matches(w, {"title": "Greenhouse tips", "summary": "no match here"}) == []
    assert matches(w, {"title": "A solar pump for ponds", "summary": ""}) == ["solar pump"]


def test_the_same_find_is_kept_once_however_it_is_linked():
    a = dedupe_key({"link": "https://www.Example.org/panels/?utm_source=feed&id=3#top"})
    b = dedupe_key({"link": "https://example.org/panels?id=3"})
    assert a == b
    assert dedupe_key({"title": "Same Title"}) == dedupe_key({"title": "same   title"})


def test_a_run_reads_each_source_through_its_adapter_and_records_one_that_refuses():
    good = world_sources.Source("good", "Good Feed", "feed", "u", ("homestead",))
    bad = world_sources.Source("bad", "Bad Feed", "feed", "u", ("homestead",))
    down = world_sources.Source("down", "Down Feed", "feed", "u", ("homestead",))

    def fetch(src, watch):
        """A stand-in feed reader: good parses the fixture, bad refuses, down fails."""
        if src.source_id == "bad":
            raise world_sources.SourceRefused("403")
        if src.source_id == "down":
            raise OSError("timeout")
        from core.good_news import parse_feed
        return parse_feed(FEED, src.source_id)

    result = run_watch(_watch(), NOW, {"feed": fetch}, sources=[good, bad, down])
    assert [item["title"] for item, _ in result["items"]] == ["Cheap polycarbonate greenhouse panels compared"]
    assert result["refused"] == ["bad"] and result["failed"] == ["down"]


def test_old_news_is_left_out_so_a_first_run_brings_no_backlog():
    src = world_sources.Source("rel", "Releases", "feed", "u", ("self",))
    old = {"source": "rel", "title": "Ollama v0.1", "link": "https://e.org/old", "summary": "",
           "published": (NOW - timedelta(days=40)).isoformat()}
    fresh = {"source": "rel", "title": "Ollama v0.2", "link": "https://e.org/new", "summary": "",
             "published": (NOW - timedelta(days=2)).isoformat()}
    undated = {"source": "rel", "title": "Ollama notes", "link": "https://e.org/x", "summary": "", "published": ""}
    result = run_watch(_watch("ollama"), NOW, {"feed": lambda s, w: [old, fresh, undated]}, sources=[src])
    assert [item["title"] for item, _ in result["items"]] == ["Ollama v0.2", "Ollama notes"]


def test_a_feed_that_shows_a_block_page_counts_as_refused():
    src = world_sources.Source("x", "X", "feed", "https://x", ("news",))
    with pytest.raises(world_sources.SourceRefused):
        world_sources.fetch_feed(src, _watch(), get_text=lambda url: "<html>Please complete the CAPTCHA</html>")
    assert world_sources.fetch_feed(src, _watch(), get_text=lambda url: FEED)[0]["source"] == "x"


def test_every_catalog_source_has_a_name_an_area_and_an_adapter():
    assert len({s.source_id for s in world_sources.CATALOG}) == len(world_sources.CATALOG)
    for s in world_sources.CATALOG:
        assert s.name and s.areas and set(s.areas) <= set(world_sources.AREAS) and s.kind in world_sources.ADAPTERS
        assert s.url.startswith("https://")


@pytest.fixture
def book(tmp_path):
    """An empty World Intelligence store in its own folder."""
    return WorldBook(MagicMock(), data_dir=tmp_path)


def test_ingesting_keeps_each_find_once_with_its_source_named_and_records_the_run(book):
    w = book.add_watch("Panels", "greenhouse panels", areas=["homestead"])
    item = {"source": "hobby_farms", "title": "Greenhouse panels half off", "link": "https://example.org/p",
            "summary": "", "published": "2026-11-15T08:00:00+00:00"}
    new = book.ingest([{"watch_id": w.watch_id, "at": NOW.isoformat(), "items": [(item, ["greenhouse panels"])],
                        "refused": ["phoronix"]}], NOW)
    assert len(new) == 1 and new[0].source_name == "Hobby Farms" and "published in the last day" in new[0].why
    again = book.ingest([{"watch_id": w.watch_id, "at": NOW.isoformat(), "items": [(dict(item), ["greenhouse panels"])]}], NOW)
    assert again == [] and len(book.discoveries) == 1
    reloaded = WorldBook(MagicMock(), data_dir=book.data_dir)
    assert reloaded.watches[0].last_run and reloaded.watches[0].refused == ["phoronix"] and reloaded.watches[0].runs == 2


def test_a_watch_is_due_by_its_hours_and_never_while_paused(book):
    w = book.add_watch("Panels", "greenhouse panels", every_hours=6)
    assert book.due_watches(NOW) == [w]
    w.last_run = (NOW - timedelta(hours=2)).isoformat()
    assert book.due_watches(NOW) == []
    w.last_run = (NOW - timedelta(hours=7)).isoformat()
    book.set_paused(w.watch_id, True)
    assert book.due_watches(NOW) == []


def test_the_worker_thread_only_reads_and_the_store_changes_when_its_results_are_collected(book):
    w = book.add_watch("Panels", "greenhouse panels", sources=["hobby_farms"])
    runner = world_intel.Runner()
    from core.good_news import parse_feed

    assert runner.start([w], NOW, {"feed": lambda src, watch: parse_feed(FEED, src.source_id)})
    runner._thread.join(5)
    assert book.discoveries == []  # nothing written by the thread
    results = runner.collect()
    assert results and runner.collect() == []
    assert len(book.ingest(results, NOW)) == 1


class _Gate:
    """A stand-in gate that remembers what was offered and what was engaged with."""

    def __init__(self):
        """Nothing offered yet."""
        self.offered, self.engaged = [], []

    def offer_batch(self, candidates, now=None):
        """Remembers the candidates."""
        self.offered.extend(candidates)
        return []

    def note_engagement(self, topic="", notification_id="", how="acted", now=None):
        """Remembers an engagement."""
        self.engaged.append((topic, how))
        return True


@pytest.fixture
def context(tmp_path, monkeypatch):
    """A context with the store, a stand-in gate, and World Intelligence switched on through the setting."""
    settings = {"world.on": True}
    from core import person_settings

    monkeypatch.setattr(person_settings, "get", lambda ctx, key, default=None: settings.get(key, default))
    monkeypatch.setattr(person_settings, "put", lambda ctx, key, value: settings.__setitem__(key, value))
    ctx = SimpleNamespace(world_intel=WorldBook(MagicMock(), data_dir=tmp_path), communication=_Gate(), settings=settings)
    return ctx


def test_new_finds_go_to_the_gate_once_under_one_kind_each_naming_its_source(context):
    book = context.world_intel
    w = book.add_watch("Panels", "greenhouse panels", sources=["hobby_farms"])
    from core.good_news import parse_feed

    fetchers = {"feed": lambda src, watch: parse_feed(FEED, src.source_id)}
    world_intel.tick(context, NOW, fetchers)  # starts the run
    world_intel.runner_for(book)._thread.join(5)
    new = world_intel.tick(context, NOW + timedelta(minutes=10), fetchers)  # collects and offers
    assert len(new) == 1
    [c] = context.communication.offered
    assert c.topic == "world_find" and c.message.startswith("From Hobby Farms.") and c.title.startswith("Found: ")
    world_intel.tick(context, NOW + timedelta(minutes=30), fetchers)
    assert len(context.communication.offered) == 1  # never offered twice
    assert book.get_watch(w.watch_id).found == 1


def test_nothing_runs_while_it_is_off(context):
    context.settings["world.on"] = False
    context.world_intel.add_watch("Panels", "greenhouse panels")
    assert world_intel.tick(context, NOW, {"feed": lambda s, w: pytest.fail("read while off")}) == []
    assert not world_intel.runner_for(context.world_intel).busy()


def test_the_actions_add_pause_save_and_set_aside_and_saving_counts_as_engaging(context):
    from core.actions import ACTION_TYPES, ActionError

    run = lambda kind, **p: (ACTION_TYPES[kind].describe(context, p), ACTION_TYPES[kind].execute(context, p))  # noqa: E731
    said, done = run("world_watch.add", words="solar pump, aquaponics pump", areas="homestead,energy", max_price="120")
    assert "Watch for “solar pump, aquaponics pump” in homestead" in said and "up to" in said and "Watching for" in done
    with pytest.raises(ActionError):
        ACTION_TYPES["world_watch.add"].describe(context, {"words": "  "})
    with pytest.raises(ActionError):
        ACTION_TYPES["world_watch.add"].describe(context, {"words": "pumps", "areas": "moon"})
    run("world_watch.pause", watch="solar pump")
    assert context.world_intel.watches[0].paused
    w = context.world_intel.watches[0]
    item = {"source": "electrek", "title": "A solar pump test", "link": "https://e.org/1", "summary": ""}
    [find] = context.world_intel.ingest([{"watch_id": w.watch_id, "items": [(item, ["solar pump"])]}], NOW)
    run("world_find.save", discovery_id=find.discovery_id)
    assert context.world_intel.get(find.discovery_id).status == "saved"
    assert context.communication.engaged == [("world_find", "acted")]
    run("world_intel.switch", on="no")
    assert context.settings["world.on"] is False


def test_the_page_and_the_voice_tools_say_the_same_finds_with_their_sources(context):
    from core.assistant_actions import AssistantActionRegistry
    from core.assistant_world_intel_actions import register_world_intel_actions
    from core.web_world_intel import world_page

    registry = AssistantActionRegistry()
    register_world_intel_actions(registry)
    say = lambda name, **a: registry.execute(context, name, a)  # noqa: E731
    assert "not watching for anything" in say("world_finds")
    w = context.world_intel.add_watch("Panels", "greenhouse panels")
    item = {"source": "hobby_farms", "title": "Greenhouse panels half off", "link": "https://example.org/p", "summary": ""}
    context.world_intel.ingest([{"watch_id": w.watch_id, "items": [(item, ["greenhouse panels"])]}], NOW)
    page = world_page(context, NOW)
    assert page["on"] and page["finds"][0]["source"] == "Hobby Farms" and page["counts"]["new"] == 1
    assert "Greenhouse panels half off (from Hobby Farms)" in say("world_finds")
    assert "Panels (1 found" in say("list_watches")
