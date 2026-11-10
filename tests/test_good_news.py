"""Good News Radio (DEC-0096, core/good_news.py): good news judged in code, each story saying how it's known
(confirmed by two outlets, from the source itself, or one outlet, each with its tag), its caveats kept, four personalities, on only
when switched on, and stories called misleading counted by source. Its page (2026-11-10): a story followed
and what was reported on it since, a story marked misleading from the screen, an episode made on request,
playing it counted as heard once a day, and what the screen is handed."""

import json
from datetime import date, datetime, timedelta
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
    """A stand-in person whose settings live in a dict, and the news folder in a temporary one. The loops'
    30 days are counted back from the tests' own week, so they pass whenever they run."""
    import core.person_settings as ps

    store = {}
    monkeypatch.setattr(ps, "get", lambda context, key, default=None: store.get(key, default))
    monkeypatch.setattr(ps, "put", lambda context, key, value: store.__setitem__(key, value))
    monkeypatch.setattr(gn, "DATA", tmp_path / "news")
    monkeypatch.setattr(loops, "_since",  # the 30 days counted back from the tests' own week, whenever they run
                        lambda days: (datetime(2026, 11, 10) - timedelta(days=days)).isoformat())
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


def test_each_way_a_story_is_known_has_its_tag():
    from core.good_news import KNOWN_TAGS

    assert KNOWN_TAGS["confirmed"]["tone"] == "ok" and KNOWN_TAGS["one outlet"]["tone"] == "attention"
    assert set(KNOWN_TAGS) == {"confirmed", "from the source", "one outlet"}  # every value the reader gives `known`


# ------------------------------------------------------------------ the page: stories to read, follow and mark

FEEDS = {url: (RSS if "bbc" in url else ATOM if "npr.org/1007" in url else "<rss/>") for _i, _n, url, _k in gn.SOURCES}
DAY = date(2026, 11, 6)
MORNING = datetime(2026, 11, 6, 8, 0)
LATER = {"source": "npr-science", "title": "Malaria vaccine success: child deaths stay halved in trial a year on",
         "link": "https://b.example/20", "published": "2026-11-08T09:00:00+00:00", "summary": "The gain held. More soon."}


def _episode(day: date = DAY) -> dict:
    """The one-story episode of the sample feeds, kept as `day`'s (the buttons read today's, whenever a test runs)."""
    record = gn.make(DAY, fetch=lambda url: FEEDS[url])
    if day != DAY:
        (gn._episodes() / f"{DAY.isoformat()}.json").rename(gn._episodes() / f"{day.isoformat()}.json")
        path = gn._episodes() / f"{day.isoformat()}.json"
        record = {**record, "day": day.isoformat()}
        path.write_text(json.dumps(record), encoding="utf-8")
    return record


def test_the_page_lists_each_story_with_a_summary_and_where_to_read_it(person):
    person.settings[gn.SETTING] = True
    _episode()
    page = gn.screen(person, MORNING)
    [story] = page["stories"]
    assert page["on"] and page["today"] and page["fresh"] and page["day"] == "2026-11-06" and not page["can_make"]
    assert story["summary"] == "A new vaccine halved deaths in a pilot trial." and story["how"] and len(story["id"]) == 10
    assert story["reads"] == [{"outlet": "BBC Science", "href": "https://a.example/1"},
                              {"outlet": "NPR", "href": "https://b.example/9"}]
    assert story["followed"] is False and story["misleading"] is False and story["tag"]
    assert [p["when"] for p in page["personalities"]] == list(gn.PERSONALITIES) and page["audio"] == {}
    assert {"name": "NASA", "kind": gn.PRIMARY} in page["sources"] and set(page["scripts"]) == set(gn.PERSONALITIES)
    older = gn.screen(person, datetime(2026, 11, 10, 8, 0))  # nothing made since: still readable, never called today's
    assert older["day"] == "2026-11-06" and not older["today"] and not older["fresh"]
    assert gn.screen(person, datetime(2026, 11, 20, 8, 0))["day"] is None


def test_a_link_that_is_not_a_web_address_is_never_offered_to_open():
    assert gn._reads(["A", "B"], ["javascript:alert(1)", "https://x.example/1"]) == [
        {"outlet": "B", "href": "https://x.example/1"}]


def test_a_recording_is_found_in_the_music_library_by_its_title():
    tracks = [SimpleNamespace(title="Good News Radio: Sunny, Nov 6", track_id="t1"),
              SimpleNamespace(title="Something else", track_id="t2")]
    music = SimpleNamespace(all_tracks=lambda: tracks)
    record = {"tracks": {"morning": "Good News Radio - Sunny (Nov 6)", "evening": "Never recorded"}}
    assert gn._audio(SimpleNamespace(music=music), record) == {"morning": "t1"}
    assert gn._audio(SimpleNamespace(), record) == {}


def test_a_followed_story_gets_its_later_reports_once_and_good_or_not(person):
    person.settings[gn.SETTING] = True
    record = _episode()
    sid = gn.story_id(record["stories"][0])
    kept = gn.follow(person, sid, MORNING)
    assert kept["since"] == "2026-11-06" and kept["outlets"] == ["BBC Science", "NPR"]
    assert gn.follow(person, sid, MORNING) == kept and len(gn.following(person)) == 1  # twice changes nothing
    items = gn.parse_feed(RSS, "bbc") + [  # its own report, an older one, an unrelated one, and what happened next
        {**LATER, "link": "https://b.example/3", "published": "2026-11-01T09:00:00+00:00"},
        {"source": "nasa", "title": "A telescope finds a new moon", "link": "https://n.example/1",
         "published": "2026-11-08T09:00:00+00:00", "summary": ""},
        LATER,
        {"source": "bbc", "title": "Malaria vaccine trial halted after child deaths rise", "link": "https://a.example/7",
         "published": "2026-11-09T09:00:00+00:00", "summary": ""}]
    assert gn.keep_updates(person, items, date(2026, 11, 9)) == 2
    assert gn.keep_updates(person, items, date(2026, 11, 10)) == 0  # never kept twice
    [mine] = gn.screen(person, MORNING)["following"]
    assert [(u["href"], u["good"], u["found"]) for u in mine["updates"]] == [
        ("https://a.example/7", False, "2026-11-09"), ("https://b.example/20", True, "2026-11-09")]  # newest first
    assert mine["updates"][1]["outlet"] == "NPR" and mine["updates"][1]["summary"] == "The gain held. More soon."
    assert gn.screen(person, MORNING)["stories"][0]["followed"] is True
    assert gn.unfollow(person, sid)["id"] == sid and gn.following(person) == [] and gn.unfollow(person, sid) is None
    with pytest.raises(ValueError):
        gn.follow(person, "nope", MORNING)


def test_following_and_marking_by_voice_do_what_the_buttons_do(person):
    person.settings[gn.SETTING] = True
    _episode()
    assert "first" in gn.reply(person, "follow that story", MORNING)  # nothing heard yet: it says how
    gn.reply(person, "what's the good news?", MORNING)
    assert gn.reply(person, "Follow that story.", MORNING).startswith("Following \"New malaria vaccine")
    assert "nothing new yet" in gn.reply(person, "what's new on the stories I follow?", MORNING)
    gn.keep_updates(person, [LATER], date(2026, 11, 9))
    assert "NPR reported" in gn.reply(person, "what am I following?", MORNING)
    assert gn.reply(person, "stop following the malaria story", MORNING).startswith("Stopped following")
    assert "aren't following any" in gn.reply(person, "what's new on the stories I follow?", MORNING)
    assert gn.reply(person, "follow the story about the malaria vaccines", MORNING).startswith("Following")
    assert gn.reply(person, "follow the story about cricket", MORNING) is None  # not one of its stories
    assert gn.reply(person, "stop following me", MORNING) is None
    assert gn.reply(person, "the story about the malaria vaccine was misleading", MORNING).startswith("Marked")
    assert "already marked" in gn.reply(person, "the one about malaria was wrong", MORNING)
    reading = BY_ID["news.misleading"].measure(person)
    assert reading.n == 1 and "bbc 1" in reading.detail  # counted on the episode already heard, not a new one
    assert gn.screen(person, MORNING)["stories"][0]["misleading"] is True
    assert "is off" in gn.reply(person, "turn off good news radio", MORNING) and not gn.is_on(person)
    assert gn.reply(person, "follow that story", MORNING) is None  # off: the words are someone else's to answer
    assert "off" in gn.reply(person, "make today's good news", MORNING)


def test_the_buttons_follow_mark_and_switch_like_the_words(person, monkeypatch):
    from core.actions import ACTION_TYPES, ActionError

    def act(kind, **params):
        """Describes, then does, one action: (the sentence approved, what it said happened)."""
        return ACTION_TYPES[kind].describe(person, params), ACTION_TYPES[kind].execute(person, params)

    def refused(kind, **params):
        """Whether the action is refused before anything is asked of the person."""
        with pytest.raises(ActionError):
            ACTION_TYPES[kind].describe(person, params)
        return True

    monkeypatch.setattr(loops, "_has_repo", lambda: True)
    record = _episode(date.today())
    sid = gn.story_id(record["stories"][0])
    assert refused("news.follow", story_id=sid) and refused("news.make")  # it's off
    assert act("news.turn_on")[0] == "Turn Good News Radio on" and gn.is_on(person) and refused("news.turn_on")
    assert refused("news.make")  # today's is already made
    said, done = act("news.follow", story_id=sid)
    assert said == "Follow \"New malaria vaccine cuts child deaths by half in trial\"" and done.startswith("Following")
    assert refused("news.follow", story_id=sid) and refused("news.follow", story_id="nope")
    assert gn.screen(person)["following"][0]["id"] == sid
    assert act("news.unfollow", story_id=sid)[1].startswith("Stopped following") and refused("news.unfollow", story_id=sid)
    assert act("news.misleading", story_id=sid)[1].startswith("Marked") and refused("news.misleading", story_id=sid)
    assert BY_ID["news.misleading"].measure(person).n == 1  # marked before it was heard: the episode counts from here
    (gn._episodes() / f"{date.today().isoformat()}.json").unlink()
    said, done = act("news.make")  # in a test nothing is started: launch() never runs a process from one
    assert said == "Start making today's episode" and done.startswith("Making today's episode")
    assert act("news.turn_off")[0] == "Turn Good News Radio off" and not gn.is_on(person) and refused("news.turn_off")


def test_listening_on_the_page_counts_once_a_day(person):
    _episode()
    assert gn.note_listened(person, "morning", MORNING) is False  # off
    person.settings[gn.SETTING] = True
    assert gn.note_listened(person, "nobody", MORNING) is True and gn.heard(person)[-1]["personality"] == "morning"
    assert gn.note_listened(person, "evening", MORNING) is False and len(gn.heard(person)) == 1
    assert gn.note_listened(person, "evening", datetime(2026, 11, 7, 20, 0)) is True
    assert BY_ID["news.misleading"].measure(person).n == 2


def test_old_episodes_and_start_notes_are_tidied_and_a_start_counts_for_minutes(person, monkeypatch):
    monkeypatch.setattr(loops, "_has_repo", lambda: True)
    person.settings[gn.SETTING] = True
    gn._episodes().mkdir(parents=True)
    (gn._episodes() / "2026-09-01.json").write_text("{}", encoding="utf-8")
    (gn.DATA / "started-2026-11-05").write_text("x", encoding="utf-8")
    _episode()
    assert sorted(p.name for p in gn._episodes().iterdir()) == ["2026-11-06.json"]
    assert not (gn.DATA / "started-2026-11-05").exists()
    now = datetime.now()
    assert gn.can_make(person, now) is None and gn.screen(person, now)["can_make"] is True
    (gn.DATA / f"started-{now.date().isoformat()}").write_text("x", encoding="utf-8")
    assert gn.making(now) and "being made" in gn.can_make(person, now) and gn.screen(person, now)["making"] is True
    assert not gn.making(now + timedelta(minutes=gn.MAKING_MINUTES + 1))  # a start that never finished stops counting
