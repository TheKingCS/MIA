"""Good News Radio (DEC-0096, core/good_news.py): good news judged in code, each story saying how it's known
(confirmed by two outlets, from the source itself, or one outlet), its caveats kept, four personalities, on only
when switched on, and stories called misleading counted by source."""

from datetime import date, datetime
from types import SimpleNamespace

import pytest

from core import good_news as gn
from core import loops

BY_ID = {l.id: l for l in loops.LOOPS}
RSS = """<?xml version="1.0"?><rss><channel>
<item><title>New malaria vaccine cuts child deaths by half in trial</title><link>https://a.example/1</link>
<description>&lt;p&gt;A &lt;b&gt;new vaccine&lt;/b&gt; halved deaths in a pilot trial.&lt;/p&gt;</description>
<pubDate>Thu, 05 Nov 2026 10:00:00 GMT</pubDate></item>
<item><title>Storm kills dozens</title><link>https://a.example/2</link><description>A disaster.</description></item>
</channel></rss>"""
ATOM = """<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">
<entry><title>Malaria vaccine halves child deaths in new trial</title><link href="https://b.example/9"/>
<summary>Researchers report a breakthrough.</summary><updated>2026-11-05T12:00:00Z</updated></entry></feed>"""


def test_feeds_rss_and_atom():
    items = gn.parse_feed(RSS, "bbc") + gn.parse_feed(ATOM, "npr-science")
    assert [i["link"] for i in items] == ["https://a.example/1", "https://a.example/2", "https://b.example/9"]
    assert items[0]["summary"] == "A new vaccine halved deaths in a pilot trial." and items[2]["published"].startswith("2026-11-05")
    assert gn.parse_feed("not xml", "bbc") == []


def test_what_counts_as_good_news():
    good = {"source": "bbc", "title": "New malaria vaccine cuts child deaths by half in trial", "summary": ""}
    assert gn.judge(good) == "health"
    for bad in ("Storm kills dozens", "A Farewell to Swift", "NASA's Swift telescope falls to Earth after 22 years",
                "APOD: Midwestern City Lights", "What went right this week: the good news that matters"):
        assert gn.judge({"source": "nasa", "title": bad, "summary": "new"}) is None, bad
    assert gn.judge({"source": "nasa", "title": "Scientists study the moon", "summary": "a passing new"}) is None
    assert gn.caveats({"source": "sciencedaily", "title": "Drug may help", "summary": "in mice"}) == [
        "so far in animals or the lab, not yet in people", "it says could, not does", "from a press release"]


def test_a_story_two_outlets_told_is_confirmed():
    items = gn.parse_feed(RSS, "bbc") + gn.parse_feed(ATOM, "npr-science")
    [story] = gn.gather(items)
    assert story["known"] == "confirmed" and story["sources"] == ["bbc", "npr-science"] and len(story["links"]) == 2
    assert "an early result" in story["caveats"]  # the pilot stays in
    one = gn.gather(gn.parse_feed(RSS, "nih"))[0]
    assert one["known"] == "from the source"
    assert gn.gather(gn.parse_feed(RSS, "positive"))[0]["known"] == "one outlet"


def test_the_pick_keeps_variety_and_drops_flagged_sources():
    stories = [{"title": f"t{i}", "topic": "energy" if i < 3 else "health", "sources": [src], "known": "one outlet",
                "published": f"2026-11-0{i + 1}T00:00:00+00:00", "links": [], "caveats": []}
               for i, src in enumerate(["canary", "canary", "canary", "positive", "cheerful"])]
    picked = gn.pick(stories)
    assert [s["title"] for s in picked] == ["t4", "t3", "t2", "t1"]  # two a topic, two an outlet, newest first
    assert all("cheerful" not in s["sources"] for s in gn.pick(stories, flagged=("cheerful",)))


def test_the_script_says_how_its_known_and_never_makes_any_up():
    [story] = gn.gather(gn.parse_feed(RSS, "bbc") + gn.parse_feed(ATOM, "npr-science"))
    text = gn.script([story], "late night")
    assert text.startswith("Well, hello, night owls") and "Reported by BBC Science and NPR." in text
    assert "Worth knowing: an early result" in text
    assert "won't make any up" in gn.script([], "morning")
    assert gn.personality_for(7) == "morning" and gn.personality_for(23) == "late night"
    assert gn.personality_for(9, "the calm one") == "evening"


@pytest.fixture
def person(tmp_path, monkeypatch):
    import core.person_settings as ps

    store = {}
    monkeypatch.setattr(ps, "get", lambda context, key, default=None: store.get(key, default))
    monkeypatch.setattr(ps, "put", lambda context, key, value: store.__setitem__(key, value))
    monkeypatch.setattr(gn, "DATA", tmp_path / "news")
    return SimpleNamespace(failures=SimpleNamespace(data_dir=tmp_path / "me"), settings=store)


def test_off_until_switched_on_then_asked_and_flagged(person):
    now = datetime(2026, 11, 6, 8, 0)
    assert "off" in gn.reply(person, "what's the good news?", now)
    assert "Nothing about you is sent" in gn.reply(person, "turn on good news radio", now)
    assert "isn't ready yet" in gn.reply(person, "good news", now)
    feeds = {url: (RSS if "bbc" in url else ATOM if "npr.org/1007" in url else "<rss/>") for _i, _n, url, _k in gn.SOURCES}
    gn.make(date(2026, 11, 6), fetch=lambda url: feeds[url])
    said = gn.reply(person, "what's the good news today?", now)
    assert said.startswith("Good morning!") and "malaria" in said.lower()
    assert gn.reply(person, "good news, the calm one", now).startswith("Good evening.")
    assert "weigh that source down" in gn.reply(person, "that story was misleading", now)
    reading = BY_ID["news.misleading"].measure(person)
    assert reading.n == 2 and "bbc 1" in reading.detail
    assert gn.reply(person, "what's for dinner", now) is None


def test_it_goes_online_only_from_the_pc_and_never_from_a_test(person, monkeypatch):
    monkeypatch.setattr(loops, "_has_repo", lambda: True)
    person.settings[gn.SETTING] = True
    assert gn.due(person, datetime(2026, 11, 6, 8, 0)) and not gn.due(person, datetime(2026, 11, 6, 4, 0))
    gn.launch()  # a no-op in a test run: no process, no fetch
    assert not (gn.DATA / "last_run.log").exists()
