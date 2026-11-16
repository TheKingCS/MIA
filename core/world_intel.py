"""
core.world_intel
==================

World Intelligence's store and its watch runs (DEC-0170, DEC-0171; the plan is
`docs/mia_os/MIA_OS_WORLD_INTELLIGENCE_PROPOSAL.md`, phase W1).

**A watch** (`Watch`) is something to keep an eye on: a name, the person's own words to look for (DEC-0122: only
their words go out), the areas and sources it reads (`core/world_sources.py`), how often, a price ceiling for
listings, who made it (the person, or MIA from their records, later phases), and why. **A find** (`Discovery`) is one
thing a watch turned up, kept once however often it's seen: its title, link and summary as the source gave them, the
source's name (every find names its source, always), when it was published, first and last seen, which watches found
it, its status (new, saved, not for me, gone), when it was offered, and the reasons it scored.

**Running** (`run_watch`, pure apart from the fetchers it's given): each source the watch reads is fetched through
its kind's adapter; items whose title and summary hold every word of one of the watch's phrases are kept, unless
they were published more than two weeks ago (a first run would otherwise bring up a feed's whole backlog: twenty old
releases at once, found on the first real run, 2026-11-15). A source
that refuses (`SourceRefused`) is recorded on the watch and not read again until the person looks. Fetching happens
on one worker thread (`Runner`), scoped to this module (CLAUDE.md: a network task is the case that earns a thread):
the thread only reads the web and returns raw items; the store is changed only on the job's own thread when it
collects them (`WorldBook.ingest`).

**Watches MIA makes herself** (`sync_own_watches`, W1b; Zac, 2026-11-15: "it should also automate watching for
things not just ones I set"): once a day, every open goal, live project, active mission, the homestead plan's next
step and goal, and each machine owned (its maker and model) gets a watch of its own, marked as hers, with the record
it serves as its reason, looking for the meaningful words of the record's name (`_own_words`). They read whole public feeds and match on the PC, so no word of them leaves it (no search).
One stops by itself when its record does (finished, removed); one the person stops is never made again for that
record (`declined`). At most `OWN_MAX` at a time, strongest records first.

**Sources judged** (`source_stats`, the `world.sources` loop in core/loops.py): for each source over the last 30
days, how many finds it gave, how many were saved, set aside or are still new. One that gave eight or more, none
saved and four or more set aside is suggested for muting (`mute_suggestions`); a muted source (`muted`, the action
`world_source.mute`) isn't read by any watch until it's unmuted.

**Telling** (`offers`): the new finds best first, each a candidate for the communication gate under the topic
`world_find`, its message naming the source. The gate paces them (four a day to start, learned from what the person
does with them: saving or researching a find counts as engaging, "not for me" as passing, DEC-0171).

**Scoring** (`score`) is explained, point by point: how many of the watch's words it holds, how recent it is, and
(W2, `core/relevance.py`) which of the person's own records it fits: their goals, projects, missions, the homestead
plan's next step, what they're learning, what they own. Each fit is a reason naming the record, and its `kind:id` is
kept on the find (`refs`) for links. Finds not yet offered are re-ranked whenever the records change (`rescore`).

Off until the person switches it on (`world.on`, their own setting; DEC-0053: switching it on is the asking).
`WorldBook` keeps `world_intel.json` in their folder, sealed at rest (what someone watches for says a lot about them),
written through atomic_write_text so "undo that" restores it.
"""

from __future__ import annotations

from core.data_root import DATA_DIR

import json
import re
import threading
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from core.at_rest import open_text
from core.atomic_write import atomic_write_text
from core.data_recovery import notify_data_corruption
from core.logger import get_logger

log = get_logger(__name__)

_DATA_DIR = DATA_DIR
_FILE = "world_intel.json"
TOPIC = "world_find"  # the gate's kind for World Intelligence's finds (core/communication_gate.TOPIC_DAILY)
STATUSES = ("new", "saved", "not_for_me", "gone")
KEEP_DAYS = 90  # a find nobody saved is let go after this long
PER_RUN = 20  # at most this many new finds a watch keeps from one run
MAX_AGE_DAYS = 14  # an item published longer ago than this is old news: a first run doesn't bring up a backlog
MIN_HOURS = 1  # no watch is read more often than this
OWN_MAX = 12  # at most this many watches MIA made herself at a time
OWN_HOURS = 12  # how often hers look
_TRACKING = re.compile(r"^(utm_|fbclid$|gclid$|mc_|ref$|ref_src$)")
_WORD = re.compile(r"[a-z0-9][a-z0-9+.#-]*")


def is_on(context) -> bool:
    """Whether this person has switched World Intelligence on (their own setting `world.on`, off by default)."""
    from core import person_settings

    try:
        return bool(person_settings.get(context, "world.on", False))
    except Exception:
        return False


# ------------------------------------------------------------------ records


@dataclass
class Watch:
    """Something to keep an eye on (see the module's opening)."""
    watch_id: str
    name: str
    words: str  # the person's own words; phrases separated by commas ("greenhouse panels, polycarbonate sheets")
    areas: list = field(default_factory=list)  # core.world_sources.AREAS
    sources: list = field(default_factory=list)  # source ids; empty: every feed in its areas
    search: bool = False  # also search the person's own SearXNG with these words
    every_hours: int = 6
    max_price: float = 0.0
    made_by: str = "person"  # person | mia
    reason: str = ""  # why it exists, in a sentence (MIA's own watches say which record)
    refs: list = field(default_factory=list)  # kind:id records it serves (links)
    paused: bool = False
    created: str = ""
    last_run: str = ""
    refused: list = field(default_factory=list)  # sources that turned the reader away, waiting for the person
    runs: int = 0
    found: int = 0


@dataclass
class Discovery:
    """One thing a watch found (see the module's opening), with the person's records it fits (`refs`, `fits`)."""
    discovery_id: str
    key: str  # what makes it the same thing again (dedupe_key)
    title: str
    link: str
    source_id: str
    source_name: str  # shown on every find, everywhere
    summary: str = ""
    site: str = ""  # for a search result: the site it's on
    published: str = ""
    found_at: str = ""
    last_seen: str = ""
    watch_ids: list = field(default_factory=list)
    status: str = "new"
    offered_at: str = ""
    score: float = 0.0
    why: list = field(default_factory=list)
    refs: list = field(default_factory=list)  # kind:id of the person's records it fits (core/relevance.py)
    fits: str = ""  # "fits your plans" / "may fit your plans" / "" (only matched a watch's words)


# ------------------------------------------------------------------ pure logic


def phrases(words: str) -> list[list[str]]:
    """Pure logic. A watch's words as phrases, each a list of lowercase words ("greenhouse panels, PVC" ->
    [["greenhouse", "panels"], ["pvc"]])."""
    out = []
    for part in str(words or "").split(","):
        found = _WORD.findall(part.lower())
        if found:
            out.append(found)
    return out


def matches(watch: Watch, item: dict) -> list[str]:
    """Pure logic. The watch's phrases this item holds every word of, in its title and summary (empty: no match)."""
    text = set(_WORD.findall(f"{item.get('title', '')} {item.get('summary', '')}".lower()))
    stems = {w.rstrip("s") for w in text}
    hit = []
    for phrase in phrases(watch.words):
        if all(w in text or w.rstrip("s") in stems for w in phrase):
            hit.append(" ".join(phrase))
    return hit


def dedupe_key(item: dict) -> str:
    """Pure logic. What makes two items the same find: the link without tracking parameters, its fragment or a
    trailing slash, lowercased host; the title when there's no link."""
    link = str(item.get("link") or "").strip()
    if not link:
        return "title:" + " ".join(_WORD.findall(str(item.get("title") or "").lower()))
    parts = urlparse(link)
    query = urlencode([(k, v) for k, v in parse_qsl(parts.query) if not _TRACKING.match(k.lower())])
    return urlunparse((parts.scheme.lower(), parts.netloc.lower().removeprefix("www."), parts.path.rstrip("/"), "",
                       query, ""))


def score(watch: Watch, item: dict, hits: list[str], now: datetime) -> tuple[float, list[str]]:
    """Pure logic. The watch's part of the score and its reasons: each phrase matched counts, and a recent item more
    (published in the last day, week). The records' part is added by `_relevant`."""
    points = 10.0 * len(hits)
    why = [f"matches your watch “{watch.name}”: {', '.join(hits)}"]
    published = _parse(item.get("published", ""))
    if published is not None:
        age = now - published.replace(tzinfo=None)
        if age <= timedelta(days=1):
            points += 5
            why.append("published in the last day")
        elif age <= timedelta(days=7):
            points += 2
    return points, why


def source_stats(discoveries: list, now: datetime, days: int = 30) -> dict:
    """Pure logic. For each source, its finds found in the last `days`: {source_id: {name, finds, saved, not_for_me,
    new}}."""
    since = (now - timedelta(days=days)).isoformat()
    out: dict = {}
    for d in discoveries:
        if d.found_at < since:
            continue
        row = out.setdefault(d.source_id, {"name": d.source_name, "finds": 0, "saved": 0, "not_for_me": 0, "new": 0})
        row["finds"] += 1
        if d.status in ("saved", "not_for_me", "new"):
            row[d.status] += 1
    return out


def mute_suggestions(stats: dict, muted=()) -> list[str]:
    """Pure logic. The sources worth muting: eight or more finds, none saved, four or more set aside; not muted yet."""
    return sorted(s for s, r in stats.items()
                  if s not in muted and r["finds"] >= 8 and r["saved"] == 0 and r["not_for_me"] >= 4)


def run_watch(watch: Watch, now: datetime, fetchers: dict, sources: Optional[list] = None, skip=()) -> dict:
    """One watch's run: each of its sources read through its kind's fetcher, the items it matches kept (at most
    PER_RUN; none published more than MAX_AGE_DAYS ago); sources in `skip` (muted) aren't read. Returns {watch_id, at, items: [(item, hits)], refused: [source ids], failed: [source ids]}. A fetcher
    takes (source, watch) and returns raw items; `fetchers` maps kind -> fetcher."""
    from core import world_sources

    chosen = sources if sources is not None else _sources_of(watch)
    items, refused, failed = [], [], []
    for src in chosen:
        fetch = fetchers.get(src.kind)
        if fetch is None or src.source_id in watch.refused or src.source_id in skip:
            continue
        try:
            raw = fetch(src, watch)
        except world_sources.SourceRefused:
            refused.append(src.source_id)
            continue
        except Exception as problem:  # one source down never stops the rest
            log.info("World Intelligence: %s didn't answer (%s)", src.source_id, problem)
            failed.append(src.source_id)
            continue
        for item in raw:
            published = _parse(item.get("published", ""))
            if published is not None and now - published > timedelta(days=MAX_AGE_DAYS):
                continue
            hits = matches(watch, item)
            if hits:
                items.append((item, hits))
    return {"watch_id": watch.watch_id, "at": now.isoformat(timespec="seconds"), "items": items[:PER_RUN],
            "refused": refused, "failed": failed}


def run_watches(watches: list[Watch], now: datetime, fetchers: dict, skip=()) -> list[dict]:
    """Several watches' runs with each feed fetched once and shared between every watch that reads it (a search is
    per watch: its words differ); sources in `skip` (muted) aren't read. Returns one result per watch, as run_watch
    does."""
    cache: dict = {}

    def shared(src, watch):
        """A feed's items, fetched the first time any watch asks; a refusal or failure is remembered and repeated."""
        if src.kind == "search":
            return fetchers["search"](src, watch)
        if src.source_id not in cache:
            try:
                cache[src.source_id] = ("ok", fetchers[src.kind](src, watch))
            except Exception as problem:  # noqa: BLE001 - re-raised for each watch below, as it would be alone
                cache[src.source_id] = ("err", problem)
        kind, value = cache[src.source_id]
        if kind == "err":
            raise value
        return value

    wrapped = {kind: shared for kind in fetchers}
    return [run_watch(w, now, wrapped, skip=skip) for w in watches]


def _sources_of(watch: Watch) -> list:
    """The sources a watch reads: the ones it names, else every feed in its areas; plus the search when it asks."""
    from core import world_sources

    chosen = [world_sources.source(s) for s in watch.sources] if watch.sources else world_sources.for_areas(watch.areas)
    chosen = [s for s in chosen if s is not None and s.kind != "search"]
    if watch.search:
        chosen.append(world_sources.SEARCH)
    return chosen


def due(watch: Watch, now: datetime) -> bool:
    """Pure logic. Whether a watch should run now: not paused, and its hours have passed since its last run."""
    if watch.paused:
        return False
    last = _parse(watch.last_run)
    return last is None or now - last >= timedelta(hours=max(MIN_HOURS, int(watch.every_hours or 6)))


def _parse(iso: str) -> Optional[datetime]:
    """A datetime from ISO text (or an RFC date), naive, or None."""
    if not iso:
        return None
    try:
        when = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
    except ValueError:
        return None
    if when.tzinfo is not None:
        when = when.astimezone().replace(tzinfo=None)
    return when


# ------------------------------------------------------------------ the store


class WorldBook:
    """The person's watches and finds (world_intel.json in their folder, sealed, written atomically so undo can
    restore it), under the epistemic contract (EPISTEMIC)."""

    # The epistemic contract (DEC-0173, G3): where each find came from, when it was read, how it's known, and when
    # it was last seen. tests/test_living_system.py checks every new store declares this.
    EPISTEMIC = {"record": Discovery, "source": "source_name", "at": "found_at", "how": "observed",
                 "checked": "last_seen"}

    def __init__(self, context, data_dir: Optional[Path] = None) -> None:
        """Points at the person's file (data/ by default) and loads it."""
        self.context = context
        self.data_dir = Path(data_dir) if data_dir is not None else _DATA_DIR
        self._file = self.data_dir / _FILE
        self._load()

    def _load(self) -> None:
        """Reads watches, finds, the records whose own watch the person stopped, the muted sources and the day MIA last
        made hers,
        keeping only known fields; an unreadable file is logged, reported and starts empty (a sealed one that won't
        open is copied aside first)."""
        self.watches: list[Watch] = []
        self.discoveries: list[Discovery] = []
        self.declined: list[str] = []  # records whose watch the person stopped: never made again
        self.muted: list[str] = []  # sources no watch reads (world_source.mute)
        self.own_synced = ""  # the day MIA last made her own watches
        if not self._file.exists():
            return
        try:
            raw = json.loads(open_text(self._file))
            pick = lambda cls, d: cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})  # noqa: E731
            self.watches = [pick(Watch, d) for d in raw.get("watches", [])]
            self.discoveries = [pick(Discovery, d) for d in raw.get("discoveries", [])]
            self.declined = list(raw.get("declined", []))
            self.muted = list(raw.get("muted", []))
            self.own_synced = str(raw.get("own_synced", ""))
        except (ValueError, OSError, TypeError, AttributeError):
            log.exception("world_intel.json unreadable — starting empty.")
            notify_data_corruption(self.context, _FILE)

    def reload(self) -> None:
        """Reads the file again (after undo restored it)."""
        self._load()

    def _save(self) -> None:
        """Writes watches, finds, the declined records, the muted sources and the last day MIA made hers, atomically."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._file, json.dumps({"watches": [asdict(w) for w in self.watches],
                                                  "discoveries": [asdict(d) for d in self.discoveries],
                                                  "declined": self.declined, "own_synced": self.own_synced,
                                                  "muted": self.muted}, indent=2))

    # ---------------------------------------------------------------- watches

    def get_watch(self, watch_id: str) -> Optional[Watch]:
        """The watch with this id, or None."""
        return next((w for w in self.watches if w.watch_id == watch_id), None)

    def find_watch(self, words: str) -> Optional[Watch]:
        """The watch a few words name: its name or words exactly, else the only one holding every word."""
        wanted = " ".join(_WORD.findall(str(words or "").lower()))
        if not wanted:
            return None
        exact = [w for w in self.watches if wanted in (" ".join(_WORD.findall(w.name.lower())),
                                                       " ".join(_WORD.findall(w.words.lower())))]
        if len(exact) == 1:
            return exact[0]
        some = [w for w in self.watches
                if set(wanted.split()) <= set(_WORD.findall(f"{w.name} {w.words}".lower()))]
        return some[0] if len(some) == 1 else None

    def add_watch(self, name: str, words: str, areas=(), sources=(), search: bool = False, every_hours: int = 6,
                  max_price: float = 0.0, made_by: str = "person", reason: str = "", refs=()) -> Watch:
        """Adds a watch; ValueError without words to look for, or for an area or source that isn't known."""
        from core import world_sources

        words = " ".join(str(words or "").split())
        if not phrases(words):
            raise ValueError("What should I watch for?")
        bad = [a for a in areas if a not in world_sources.AREAS] + [s for s in sources if not world_sources.source(s)]
        if bad:
            raise ValueError(f"I don't know {', '.join(bad)}.")
        watch = Watch(uuid.uuid4().hex[:8], " ".join(str(name or words).split())[:80], words, list(areas),
                      list(sources), bool(search), max(MIN_HOURS, int(every_hours or 6)), float(max_price or 0),
                      made_by, reason, list(refs), created=datetime.now().isoformat(timespec="seconds"))
        self.watches.append(watch)
        self._save()
        return watch

    def set_paused(self, watch_id: str, paused: bool) -> Watch:
        """Pauses or resumes a watch; ValueError when it isn't here."""
        watch = self.get_watch(watch_id)
        if watch is None:
            raise ValueError("That watch isn't here any more.")
        watch.paused = bool(paused)
        if not paused:
            watch.refused = []  # the person looked: refused sources may be tried again
        self._save()
        return watch

    def remove_watch(self, watch_id: str) -> Watch:
        """Removes a watch (its finds stay, until they're let go); one MIA made is never made again for its record.
        ValueError when it isn't here."""
        watch = self.get_watch(watch_id)
        if watch is None:
            raise ValueError("That watch isn't here any more.")
        self.watches = [w for w in self.watches if w.watch_id != watch_id]
        if watch.made_by == "mia":
            self.declined = sorted(set(self.declined) | set(watch.refs))
        self._save()
        return watch

    def sync_own_watches(self, anchors: list, now: Optional[datetime] = None) -> tuple[list[Watch], list[Watch]]:
        """MIA's own watches made to match the person's records now (see the module's opening): one for each anchor
        with a name that has none yet and wasn't declined, strongest first, up to OWN_MAX; hers whose record is gone
        removed. Returns (made, removed); saves when anything changed, and notes the day."""
        now = now or datetime.now()
        live = {a.ref: a for a in anchors if a.name and _own_words(a.name) and a.ref not in self.declined}
        removed = [w for w in self.watches if w.made_by == "mia" and not set(w.refs) & set(live)]
        self.watches = [w for w in self.watches if w not in removed]
        covered = {r for w in self.watches for r in w.refs}
        mine = sum(1 for w in self.watches if w.made_by == "mia")
        made = []
        for a in sorted(live.values(), key=lambda a: -a.weight):
            if a.ref in covered or mine >= OWN_MAX:
                continue
            words = _own_words(a.name)
            watch = Watch(uuid.uuid4().hex[:8], a.name[:80], words, [], [], False, OWN_HOURS, 0.0, "mia",
                          f"For {a.label}.", [a.ref], created=now.isoformat(timespec="seconds"))
            self.watches.append(watch)
            made.append(watch)
            mine += 1
        self.own_synced = now.date().isoformat()
        self._save()
        return made, removed

    def set_muted(self, source_id: str, muted: bool) -> None:
        """Mutes a source (no watch reads it) or unmutes it; ValueError for a source that isn't known."""
        from core import world_sources

        if world_sources.source(source_id) is None:
            raise ValueError("That isn't one of my sources.")
        wanted = set(self.muted)
        (wanted.add if muted else wanted.discard)(source_id)
        self.muted = sorted(wanted)
        self._save()

    def due_watches(self, now: datetime) -> list[Watch]:
        """The watches to run now."""
        return [w for w in self.watches if due(w, now)]

    # ---------------------------------------------------------------- finds

    def get(self, discovery_id: str) -> Optional[Discovery]:
        """The find with this id, or None."""
        return next((d for d in self.discoveries if d.discovery_id == discovery_id), None)

    def set_status(self, discovery_id: str, status: str) -> Discovery:
        """Marks a find saved, not for me, gone or new again; ValueError for an unknown find or status."""
        found = self.get(discovery_id)
        if found is None:
            raise ValueError("That find isn't here any more.")
        if status not in STATUSES:
            raise ValueError(f"A find is one of: {', '.join(STATUSES)}.")
        found.status = status
        self._save()
        return found

    def ingest(self, results: list[dict], now: Optional[datetime] = None, anchors: Optional[list] = None) -> list[Discovery]:
        """Takes runs' results into the store: each matched item a find (one per dedupe key, the watch added to an
        existing one; its link kept only when it's a web address), scored against the person's records when `anchors` are given (core/relevance.py), the watch's
        last run, counts and refused sources recorded, old unsaved finds let go. Returns the finds that are new."""
        from core import world_sources
        from core.good_news import web_link

        now = now or datetime.now()
        by_key = {d.key: d for d in self.discoveries}
        new = []
        for result in results:
            watch = self.get_watch(result.get("watch_id", ""))
            if watch is None:
                continue
            watch.last_run = result.get("at") or now.isoformat(timespec="seconds")
            watch.runs += 1
            watch.refused = sorted(set(watch.refused) | set(result.get("refused", [])))
            for item, hits in result.get("items", []):
                item = dict(item, link=web_link(item.get("link", "")))  # only ever a web address (outside text)
                key = dedupe_key(item)
                seen = by_key.get(key)
                if seen is not None:
                    seen.last_seen = now.isoformat(timespec="seconds")
                    if watch.watch_id not in seen.watch_ids:
                        seen.watch_ids.append(watch.watch_id)
                    continue
                src = world_sources.source(item.get("source", ""))
                points, why = score(watch, item, hits, now)
                points, why, refs, fits = _relevant(points, why, item, anchors or [])
                find = Discovery(uuid.uuid4().hex[:10], key, str(item.get("title", ""))[:300],
                                 str(item.get("link", "")), str(item.get("source", "")),
                                 src.name if src is not None else str(item.get("source", "")),
                                 str(item.get("summary", ""))[:600], str(item.get("site", "")),
                                 str(item.get("published", "")), now.isoformat(timespec="seconds"),
                                 now.isoformat(timespec="seconds"), [watch.watch_id], score=points, why=why,
                                 refs=refs, fits=fits)
                self.discoveries.append(find)
                by_key[key] = find
                new.append(find)
                watch.found += 1
        cutoff = (now - timedelta(days=KEEP_DAYS)).isoformat()
        self.discoveries = [d for d in self.discoveries if d.status == "saved" or d.last_seen >= cutoff]
        self._save()
        return new

    def rescore(self, anchors: list, now: Optional[datetime] = None) -> int:
        """Re-ranks the finds not offered yet against the person's records as they are now (a new goal pulls, a
        finished project stops). Returns how many changed; saves only when one did."""
        changed = 0
        now = now or datetime.now()
        names = {w.watch_id: w for w in self.watches}
        for d in self.discoveries:
            if d.status != "new" or d.offered_at:
                continue
            watch = next((names[w] for w in d.watch_ids if w in names), None)
            item = {"title": d.title, "summary": d.summary, "published": d.published}
            base, why = score(watch, item, matches(watch, item), now) if watch else (0.0, [])
            points, why, refs, fits = _relevant(base, why, item, anchors)
            if (points, refs) != (d.score, d.refs):
                d.score, d.why, d.refs, d.fits = points, why, refs, fits
                changed += 1
        if changed:
            self._save()
        return changed

    def offers(self, now: Optional[datetime] = None, limit: int = 8) -> list[Discovery]:
        """The new finds not offered yet, best first (the gate decides how many go out)."""
        fresh = [d for d in self.discoveries if d.status == "new" and not d.offered_at]
        return sorted(fresh, key=lambda d: (-d.score, d.found_at))[:limit]

    def mark_offered(self, discovery_ids, now: Optional[datetime] = None) -> None:
        """Notes that these finds were offered to the gate (whatever it decided), so none is offered twice."""
        at = (now or datetime.now()).isoformat(timespec="seconds")
        wanted = set(discovery_ids)
        for d in self.discoveries:
            if d.discovery_id in wanted:
                d.offered_at = at
        if wanted:
            self._save()


def _own_words(name: str) -> str:
    """Pure logic. What a watch MIA makes for a record looks for: the record's name without its common words ("Build
    the greenhouse by spring" -> "greenhouse spring"), since a find must hold every word and none says "the ... by";
    "" when nothing significant is left."""
    from core import relevance

    kept = [w for w in _WORD.findall(str(name or "").lower()) if relevance.words_of(w)]
    return " ".join(dict.fromkeys(kept))


def _relevant(points: float, why: list, item: dict, anchors: list) -> tuple[float, list, list, str]:
    """The watch's points and reasons plus the records' (core/relevance.py): (points, reasons, refs, fits)."""
    from core import relevance

    extra, reasons, refs = relevance.relevance(f"{item.get('title', '')} {item.get('summary', '')}", anchors)
    return points + extra, list(why) + reasons, refs, relevance.describe(extra, reasons) or ""


def _anchors(context) -> list:
    """The person's anchors (core/relevance.anchors), or [] when they can't be read."""
    from core import relevance

    try:
        return relevance.anchors(context)
    except Exception:  # noqa: BLE001 - relevance never stops a run
        log.exception("World Intelligence: couldn't read the person's records for relevance")
        return []


def candidate_for(find: Discovery):
    """The gate's candidate for one find: its title, where it's from (the source always named) and, first, the record
    it fits when it fits one."""
    from core.communication_gate import TIMELY, Candidate

    where = find.source_name + (f" ({find.site})" if find.site else "")
    reason = next((w for w in find.why if w.startswith("fits ")), find.why[0] if find.why else "")
    return Candidate(topic=TOPIC, title=f"Found: {find.title}"[:120],
                     message=f"From {where}. {reason[:1].upper() + reason[1:] if reason else ''}".strip(),
                     urgency=TIMELY,
                     source="world", fingerprint=find.key)


# ------------------------------------------------------------------ the worker thread


class Runner:
    """Runs due watches on one worker thread that only reads the web; `collect()` hands back the results on the
    caller's thread, where the store is changed."""

    def __init__(self) -> None:
        """Nothing running."""
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._done: Optional[list] = None

    def busy(self) -> bool:
        """Whether a run is still going."""
        return self._thread is not None and self._thread.is_alive()

    def start(self, watches: list[Watch], now: datetime, fetchers: dict, skip=()) -> bool:
        """Starts a run over copies of these watches (each feed fetched once for all of them: run_watches), muted
        sources (`skip`) left out; False when one is already going or there's nothing to run."""
        if self.busy() or not watches:
            return False
        copies = [Watch(**asdict(w)) for w in watches]

        def work() -> None:
            """The thread: every watch's run, each feed fetched once for all of them; results kept for collect()."""
            try:
                results = run_watches(copies, now, fetchers, skip=frozenset(skip))
            except Exception:
                log.exception("World Intelligence: the run failed")
                results = []
            with self._lock:
                self._done = results

        self._thread = threading.Thread(target=work, name="world-watch", daemon=True)
        self._thread.start()
        return True

    def collect(self) -> list:
        """The finished run's results (once), or [] while it runs or when there's none."""
        with self._lock:
            done, self._done = self._done, None
        return done or []


_runners: dict = {}


def runner_for(book: WorldBook) -> Runner:
    """The one Runner for a person's folder."""
    return _runners.setdefault(str(book.data_dir), Runner())


def live_fetchers(context) -> dict:
    """The adapters wired to the real web: feeds through world_sources.get, search through the person's SearXNG."""
    from core import world_sources

    return {"feed": lambda src, watch: world_sources.fetch_feed(src, watch),
            "search": lambda src, watch: world_sources.fetch_search(src, watch, context=context)}


def tick(context, now: Optional[datetime] = None, fetchers: Optional[dict] = None) -> list[Discovery]:
    """The job (core/background_jobs.py, every 10 minutes): when it's on, collect a finished run into the store (scored
    against the person's records), re-rank what's waiting, make MIA's own watches once a day, and offer the best new
    finds through the gate; muted sources are left out of the run; then start the due watches on the worker thread. Returns the new finds
    collected this time."""
    import os

    book = getattr(context, "world_intel", None)
    if book is None or not is_on(context):
        return []
    now = now or datetime.now()
    runner = runner_for(book)
    results = runner.collect()
    anchors = _anchors(context)
    new = book.ingest(results, now, anchors) if results else []
    book.rescore(anchors, now)
    if book.own_synced != now.date().isoformat():
        book.sync_own_watches(anchors, now)
    offers = book.offers(now)
    gate = getattr(context, "communication", None)
    if offers and gate is not None:
        gate.offer_batch([candidate_for(d) for d in offers], now)
        book.mark_offered([d.discovery_id for d in offers], now)
    if fetchers is None and os.environ.get("PYTEST_CURRENT_TEST"):
        return new  # never online from a test run
    runner.start(book.due_watches(now), now, fetchers or live_fetchers(context), skip=book.muted)
    return new
