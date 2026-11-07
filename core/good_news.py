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
("that story was misleading"), by source; a source that keeps misleading opens
a task to drop it.
"""

from __future__ import annotations

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
AGENT = "MIA-GoodNewsRadio/1.0 (+offline-first personal assistant; one fetch a day)"

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


def make(day: Optional[date] = None, fetch: Callable[[str], str] = _fetch, flagged: tuple = ()) -> dict:
    """Today's stories, fetched, judged, checked against each other and kept, with every personality's script."""
    day = day or date.today()
    items, failed = fetch_all(fetch)
    since = (datetime.now(timezone.utc) - timedelta(days=KEEP_DAYS)).isoformat()
    fresh = [i for i in items if not i["published"] or i["published"] >= since]
    stories = pick(gather(fresh), flagged=flagged)
    record = {"day": day.isoformat(), "made": datetime.now().isoformat(timespec="seconds"), "items": len(items),
              "failed": failed, "stories": stories,
              "scripts": {k: script(stories, k) for k in PERSONALITIES}, "tracks": {}}
    _episodes().mkdir(parents=True, exist_ok=True)
    atomic_write_text(_episodes() / f"{day.isoformat()}.json", json.dumps(record, indent=1, ensure_ascii=False))
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


_ASK = re.compile(r"^(?:(?:what'?s|tell me|give me|any|got any|read me|let'?s hear)(?: the)? )?good news(?: radio)?"
                  r"(?: today| please| for me)?(?:,? (?:with )?(?:the )?(.+?))?[?.!]*$", re.IGNORECASE)
_MISLEADING = re.compile(r"^(?:that|the last|that last) (?:story|one) (?:was|is|seemed|sounds) (?:misleading|wrong|"
                         r"not true|overblown|hype)[.!]*$", re.IGNORECASE)
_TURN_ON = re.compile(r"^(?:turn on|switch on|start|enable) good news(?: radio)?[.!]*$", re.IGNORECASE)


def reply(context, text: str, now: Optional[datetime] = None) -> Optional[str]:
    """Talking to it: "what's the good news?", "good news, the calm one", "that story was misleading",
    "turn on good news radio". None when it isn't that."""
    from core import person_settings

    said = " ".join(str(text or "").split())
    now = now or datetime.now()
    if _TURN_ON.match(said):
        person_settings.put(context, SETTING, True)
        return ("Good News Radio is on. Once a day I'll read the public feeds of NASA, the NIH, the WHO, Nature, MIT "
                "News, Our World in Data, the BBC, NPR, The Conversation, ScienceDaily, Positive News, Reasons to be "
                "Cheerful, Anthropocene and Canary Media. Nothing about you is sent. Say \"what's the good news?\".")
    if _MISLEADING.match(said):
        found = heard(context)
        last = next((n for n in range(len(found) - 1, -1, -1) if found[n].get("stories")), None)
        folder = _folder(context)
        if last is None or folder is None:
            return None
        found[last].setdefault("misleading", []).append(found[last]["stories"][-1])  # the story just heard
        atomic_write_text(folder / "good_news_heard.json", json.dumps({"heard": found}, indent=1))
        return "Thanks: I'll weigh that source down, and drop it if it keeps happening."
    asked = _ASK.match(said)
    if not asked:
        return None
    if not is_on(context):
        return "Good News Radio is off. Say \"turn on good news radio\" and I'll read the news for you once a day."
    record = episode(now.date()) or episode(now.date() - timedelta(days=1))
    if record is None:
        return "Today's Good News Radio isn't ready yet; I put it together once a day. Ask me again in a bit."
    key = personality_for(now.hour, asked.group(1) or "")
    _note_heard(context, {"at": now.isoformat(timespec="seconds"), "day": record["day"], "personality": key,
                          "stories": [s["sources"][0] for s in record["stories"]]})
    track = record.get("tracks", {}).get(key)
    tail = f"\n\n(It's in {PERSONALITIES[key]['name']}'s voice in your music too: say \"play {track}\".)" if track else ""
    return record["scripts"][key] + tail


def due(context, now: Optional[datetime] = None) -> bool:
    """On for this person, on the PC, and today's episode not made yet (after 5 in the morning)."""
    from core import loops

    now = now or datetime.now()
    started = DATA / f"started-{now.date().isoformat()}"
    return is_on(context) and loops._has_repo() and now.hour >= 5 and episode(now.date()) is None and         not started.exists()


def launch() -> None:
    """Today's episode, made in a process of its own (the feeds and the voice take a minute)."""
    import os
    import subprocess
    import sys

    if os.environ.get("PYTEST_CURRENT_TEST"):
        return  # never from a test run: it goes online
    from core.dev_lab import _python

    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / f"started-{date.today().isoformat()}").write_text(datetime.now().isoformat(), encoding="utf-8")
    with open(DATA / "last_run.log", "w", encoding="utf-8") as out:
        subprocess.Popen([_python(), "-m", "tools.good_news", "make"], cwd=str(ROOT), stdout=out,
                         stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
                         | getattr(subprocess, "DETACHED_PROCESS", 0) if sys.platform == "win32" else 0)


def screen(context, now: Optional[datetime] = None) -> dict:
    """Good News Radio's web screen (web/news.html): today's stories with how each is known and its links, the
    scripts by personality, and whether it's on."""
    now = now or datetime.now()
    record = episode(now.date()) or episode(now.date() - timedelta(days=1))
    personalities = [{"key": k, "name": p["name"]} for k, p in PERSONALITIES.items()]
    if record is None:
        return {"on": is_on(context), "day": None, "stories": [], "personalities": personalities,
                "now": personality_for(now.hour)}
    stories = [{"title": s["title"], "topic": s["topic"], "known": s["known"], "caveats": s["caveats"],
                "links": s["links"], "outlets": sorted({SOURCE_BY_ID.get(x, (0, x))[1] for x in s["sources"]})}
               for s in record["stories"]]
    return {"on": is_on(context), "day": record["day"], "stories": stories, "scripts": record["scripts"],
            "tracks": record.get("tracks", {}), "personalities": personalities, "now": personality_for(now.hour)}
