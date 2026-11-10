"""
core.good_news
================

Good News Radio (DEC-0096, build plan step 13; Zac, 2026-11-06: AI that reads
credible outlets daily and gathers good news, healing, technology, medicine,
renewable energy, societies improving, "heard through AI radio personalities
matched to mood"; sources by Claude's recommendation, approved, and its going
online approved by Zac).

**Where it reads** (`SOURCES`): primary sources (NASA, NIH, WHO, Nature, MIT
News, Our World in Data), science journalism (BBC, NPR, The Conversation,
ScienceDaily's press releases, labelled as such) and solutions journalism
(Positive News, Reasons to be Cheerful, Anthropocene, Canary Media). Only
their public feeds, once a day, and only when a person has switched it on
(DEC-0053). Nothing about anyone is sent.

**What counts as good news** (`judge()`, in code): a story about health,
science, energy, nature, society, technology or space, with a sign of
progress, and none of the words of harm (a death, a war, a disaster).

**Honest, not just upbeat**:
- each story says how it's known: *confirmed* (two or more independent
  outlets), *from the source* (the agency or journal itself), or *one
  outlet*;
- its caveats stay in ("an early study in mice", "a pilot", "a press
  release"): nothing important is cut to keep it cheerful;
- every story keeps its links.

**Four personalities** (`PERSONALITIES`), each a Kokoro voice, picked by the
hour or asked for ("the calm one"): Sunny in the morning, Spark in the
afternoon, Still in the evening, Night Owl late. An episode is a script made
in code (`script()`), kept on the PC (`data/good_news/`), and, when Kokoro is
installed, a track in MIA's music library ("Good News Radio, Sunny, Nov 6")
the PC, phone and glasses can play.

**Its loop** (`news.misleading`): stories the person said were misleading
("that story was misleading", or the story's button on the page), by source; a
source that keeps misleading opens a task to drop it.

**Following a story** (Zac, 2026-11-10): a person can follow a story from the
page or by voice ("follow that story"). Each day's feeds are then checked for
later reports on it (`follow_ups()`, by the headline's own words), good news
or not: following means hearing what happened next. What they follow, and
what was found, is theirs (`good_news_following.json` in their own folder).

**Its page** (`screen()`, web/news.html): the latest episode's stories with a
summary, how each is known and where to read it in full, the episode to play
in each personality's voice, the stories followed, and the switches (on, off,
make today's now) as actions in `core/news_actions.py`. Everything the page
does can be said, and everything said has its control there (DEC-0125).
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Callable, Optional

from core.atomic_write import atomic_write_text
from core.logger import get_logger

log = get_logger(__name__)

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "good_news"
SETTING = "good_news.on"
STORIES = 6
KEEP_DAYS = 3
KEEP_TRACKS = 7
LATEST_DAYS = 7  # how far back the page looks for an episode to show
KEEP_EPISODES = 30  # days an episode's file is kept
MAKING_MINUTES = 15  # how long a started episode counts as being made
FOLLOW_LIMIT = 20  # stories one person follows at once
UPDATES_KEPT = 12  # later reports kept for one followed story
AGENT ="MIA-GoodNewsRadio/1.0 (+offline-first personal assistant; one fetch a day)"

PRIMARY, JOURNALISM, SOLUTIONS, PRESS = "primary", "journalism", "solutions", "press release"
SOURCES = (
    ("nasa", "NASA", "https://www.nasa.gov/news-release/feed/", PRIMARY),
    ("nih", "the NIH", "https://www.nih.gov/news-releases/feed.xml", PRIMARY),
    ("who", "the WHO", "https://www.who.int/rss-feeds/news-english.xml", PRIMARY),
    ("nature", "Nature", "https://www.nature.com/nature.rss", PRIMARY),
    ("mit", "MIT News", "https://news.mit.edu/rss/feed", PRIMARY),
    ("owid", "Our World in Data", "https://ourworldindata.org/atom.xml", PRIMARY),
    ("bbc", "BBC Science", "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml", JOURNALISM),
    ("npr-science", "NPR", "https://feeds.npr.org/1007/rss.xml", JOURNALISM),
    ("npr-health", "NPR", "https://feeds.npr.org/1128/rss.xml", JOURNALISM),
    ("conversation", "The Conversation", "https://theconversation.com/us/articles.atom", JOURNALISM),
    ("sciencedaily", "ScienceDaily", "https://www.sciencedaily.com/rss/top/science.xml", PRESS),
    ("sciencedaily-health", "ScienceDaily", "https://www.sciencedaily.com/rss/health_medicine.xml", PRESS),
    ("positive", "Positive News", "https://www.positive.news/feed/", SOLUTIONS),
    ("cheerful", "Reasons to be Cheerful", "https://reasonstobecheerful.world/feed/", SOLUTIONS),
    ("anthropocene", "Anthropocene Magazine", "https://www.anthropocenemagazine.org/feed/", SOLUTIONS),
    ("canary", "Canary Media", "https://www.canarymedia.com/rss.rss", SOLUTIONS),
)
SOURCE_BY_ID = {s[0]: s for s in SOURCES}

TOPICS = (
    ("health", r"\b(cure[sd]?|treatment|therap\w+|vaccine\w*|patients?|cancer|disease|diabet\w+|heart|brain|health\w*|"
               r"medic\w+|drug|surgery|hospital|recover\w*|heal\w*|malaria|hiv|alzheimer\w*)\b"),
    ("energy", r"\b(solar|wind (power|farm|energy)|renewab\w+|batter(y|ies)|clean energy|electric (car|vehicle|bus)\w*|"
               r"\bev\b|heat pumps?|geothermal|grid|emissions?|carbon|hydrogen|nuclear fusion|fusion)\b"),
    ("nature", r"\b(species|wildlife|forest\w*|reef\w*|ocean\w*|rewild\w*|conservation|habitat|birds?|whales?|"
               r"restor\w+|biodiversity|river\w*)\b"),
    ("society", r"\b(poverty|literacy|school\w*|communit\w+|housing|homeless\w*|refugees?|equality|rights|"
                r"life expectancy|child mortality|hunger|clean water|volunteer\w*)\b"),
    ("space", r"\b(nasa|space|mars|moon|lunar|orbit\w*|telescope|asteroid|planet\w*|astronaut\w*|galax\w+|satellite\w*)\b"),
    ("technology", r"\b(robot\w*|\bai\b|artificial intelligence|chip\w*|quantum|3d.print\w*|invent\w*|engineer\w*|"
                   r"material\w*|device\w*|sensor\w*)\b"),
    ("science", r"\b(scientists?|researchers?|study|discover\w*|found that|breakthrough|first ever|new (method|way))\b"),
)
PROGRESS = re.compile(r"\b(new|first|breakthrough|cure[sd]?|approved?|restor\w+|recover\w+|rebound\w*|record (high|low)|"
                      r"success\w*|saves?|saved|improv\w+|reduc\w+|(deaths?|cases|poverty|emissions|prices|costs?|hunger|crime) "
                      r"(falls?|fell|drops?|dropped|plunge\w*|halv\w+)|declin\w+ in "
                      r"(deaths?|cases|poverty|emissions)|rises? in|boosts?|helps?|protect\w*|returns?|thriv\w+|"
                      r"milestone|launch\w*|wins?|won|eliminat\w+|eradicat\w+|clean\w*|cheaper|better|discover\w*|"
                      r"breakthrough|promising|hope\w*)\b", re.IGNORECASE)
HARM = re.compile(r"\b(kill\w*|dead|deaths? (toll|rise|climb)|dies|died|dying|war|wars|warfare|shoot\w*|attack\w*|bomb\w*|"
                  r"crash\w*|fraud|lawsuit|sued|scandal|layoffs?|collapse\w*|crisis|outbreak|disaster\w*|catastroph\w*|"
                  r"threat\w*|fears?|warns?|warning|extinct\w*|wildfire\w*|flood\w*|hurricane\w*|earthquake\w*|famine|"
                  r"abuse\w*|murder\w*|arrest\w*|protest\w*|tariff\w*|recession|shortage\w*|cuts? (to|in) (funding|aid)|"
                  r"farewell|final (days?|mission|flight)|ends?|ended|ending|retir\w+|shut\w* down|cancel\w*|"
                  r"decommission\w*|lost|loses|losing|falls? to earth|burn\w* up|re-?enters?)\b",
                  re.IGNORECASE)
STRONG = re.compile(r"\b(breakthrough|first[- ]ever|for the first time|cure[sd]?|approved|record (high|low)|"
                    r"restored|eradicat\w+|eliminat\w+|saved|halved|doubled|success(ful|fully)?)\b", re.IGNORECASE)
SKIP = re.compile(r"^(APOD|Image of the Day|Photo of the Day|Podcast|Newsletter|Quiz|Live|Watch|Video)\b|"
                  r"\b(podcast|newsletter|webinar|quiz|what went right|round.?up|this week in|the week in|digest)\b",
                  re.IGNORECASE)
CAVEATS = (
    (r"\b(in mice|mouse|mice|in rats?|animal (study|studies|model)|in (the )?lab|cells? in a dish|cell cultures?)\b",
     "so far in animals or the lab, not yet in people"),
    (r"\b(early|preliminary|pilot|small (study|trial)|phase (1|i|one)\b|proof.of.concept|first.in.human)\b",
     "an early result"),
    (r"\b(could|may|might|potential\w*|promising)\b", "it says could, not does"),
)


# ------------------------------------------------------------------ feeds (pure)

def _text(node) -> str:
    """All the text inside an XML element ("" for none)."""
    return "".join(node.itertext()).strip() if node is not None else ""


def plain(text: str, limit: int = 400) -> str:
    """Pure logic. A feed's HTML summary as plain words."""
    text = html.unescape(re.sub(r"<[^>]+>", " ", str(text or "")))
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + "…"


def parse_feed(xml_text: str, source_id: str) -> list[dict]:
    """Pure logic. RSS or Atom -> [{source, title, link, summary, published}]."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []
    out = []
    atom = "{http://www.w3.org/2005/Atom}"
    for item in root.iter():
        tag = item.tag.split("}")[-1]
        if tag not in ("item", "entry"):
            continue
        title = plain(_text(item.find("title")) or _text(item.find(f"{atom}title")), 200)
        link = _text(item.find("link"))
        if not link:
            found = item.find(f"{atom}link")
            link = found.get("href", "") if found is not None else ""
        summary = plain(_text(item.find("description")) or _text(item.find(f"{atom}summary"))
                        or _text(item.find(f"{atom}content")))
        when = _text(item.find("pubDate")) or _text(item.find(f"{atom}updated")) or _text(item.find(f"{atom}published"))
        try:
            published = (parsedate_to_datetime(when) if "," in when else datetime.fromisoformat(when.replace("Z", "+00:00")))
            published = published.astimezone(timezone.utc).isoformat(timespec="seconds")
        except (TypeError, ValueError, IndexError):
            published = ""
        if title and link:
            out.append({"source": source_id, "title": title, "link": link, "summary": summary, "published": published})
    return out


def _fetch(url: str) -> str:
    """One public feed, fetched with MIA's own user agent (at most 3 MB, 20-second timeout)."""
    request = urllib.request.Request(url, headers={"User-Agent": AGENT})
    with urllib.request.urlopen(request, timeout=20) as answer:
        return answer.read(3_000_000).decode("utf-8", errors="replace")


def fetch_all(fetch: Callable[[str], str] = _fetch, sources=SOURCES) -> tuple[list[dict], list[str]]:
    """Every source's feed: (items, the sources that didn't answer)."""
    items, failed = [], []
    for source_id, _name, url, _kind in sources:
        try:
            items.extend(parse_feed(fetch(url), source_id))
        except Exception as problem:  # one feed down never stops the rest
            log.info("Good News: %s didn't answer (%s)", source_id, problem)
            failed.append(source_id)
    return items, failed


# ------------------------------------------------------------------ judging (pure)

def judge(item: dict) -> Optional[str]:
    """Pure logic. The story's topic when it's good news, else None."""
    text = f"{item.get('title', '')} {item.get('summary', '')}"
    title = item.get("title", "")
    if HARM.search(title) or len(HARM.findall(text)) > 1 or SKIP.search(title):
        return None
    topic = next((name for name, words in TOPICS if re.search(words, text, re.IGNORECASE)), None)
    if topic is None:
        return None
    kind = SOURCE_BY_ID.get(item.get("source"), (0, 0, 0, ""))[3]
    if kind != SOLUTIONS and not (PROGRESS.search(title) or STRONG.search(item.get("summary", ""))):
        return None  # the progress has to be the story, not a word in passing
    return topic


def caveats(item: dict) -> list[str]:
    """Pure logic. What the story's own words say to keep in mind."""
    text = f"{item.get('title', '')} {item.get('summary', '')}"
    found = [say for words, say in CAVEATS if re.search(words, text, re.IGNORECASE)]
    if SOURCE_BY_ID.get(item.get("source"), (0, 0, 0, ""))[3] == PRESS:
        found.append("from a press release")
    return found


def _alike(a: str, b: str) -> float:
    """How alike two headlines are (0 to 1), to spot the same story from different outlets."""
    from core.failure_log import similar

    return similar(a, b)


def gather(items: list[dict], alike: float = 0.3) -> list[dict]:
    """Pure logic. Good-news stories, each with every outlet that told it and how it's known."""
    stories: list[dict] = []
    for item in items:
        topic = judge(item)
        if topic is None:
            continue
        home = next((s for s in stories if _alike(s["title"], item["title"]) >= alike), None)
        if home is None:
            stories.append({**item, "topic": topic, "sources": [item["source"]], "links": [item["link"]],
                            "caveats": caveats(item)})
        elif item["source"] not in home["sources"]:
            home["sources"].append(item["source"])
            home["links"].append(item["link"])
            home["caveats"] = sorted(set(home["caveats"]) | set(caveats(item)))
    for s in stories:
        outlets = {SOURCE_BY_ID[x][1] for x in s["sources"] if x in SOURCE_BY_ID}
        kinds = {SOURCE_BY_ID[x][3] for x in s["sources"] if x in SOURCE_BY_ID}
        s["known"] = "confirmed" if len(outlets) > 1 else "from the source" if PRIMARY in kinds else "one outlet"
    return stories


RANK = {"confirmed": 0, "from the source": 1, "one outlet": 1}  # how it's known is said either way


def pick(stories: list[dict], n: int = STORIES, per_topic: int = 2, flagged: tuple = (),
         per_source: int = 2) -> list[dict]:
    """Pure logic. The episode's stories: the best-known first, newest within that, no more than two a topic or
    an outlet, never a source the person flagged as misleading."""
    ordered = sorted((s for s in stories if not set(s["sources"]) & set(flagged)),
                     key=lambda s: (RANK[s["known"]], -_stamp(s.get("published", ""))))
    out, count, outlet = [], {}, {}
    for s in ordered:
        home = SOURCE_BY_ID.get(s["sources"][0], (0, s["sources"][0]))[1]
        if count.get(s["topic"], 0) >= per_topic or outlet.get(home, 0) >= per_source:
            continue
        out.append(s)
        count[s["topic"]] = count.get(s["topic"], 0) + 1
        outlet[home] = outlet.get(home, 0) + 1
        if len(out) == n:
            break
    return out


def _stamp(text: str) -> float:
    """A timestamp from ISO text, as seconds (0 when it can't be read)."""
    try:
        return datetime.fromisoformat(text).timestamp()
    except ValueError:
        return 0.0


def story_id(story: dict) -> str:
    """Pure logic. A story's id, the same on every day and device: made from its first link (its headline when it
    has none)."""
    first = (story.get("links") or [story.get("link", "")])[0] or story.get("title", "")
    return hashlib.sha1(str(first).encode("utf-8")).hexdigest()[:10]


# ------------------------------------------------------------------ following a story (pure)

COMMON = frozenset(
    "the and for with from that this these those have has had are was were will would its into onto new first says "
    "said say study studies scientists researchers research after before over under more most than about how why "
    "what when where who could may might can their they them been being not but you your our one two three year "
    "years day days week weeks now just also here there out off all any some found finds find shows show "
    "reveals reveal report reports make makes made help helps gets get got way ways use uses used using".split())


def _keywords(text: str) -> set[str]:
    """Pure logic. A headline's own words: three letters or more, the everyday ones left out, a plural's "s" dropped
    (so "reefs" and "reef" are the same word)."""
    words = (w for w in re.findall(r"[a-z0-9]+", str(text or "").lower()) if len(w) >= 3 and w not in COMMON)
    return {w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w for w in words}


def _same_subject(a: set[str], b: set[str]) -> bool:
    """Pure logic. Whether two headlines' words are about the same thing: three words shared, or two when that is
    most of the shorter headline. Strict on purpose: a missed report is better than a wrong one."""
    shared = len(a & b)
    return shared >= 3 or (shared >= 2 and shared / min(len(a), len(b)) >= 0.6)


def follow_ups(items: list[dict], followed: list[dict]) -> dict[str, list[dict]]:
    """Pure logic. Later reports on each followed story among the feeds' items, by followed id, oldest first: an item
    about the same subject, not one of the story's own links or a report already kept, and not published before the
    story. Good news or not (each says which): following means hearing what happened next."""
    out: dict[str, list[dict]] = {}
    for f in followed:
        mine = _keywords(f.get("title", ""))
        known = set(f.get("links", [])) | set(f.get("seen", [])) | {u.get("link") for u in f.get("updates", [])}
        found = []
        for item in items:
            if not mine or item["link"] in known:
                continue
            if item.get("published") and f.get("published") and item["published"] <= f["published"]:
                continue
            theirs = _keywords(item["title"])
            if not theirs or not _same_subject(mine, theirs):
                continue
            known.add(item["link"])
            found.append({"title": item["title"], "link": item["link"], "source": item["source"],
                          "outlet": SOURCE_BY_ID.get(item["source"], (0, item["source"]))[1],
                          "published": item.get("published", ""),
                          "summary": _first_sentences(item.get("summary", ""), 2, 320)
                          if item.get("summary") and item["summary"] != item["title"] else "",
                          "good": judge(item) is not None})
        if found:
            out[f["id"]] = sorted(found, key=lambda u: _stamp(u["published"]))
    return out


# ------------------------------------------------------------------ on the air (pure)

PERSONALITIES = {
    "morning": {"name": "Sunny", "voice": "kokoro:af_bella", "hours": range(5, 11),
                "open": "Good morning! This is Good News Radio, I'm Sunny, and the world did some good things. Let's go!",
                "turn": ("Next up!", "And here's another.", "Oh, this one's great.", "Keep that coffee warm for this:"),
                "close": "That's your good news. Go have a great day!"},
    "afternoon": {"name": "Spark", "voice": "kokoro:bf_emma", "hours": range(11, 17),
                  "open": "Hello, curious people. This is Good News Radio with Spark, and I've been reading.",
                  "turn": ("Here's something fascinating.", "Now, this one made me look twice.", "Stay with me on this:",
                           "And another."),
                  "close": "That's what's going right today. Stay curious."},
    "evening": {"name": "Still", "voice": "kokoro:af_nicole", "hours": range(17, 21),
                "open": "Good evening. This is Good News Radio. I'm Still. Let's take a few quiet minutes for what went well.",
                "turn": ("Here's another.", "Next, gently.", "And this one.", "One more good thing."),
                "close": "That's all for tonight. Rest easy."},
    "late night": {"name": "Night Owl", "voice": "kokoro:bm_george", "hours": (21, 22, 23, 0, 1, 2, 3, 4),
                   "open": "Well, hello, night owls. You're up late, and so am I. This is Good News Radio. Let's see "
                           "what the world got right while everyone else was sleeping.",
                   "turn": ("Now get this.", "And folks, it gets better.", "Next story. You'll like this one.",
                            "Here's one for the insomniacs."),
                   "close": "That's the show. Get some sleep, will you? Good night."},
}
ASKED = (("late night", r"late.?night|night owl|talk show"), ("evening", r"calm|still|quiet|gentle|evening"),
         ("morning", r"morning|sunny|energetic|upbeat|pump me up"), ("afternoon", r"curious|spark|afternoon"))


def personality_for(hour: int, asked: str = "") -> str:
    """Which radio personality reads: the one the person asked for, else the one for this hour of the day."""
    for key, words in ASKED:
        if asked and re.search(words, asked, re.IGNORECASE):
            return key
    return next(k for k, p in PERSONALITIES.items() if hour in p["hours"])


def _how_known(s: dict) -> str:
    """How a story is known, in words: reported by which outlets (confirmed), from the source itself, or one outlet
    so far.
    """
    names = []
    for x in s["sources"]:
        name = SOURCE_BY_ID.get(x, (0, x))[1]
        if name not in names:
            names.append(name)
    if s["known"] == "confirmed":
        return f"Reported by {' and '.join(names[:2])}" + (f" and {len(names) - 2} more" if len(names) > 2 else "") + "."
    if s["known"] == "from the source":
        return f"That's from {names[0]} itself."
    return f"That's from {names[0]}, one outlet so far."


# How a story is known, as the design canvas tags it (DEC-0113): green when two outlets confirm it, plain when it's
# the source's own word, amber when only one outlet has it so far.
KNOWN_TAGS = {"confirmed": {"tag": "Confirmed by two outlets", "tone": "ok"},
              "from the source": {"tag": "From the source itself", "tone": ""},
              "one outlet": {"tag": "One outlet", "tone": "attention"}}


BOILERPLATE = re.compile(r"\b(supported by|sponsored|see more|subscribe|sign up|newsletter|column|welcome back|"
                         r"read more|click here|the post .* appeared first)\b", re.IGNORECASE)


def _first_sentences(text: str, n: int = 2, limit: int = 320) -> str:
    """A story's first sentences (two by default), boilerplate left out, cut at a word near the limit."""
    parts = [s for s in re.split(r"(?<=[.!?])\s+", text or "") if s and not BOILERPLATE.search(s)]
    out = " ".join(parts[:n]).strip()
    return out if len(out) <= limit else out[:limit].rsplit(" ", 1)[0] + "…"


def script(stories: list[dict], personality: str) -> str:
    """Pure logic. The episode as she'll say it: every story with how it's known and its caveats."""
    p = PERSONALITIES[personality]
    if not stories:
        return f"{p['open']} I didn't find good news I could stand behind today, so I won't make any up. Back tomorrow."
    lines = [p["open"]]
    for i, s in enumerate(stories):
        lead = "" if i == 0 else p["turn"][i % len(p["turn"])] + " "
        body = _first_sentences(s["summary"]) if s["summary"] and s["summary"] != s["title"] else ""
        caveat = (" Worth knowing: " + "; ".join(s["caveats"]) + ".") if s["caveats"] else ""
        lines.append(f"{lead}{s['title'].rstrip('.')}." + (f" {body}" if body else "") + f" {_how_known(s)}{caveat}")
    lines.append(p["close"])
    return "\n\n".join(lines)


# ------------------------------------------------------------------ the day's episode

def _episodes() -> Path:
    """Where each day's episode is kept."""
    return DATA / "episodes"


def episode(day: Optional[date] = None) -> Optional[dict]:
    """One day's episode (today by default), or None when there isn't one."""
    day = day or date.today()
    try:
        return json.loads((_episodes() / f"{day.isoformat()}.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def latest(day: Optional[date] = None, days: int = LATEST_DAYS) -> Optional[dict]:
    """The newest episode from `day` (today by default) back `days` days, or None: what the page shows when today's
    isn't made yet."""
    day = day or date.today()
    for back in range(days + 1):
        found = episode(day - timedelta(days=back))
        if found is not None:
            return found
    return None


def _tidy_episodes(day: date) -> None:
    """Episodes older than KEEP_EPISODES days, and the "started" notes of earlier days, are deleted."""
    oldest = (day - timedelta(days=KEEP_EPISODES)).isoformat()
    for path in list(_episodes().glob("*.json")):
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", path.stem) and path.stem < oldest:
            path.unlink(missing_ok=True)
    for path in list(DATA.glob("started-*")):
        if path.name[len("started-"):] < day.isoformat():
            path.unlink(missing_ok=True)


def making(now: Optional[datetime] = None) -> bool:
    """Whether today's episode is being made right now: started within MAKING_MINUTES and not there yet. (A start
    that never finished stops counting, so it can be started again.)"""
    now = now or datetime.now()
    started = DATA / f"started-{now.date().isoformat()}"
    try:
        age = now.timestamp() - started.stat().st_mtime
    except OSError:
        return False
    return episode(now.date()) is None and age < MAKING_MINUTES * 60


def make(day: Optional[date] = None, fetch: Callable[[str], str] = _fetch, flagged: tuple = (),
         on_items: Optional[Callable[[list[dict]], None]] = None) -> dict:
    """The day's stories, fetched, judged, checked against each other and kept, with every personality's script.
    Fresh means published within KEEP_DAYS before the end of that day (not before now), so an episode made for a
    given day keeps the same stories whenever it's made. `on_items` is handed everything the feeds held (how a
    person's followed stories get their later reports, `keep_updates`, without their list going in the episode)."""
    day = day or date.today()
    items, failed = fetch_all(fetch)
    if on_items is not None:
        try:
            on_items(items)
        except Exception:  # the episode is still made
            log.exception("Good News: the followed stories couldn't be checked")
    day_end = datetime(day.year, day.month, day.day, tzinfo=timezone.utc) + timedelta(days=1)
    since = (day_end - timedelta(days=KEEP_DAYS + 1)).isoformat()
    fresh = [i for i in items if not i["published"] or i["published"] >= since]
    stories = pick(gather(fresh), flagged=flagged)
    record = {"day": day.isoformat(), "made": datetime.now().isoformat(timespec="seconds"), "items": len(items),
              "failed": failed, "stories": stories,
              "scripts": {k: script(stories, k) for k in PERSONALITIES}, "tracks": {}}
    _episodes().mkdir(parents=True, exist_ok=True)
    atomic_write_text(_episodes() / f"{day.isoformat()}.json", json.dumps(record, indent=1, ensure_ascii=False))
    _tidy_episodes(day)
    return record


def on_air(context, record: dict, personality: str, synth=None) -> Optional[str]:
    """The episode in its personality's voice, as a track in MIA's music library. Returns its title, or None
    without Kokoro."""
    music = getattr(context, "music", None)
    if music is None:
        return None
    p = PERSONALITIES[personality]
    title = f"Good News Radio, {p['name']}, {date.fromisoformat(record['day']):%b} {date.fromisoformat(record['day']).day}"
    path = _episodes() / f"{record['day']}-{p['name'].lower().replace(' ', '-')}.wav"
    try:
        if synth is None:
            from core.voice_catalog import VoiceOption
            from core.voice_manager import KokoroBackend

            synth = KokoroBackend(VoiceOption(p["voice"], p["name"], engine="kokoro")).synthesize
        synth(record["scripts"][personality].replace("\n\n", " "), path)
        music.save_upload(f"{title}.wav", path.read_bytes())
        music.scan_library()
    except Exception:
        log.exception("Good News Radio couldn't be voiced")
        return None
    finally:
        path.unlink(missing_ok=True)
    _tidy_tracks(music)
    record["tracks"][personality] = title
    atomic_write_text(_episodes() / f"{record['day']}.json", json.dumps(record, indent=1, ensure_ascii=False))
    return title


def _tidy_tracks(music) -> None:
    """Only the last week's episodes stay in the library."""
    mine = sorted((t for t in music.all_tracks() if t.title.startswith("Good News Radio,") and music.uploaded(t)),
                  key=lambda t: t.file_path)
    for t in mine[:-KEEP_TRACKS]:
        music.delete_track(t.track_id)


# ------------------------------------------------------------------ the person: on, asked, flagged

def is_on(context) -> bool:
    """Whether this person has switched Good News Radio on (it's off until they do)."""
    from core import person_settings

    return bool(person_settings.get(context, SETTING, False))


def _folder(context) -> Optional[Path]:
    """The person's own folder (where their Fix-It Log or traces live), or None."""
    for name in ("failures", "traces"):
        found = getattr(getattr(context, name, None), "data_dir", None)
        if found is not None:
            return Path(found)
    return None


def heard(context) -> list[dict]:
    """What this person has heard: each day's stories, and any they called misleading."""
    folder = _folder(context)
    try:
        return json.loads((folder / "good_news_heard.json").read_text(encoding="utf-8")).get("heard", []) if folder else []
    except (OSError, ValueError):
        return []


def _note_heard(context, entry: dict) -> None:
    """Adds to what this person has heard (about the last 500 entries kept), atomically."""
    folder = _folder(context)
    if folder is None:
        return
    found = heard(context)[-500:] + [entry]
    folder.mkdir(parents=True, exist_ok=True)
    atomic_write_text(folder / "good_news_heard.json", json.dumps({"heard": found}, indent=1))


def flagged_sources(context, days: int = 90, at_least: int = 2) -> tuple:
    """The outlets this person called misleading at least `at_least` times in the last `days` days."""
    since = (date.today() - timedelta(days=days)).isoformat()
    by: dict[str, int] = {}
    for h in heard(context):
        if h.get("day", "") >= since:
            for s in h.get("misleading", []):
                by[s] = by.get(s, 0) + 1
    return tuple(s for s, n in by.items() if n >= at_least)


# ------------------------------------------------------------------ the person: followed, marked, listened

def _story(record: Optional[dict], sid: str) -> Optional[dict]:
    """The story with this id in an episode, or None."""
    return next((s for s in (record or {}).get("stories", []) if story_id(s) == sid), None)


def _find_story(stories: list[dict], words: str) -> Optional[dict]:
    """The story (or followed story) a person's words name ("the reef one"): the one sharing the most of their words
    with its headline and topic, the first of them on a tie; None when none shares any."""
    asked = _keywords(words)
    best, most = None, 0
    for s in stories:
        shared = len(asked & _keywords(f"{s.get('title', '')} {s.get('topic', '')}"))
        if shared > most:
            best, most = s, shared
    return best


def following(context) -> list[dict]:
    """The stories this person follows, oldest first: id, title, topic, its links and their outlets, when it was
    published and followed (`since`), the later reports found (`updates`) and every report link seen (`seen`)."""
    folder = _folder(context)
    try:
        found = json.loads((folder / "good_news_following.json").read_text(encoding="utf-8")) if folder else {}
    except (OSError, ValueError):
        return []
    return [f for f in found.get("following", []) if isinstance(f, dict) and f.get("id")]


def _save_following(context, found: list[dict]) -> None:
    """Writes the followed stories to the person's own folder, atomically (so an action's change can be undone).
    ValueError, in words, for an account with no folder."""
    folder = _folder(context)
    if folder is None:
        raise ValueError("There's nowhere to keep followed stories for this account.")
    folder.mkdir(parents=True, exist_ok=True)
    atomic_write_text(folder / "good_news_following.json",
                      json.dumps({"following": found}, indent=1, ensure_ascii=False))


def follow(context, sid: str, now: Optional[datetime] = None) -> dict:
    """Starts following a story of the latest episode and returns what's kept. Following one already followed changes
    nothing. ValueError, in words for the person, when the story isn't there anymore or FOLLOW_LIMIT is reached."""
    now = now or datetime.now()
    found = following(context)
    mine = next((f for f in found if f["id"] == sid), None)
    if mine is not None:
        return mine
    story = _story(latest(now.date()), sid)
    if story is None:
        raise ValueError("That story isn't in the latest episode anymore.")
    if len(found) >= FOLLOW_LIMIT:
        raise ValueError(f"You're following {FOLLOW_LIMIT} stories, the most I keep up with. Stop following one first.")
    mine = {"id": sid, "title": story["title"], "topic": story.get("topic", ""), "links": list(story["links"]),
            "outlets": [SOURCE_BY_ID.get(x, (0, x))[1] for x in story["sources"]],
            "published": story.get("published", ""), "since": now.date().isoformat(), "updates": [], "seen": []}
    _save_following(context, found + [mine])
    return mine


def unfollow(context, sid: str) -> Optional[dict]:
    """Stops following a story (its kept reports go with it). Returns what was kept, or None when it wasn't followed."""
    found = following(context)
    mine = next((f for f in found if f["id"] == sid), None)
    if mine is not None:
        _save_following(context, [f for f in found if f["id"] != sid])
    return mine


def keep_updates(context, items: list[dict], today: Optional[date] = None) -> int:
    """Checks a day's feed items against this person's followed stories and keeps each later report found (the newest
    UPDATES_KEPT a story, each with the day it was found). Returns how many were new."""
    found = following(context)
    if not found:
        return 0
    new = follow_ups(items, found)
    day = (today or date.today()).isoformat()
    count = 0
    for f in found:
        for update in new.get(f["id"], []):
            f.setdefault("updates", []).append({**update, "found": day})
            f["seen"] = (f.get("seen", []) + [update["link"]])[-200:]
            count += 1
        f["updates"] = f.get("updates", [])[-UPDATES_KEPT:]
    if count:
        _save_following(context, found)
    return count


def flagged_ids(context, day: str) -> set[str]:
    """The stories of one day's episode this person marked misleading, by story id."""
    return {sid for h in heard(context) if h.get("day") == day for sid in h.get("flagged", [])}


def flag(context, sid: str, now: Optional[datetime] = None) -> dict:
    """Marks a story of the latest episode misleading, from its button or "the story about X was misleading": its
    outlet is counted (the `news.misleading` loop, `flagged_sources`) and the story is remembered as marked.
    Returns the story. ValueError, in words, when it isn't there, was already marked, or can't be kept."""
    now = now or datetime.now()
    record = latest(now.date())
    story = _story(record, sid)
    folder = _folder(context)
    if story is None:
        raise ValueError("That story isn't in the latest episode anymore.")
    if folder is None:
        raise ValueError("There's nowhere to keep that for this account.")
    if sid in flagged_ids(context, record["day"]):
        raise ValueError("You already marked that story misleading.")
    found = heard(context)[-500:]
    at = next((n for n in range(len(found) - 1, -1, -1)
               if found[n].get("day") == record["day"] and found[n].get("stories")), None)
    if at is None:  # marked before it was played or asked for: the episode counts as heard from here
        found.append({"at": now.isoformat(timespec="seconds"), "day": record["day"], "how": "screen",
                      "personality": personality_for(now.hour),
                      "stories": [s["sources"][0] for s in record["stories"]]})
        at = len(found) - 1
    found[at].setdefault("misleading", []).append(story["sources"][0])
    found[at].setdefault("flagged", []).append(sid)
    folder.mkdir(parents=True, exist_ok=True)
    atomic_write_text(folder / "good_news_heard.json", json.dumps({"heard": found}, indent=1))
    return story


def note_listened(context, personality: str = "", now: Optional[datetime] = None) -> bool:
    """The page saying its episode was played: counted as heard once a day, so stories listened to on the page count
    toward the misleading share the same as ones asked for. False when it's off, there's no episode, or today's
    listening is already counted."""
    now = now or datetime.now()
    record = latest(now.date())
    if record is None or not is_on(context) or _folder(context) is None:
        return False
    today = now.date().isoformat()
    if any(h.get("how") == "screen" and h.get("day") == record["day"] and str(h.get("at", "")).startswith(today)
           for h in heard(context)):
        return False
    _note_heard(context, {"at": now.isoformat(timespec="seconds"), "day": record["day"], "how": "screen",
                          "personality": personality if personality in PERSONALITIES else personality_for(now.hour),
                          "stories": [s["sources"][0] for s in record["stories"]]})
    return True


def can_make(context, now: Optional[datetime] = None) -> Optional[str]:
    """Why today's episode can't be started right now, in words for the person, or None when it can."""
    from core import loops

    now = now or datetime.now()
    if not is_on(context):
        return "Good News Radio is off. Turn it on first."
    if episode(now.date()) is not None:
        return "Today's episode is already made."
    if making(now):
        return "Today's episode is being made right now. Give it a minute or two."
    if not loops._has_repo():
        return "The episode is made on the home computer, and this isn't it."
    return None


def start_making(context, now: Optional[datetime] = None) -> str:
    """Starts today's episode now instead of waiting for the daily check (`launch()`, a process of its own), and
    says so. ValueError with why not (`can_make`)."""
    why = can_make(context, now)
    if why:
        raise ValueError(why)
    launch()
    return "Making today's episode: reading the feeds and recording the voices takes a minute or two."


_ASK = re.compile(r"^(?:(?:what'?s|tell me|give me|any|got any|read me|let'?s hear)(?: the)? )?good news(?: radio)?"
                  r"(?: today| please| for me)?(?:,? (?:with )?(?:the )?(.+?))?[?.!]*$", re.IGNORECASE)
_WRONG = r"(?:was|is|seemed|sounds) (?:misleading|wrong|not true|overblown|hype)"
_MISLEADING = re.compile(rf"^(?:that|the last|that last) (?:story|one) {_WRONG}[.!]*$", re.IGNORECASE)
_MISLEADING_ABOUT = re.compile(rf"^the (?:story|one) (?:about|on) (.+?) {_WRONG}[.!]*$", re.IGNORECASE)
_TURN_ON = re.compile(r"^(?:turn on|switch on|start|enable) good news(?: radio)?[.!]*$", re.IGNORECASE)
_TURN_OFF = re.compile(r"^(?:turn off|switch off|disable) good news(?: radio)?[.!]*$", re.IGNORECASE)
_MAKE = re.compile(r"^(?:make|build|refresh|update) (?:today'?s |the )?good news(?: radio)?(?: episode)?"
                   r"(?: now| today)?[.!]*$", re.IGNORECASE)
_FOLLOW_THAT = re.compile(r"^follow (?:that|this|the last|that last) (?:story|one)[.!]*$", re.IGNORECASE)
_FOLLOW = re.compile(r"^follow the (?:(?:story|one) (?:about|on) (.+?)|(.+?) story)[.!]*$", re.IGNORECASE)
_UNFOLLOW = re.compile(r"^(?:stop following|unfollow) (?:the )?(?:(?:story|one) (?:about|on) )?(.+?)(?: story)?[.!]*$",
                       re.IGNORECASE)
_I_FOLLOW = r"(?:the |my )?stories i(?:'m| am)? follow(?:ing)?"
_UPDATES = re.compile(rf"^(?:what'?s new (?:on|with|in) {_I_FOLLOW}|what (?:stories )?am i following|"
                      rf"any(?:thing)? (?:new|updates?|news) on {_I_FOLLOW}|(?:show |list )?(?:me )?{_I_FOLLOW}|"
                      r"(?:show |list )?(?:me )?my followed stories)[?.!]*$", re.IGNORECASE)
OFF_SAID = "Good News Radio is off. Say \"turn on good news radio\" and I'll read the news for you once a day."
THANKS_SAID = "Thanks: I'll weigh that source down, and drop it if it keeps happening."


def reply(context, text: str, now: Optional[datetime] = None) -> Optional[str]:
    """Talking to it: "what's the good news?", "good news, the calm one", "that story was misleading", "the story
    about the reef was misleading", "turn on good news radio", "turn off good news radio", "make today's good
    news", "follow that story", "follow the story about the reef", "stop following the reef story", "what's new on
    the stories I follow?". None when it isn't that."""
    from core import person_settings

    said = " ".join(str(text or "").split())
    now = now or datetime.now()
    if _TURN_ON.match(said):
        person_settings.put(context, SETTING, True)
        return ("Good News Radio is on. Once a day I'll read the public feeds of NASA, the NIH, the WHO, Nature, MIT "
                "News, Our World in Data, the BBC, NPR, The Conversation, ScienceDaily, Positive News, Reasons to be "
                "Cheerful, Anthropocene and Canary Media. Nothing about you is sent. Say \"what's the good news?\".")
    if _TURN_OFF.match(said):
        person_settings.put(context, SETTING, False)
        return "Good News Radio is off. I won't read the feeds again until you turn it back on."
    if _MISLEADING.match(said):
        found = heard(context)
        last = next((n for n in range(len(found) - 1, -1, -1) if found[n].get("stories")), None)
        folder = _folder(context)
        if last is None or folder is None:
            return None
        found[last].setdefault("misleading", []).append(found[last]["stories"][-1])  # the story just heard
        atomic_write_text(folder / "good_news_heard.json", json.dumps({"heard": found}, indent=1))
        return THANKS_SAID
    if _MAKE.match(said):
        try:
            return start_making(context, now) if is_on(context) else OFF_SAID
        except ValueError as problem:
            return str(problem)
    stories = _said_about_a_story(context, said, now)
    if stories is not None:
        return stories
    asked = _ASK.match(said)
    if not asked:
        return None
    if not is_on(context):
        return OFF_SAID
    record = episode(now.date()) or episode(now.date() - timedelta(days=1))
    if record is None:
        return "Today's Good News Radio isn't ready yet; I put it together once a day. Ask me again in a bit."
    key = personality_for(now.hour, asked.group(1) or "")
    _note_heard(context, {"at": now.isoformat(timespec="seconds"), "day": record["day"], "personality": key,
                          "stories": [s["sources"][0] for s in record["stories"]]})
    track = record.get("tracks", {}).get(key)
    tail = f"\n\n(It's in {PERSONALITIES[key]['name']}'s voice in your music too: say \"play {track}\".)" if track else ""
    return record["scripts"][key] + tail


def _said_about_a_story(context, said: str, now: datetime) -> Optional[str]:
    """The story commands of `reply()`: following one ("that story", or named by its subject), stopping, what's new
    on the ones followed, and marking a named one misleading. None when it isn't one of those, the radio is off, or
    the words name no story it has (so the words can still mean something else to MIA)."""
    that, named, stop = _FOLLOW_THAT.match(said), _FOLLOW.match(said), _UNFOLLOW.match(said)
    news, wrong = _UPDATES.match(said), _MISLEADING_ABOUT.match(said)
    if not (that or named or stop or news or wrong) or not is_on(context):
        return None
    mine = following(context)
    if news:
        if not mine:
            return ("You aren't following any stories. Say \"follow that story\" after the news, or press Follow on "
                    "one on the Good News Radio page.")
        lines = []
        for f in mine:
            reports = f.get("updates", [])
            lines.append(f"- {f['title']}: " + (
                f"{reports[-1]['outlet']} reported \"{reports[-1]['title']}\""
                + (f" ({len(reports)} reports so far)." if len(reports) > 1 else ".") if reports
                else "nothing new yet."))
        return "The stories you follow:\n" + "\n".join(lines)
    if stop:
        target = _find_story(mine, stop.group(1))
        if target is None:
            return None
        unfollow(context, target["id"])
        return f"Stopped following \"{target['title']}\"."
    record = latest(now.date())
    stories = (record or {}).get("stories", [])
    if wrong:
        story = _find_story(stories, wrong.group(1))
        if story is None:
            return None
        try:
            flag(context, story_id(story), now)
        except ValueError as problem:
            return str(problem)
        return f"Marked \"{story['title']}\" misleading. {THANKS_SAID}"
    if that:
        last = next((h for h in reversed(heard(context)) if h.get("stories")), None)
        story = stories[-1] if stories and last is not None and last.get("day") == record["day"] else None
        if story is None:
            return ("Ask me \"what's the good news?\" first and then say \"follow that story\", or name it: "
                    "\"follow the story about the reef\".")
    else:
        words = named.group(1) or named.group(2)
        story = _find_story(stories, words)
        if story is None:
            return None
    try:
        kept = follow(context, story_id(story), now)
    except ValueError as problem:
        return str(problem)
    return (f"Following \"{kept['title']}\". When an outlet I read reports more on it, good or not, it'll be on the "
            "Good News Radio page, or ask \"what's new on the stories I follow?\".")


def due(context, now: Optional[datetime] = None) -> bool:
    """On for this person, on the PC, and today's episode not made yet (after 5 in the morning)."""
    from core import loops

    now = now or datetime.now()
    started = DATA / f"started-{now.date().isoformat()}"
    return is_on(context) and loops._has_repo() and now.hour >= 5 and episode(now.date()) is None and not started.exists()


def launch() -> None:
    """Today's episode, made in a process of its own (the feeds and the voice take a minute), with a console that's
    never shown (core.dev_lab.quiet_job_flags), so nothing it runs flashes a window."""
    import os
    import subprocess
    import sys

    if os.environ.get("PYTEST_CURRENT_TEST"):
        return  # never from a test run: it goes online
    from core.dev_lab import _python, quiet_job_flags

    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / f"started-{date.today().isoformat()}").write_text(datetime.now().isoformat(), encoding="utf-8")
    with open(DATA / "last_run.log", "w", encoding="utf-8") as out:
        subprocess.Popen([_python(), "-m", "tools.good_news", "make"], cwd=str(ROOT), stdout=out,
                         stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                         creationflags=quiet_job_flags())


def _reads(names: list, links: list) -> list[dict]:
    """Where to read a story in full: [{outlet, href}] in the order its outlets told it, web links only (whatever
    else a feed put in a link never becomes something the page opens)."""
    return [{"outlet": names[n] if n < len(names) else "", "href": link} for n, link in enumerate(links)
            if str(link).startswith(("https://", "http://"))]


def _flat(text) -> str:
    """A title as letters and digits only, to match a recording's title to its track whatever the library did to
    its punctuation."""
    return re.sub(r"[^a-z0-9]+", "", str(text).lower())


def _audio(context, record: dict) -> dict:
    """The music-library track of each personality's recording of this episode, {personality: track id}: {} without
    the library or the recordings. Matched by the title each was saved under (`on_air`)."""
    music = getattr(context, "music", None)
    titles = record.get("tracks") or {}
    if music is None or not titles:
        return {}
    try:
        by_title = {_flat(t.title): t.track_id for t in music.all_tracks()}
    except Exception:
        log.exception("Good News Radio couldn't look for its recordings")
        return {}
    return {key: by_title[_flat(title)] for key, title in titles.items() if _flat(title) in by_title}


def _story_card(s: dict, mine: set, marked: set) -> dict:
    """One story as the page shows it: its id, headline, topic, a summary in the outlet's own first sentences, how
    it's known (in words and as its tag), its caveats, where to read it, and whether this person follows it or
    marked it misleading."""
    sid = story_id(s)
    names = [SOURCE_BY_ID.get(x, (0, x))[1] for x in s["sources"]]
    reads = _reads(names, s["links"])
    return {"id": sid, "title": s["title"], "topic": s["topic"], "known": s["known"], "caveats": s["caveats"],
            "summary": _first_sentences(s["summary"], 3, 480) if s.get("summary") and s["summary"] != s["title"] else "",
            "how": _how_known(s), "published": s.get("published", ""), "reads": reads,
            "links": [r["href"] for r in reads], "outlets": sorted(set(names)),
            "followed": sid in mine, "misleading": sid in marked,
            **KNOWN_TAGS.get(s["known"], {"tag": s["known"], "tone": ""})}


def _followed_card(f: dict) -> dict:
    """One followed story as the page shows it: what it is, since when, where it was read, and the later reports
    found, newest first (each: headline, outlet, link, when, a summary, and whether it reads as good news)."""
    reports = [{"title": u.get("title", ""), "outlet": u.get("outlet", ""), "published": u.get("published", ""),
                "found": u.get("found", ""), "summary": u.get("summary", ""), "good": bool(u.get("good")),
                "href": u["link"] if str(u.get("link", "")).startswith(("https://", "http://")) else ""}
               for u in reversed(f.get("updates", []))]
    return {"id": f["id"], "title": f.get("title", ""), "topic": f.get("topic", ""), "since": f.get("since", ""),
            "reads": _reads(f.get("outlets", []), f.get("links", [])), "updates": reports}


def screen(context, now: Optional[datetime] = None) -> dict:
    """Good News Radio's web screen (web/news.html). Whether it's on; the latest episode (today's, or the newest of
    the last LATEST_DAYS days, with `today` and `fresh`, meaning today's or yesterday's, saying which): its stories
    (`_story_card`), the scripts by personality, the recordings to play (`tracks` by title, `audio` by library
    track id); the personalities and the one for this hour; the stories this person follows with what was found
    since; the outlets it reads; and whether today's episode is being made or can be started now."""
    now = now or datetime.now()
    today = now.date()
    record = latest(today)
    sources = []
    for _id, name, _url, kind in SOURCES:
        if not any(s["name"] == name for s in sources):
            sources.append({"name": name, "kind": kind})
    followed = following(context)
    out = {"on": is_on(context), "day": None, "today": False, "fresh": False, "made": "", "stories": [], "scripts": {},
           "tracks": {}, "audio": {}, "failed": [],
           "personalities": [{"key": k, "name": p["name"], "when": k} for k, p in PERSONALITIES.items()],
           "now": personality_for(now.hour), "following": [_followed_card(f) for f in followed], "sources": sources,
           "making": making(now), "can_make": can_make(context, now) is None}
    if record is None:
        return out
    mine, marked = {f["id"] for f in followed}, flagged_ids(context, record["day"])
    out.update({"day": record["day"], "today": record["day"] == today.isoformat(),
                "fresh": record["day"] >= (today - timedelta(days=1)).isoformat(), "made": record.get("made", ""),
                "stories": [_story_card(s, mine, marked) for s in record["stories"]], "scripts": record["scripts"],
                "tracks": record.get("tracks", {}), "audio": _audio(context, record),
                "failed": sorted({SOURCE_BY_ID.get(x, (0, x))[1] for x in record.get("failed", [])})})
    return out
