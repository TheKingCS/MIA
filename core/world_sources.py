"""
core.world_sources
====================

Where World Intelligence reads (DEC-0170, `docs/mia_os/MIA_OS_WORLD_INTELLIGENCE_PROPOSAL.md` sections 5 and 5b):
the source adapters and the starting catalog.

**A source** (`Source`) is one place MIA reads: its id, the name every find shows (Zac, 2026-11-15: "It should just
always list the source"), its kind (`feed`, `search`; `api`, `browser_skill` and `capture` come in later phases),
the areas it covers, and how often it may be read. Each kind has one adapter function, `fetch(source, watch)`, that
returns raw items: `{source, title, link, summary, published}`. A new source is a row in `CATALOG`; a new kind is a
new adapter in `ADAPTERS`. Nothing else changes (the proposal's first acceptance criterion).

**The starting catalog** (`CATALOG`) is the feeds Claude checked from the PC on 2026-11-15: each answered with a feed
whose newest item was recent. It holds no one's personal places; those live in the person's own data.

**Reading:** the feed reader is Good News Radio's (`core.good_news.parse_feed`, one parser for every feed in MIA),
fetched with `certifi`'s certificates (on the PC's Python, arXiv and Grants.gov fail certificate checks without
them), MIA's own user agent, a 20-second timeout and at most 3 MB. A search watch uses the person's own SearXNG
(`core.online_lookup.search`, DEC-0053's scrub). A source that refuses (an HTTP 403, a block page) raises
`SourceRefused`, which the run records so the source waits for the person instead of being retried.
"""

from __future__ import annotations

import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Callable, Optional

from core.logger import get_logger

log = get_logger(__name__)

AGENT = "MIA World Intelligence (a personal assistant; one reader, a few times a day)"
MAX_BYTES = 3_000_000
TIMEOUT = 20

AREAS = ("self", "ai", "tech", "smart_home", "homestead", "energy", "grants", "money", "science", "news", "listings")
AREA_NAMES = {"self": "MIA's own software", "ai": "AI and local models", "tech": "Linux, hardware and boards",
              "smart_home": "Smart home", "homestead": "Homestead, farming and building", "energy": "Energy and solar",
              "grants": "Grants, programs and rules", "money": "Money and property", "science": "Science",
              "news": "General news", "listings": "Auctions and listings"}


class SourceRefused(RuntimeError):
    """A source turned the reader away (a 403, a block or CAPTCHA page): it waits for the person, never retried."""


@dataclass(frozen=True)
class Source:
    """One place World Intelligence reads: id, the name shown on every find, kind, address, areas, and how many hours
    at least between reads."""
    source_id: str
    name: str
    kind: str  # feed | search
    url: str
    areas: tuple
    every_hours: int = 6


def _feed(source_id: str, name: str, url: str, areas: tuple, every_hours: int = 6) -> Source:
    """A feed row for the catalog."""
    return Source(source_id, name, "feed", url, areas, every_hours)


def _releases(source_id: str, name: str, repo: str) -> Source:
    """A GitHub repository's releases feed (each repository publishes one at /releases.atom)."""
    return _feed(source_id, f"{name} releases", f"https://github.com/{repo}/releases.atom", ("self",), 12)


# Checked from the PC on 2026-11-15 (proposal section 5b): each answered with a recent feed.
CATALOG: tuple[Source, ...] = (
    _releases("gh_ollama", "Ollama", "ollama/ollama"),
    _releases("gh_llamacpp", "llama.cpp", "ggml-org/llama.cpp"),
    _releases("gh_playwright", "Playwright for Python", "microsoft/playwright-python"),
    _releases("gh_home_assistant", "Home Assistant", "home-assistant/core"),
    _feed("hugging_face", "Hugging Face blog", "https://huggingface.co/blog/feed.xml", ("ai",)),
    _feed("openai", "OpenAI news", "https://openai.com/news/rss.xml", ("ai",)),
    _feed("mistral", "Mistral news", "https://mistral.ai/news/rss", ("ai",)),
    _feed("simon_willison", "Simon Willison's weblog", "https://simonwillison.net/atom/everything/", ("ai",)),
    _feed("hn_local_llm", "Hacker News (local LLMs)", "https://hnrss.org/newest?q=local+LLM&points=50", ("ai",)),
    _feed("arxiv_ai", "arXiv cs.AI", "https://rss.arxiv.org/rss/cs.AI", ("ai", "science"), 24),
    _feed("arxiv_cl", "arXiv cs.CL", "https://rss.arxiv.org/rss/cs.CL", ("ai", "science"), 24),
    _feed("phoronix", "Phoronix", "https://www.phoronix.com/rss.php", ("tech",)),
    _feed("lwn", "LWN", "https://lwn.net/headlines/newrss", ("tech",)),
    _feed("fedora_magazine", "Fedora Magazine", "https://fedoramagazine.org/feed/", ("tech",), 24),
    _feed("raspberry_pi", "Raspberry Pi news", "https://www.raspberrypi.com/news/feed/", ("tech",)),
    _feed("cnx_software", "CNX Software", "https://www.cnx-software.com/feed/", ("tech",)),
    _feed("toms_hardware", "Tom's Hardware", "https://www.tomshardware.com/feeds/all", ("tech",)),
    _feed("hackaday", "Hackaday", "https://hackaday.com/blog/feed/", ("tech", "homestead")),
    _feed("home_assistant", "Home Assistant blog", "https://www.home-assistant.io/atom.xml", ("smart_home",), 24),
    _feed("usda_ars", "USDA Agricultural Research Service", "https://www.ars.usda.gov/news-events/news/rss/",
          ("homestead", "science"), 24),
    _feed("modern_farmer", "Modern Farmer", "https://modernfarmer.com/feed/", ("homestead",)),
    _feed("mother_earth_news", "Mother Earth News", "https://www.motherearthnews.com/feed/", ("homestead",)),
    _feed("hobby_farms", "Hobby Farms", "https://www.hobbyfarms.com/feed/", ("homestead",)),
    _feed("sciencedaily_ag", "ScienceDaily: agriculture and food",
          "https://www.sciencedaily.com/rss/plants_animals/agriculture_and_food.xml", ("homestead", "science")),
    _feed("fine_homebuilding", "Fine Homebuilding", "https://www.finehomebuilding.com/feed", ("homestead",), 24),
    _feed("family_handyman", "Family Handyman", "https://www.familyhandyman.com/feed/", ("homestead",), 24),
    _feed("make", "Make:", "https://makezine.com/feed/", ("homestead", "tech"), 24),
    _feed("pv_magazine", "pv magazine USA", "https://pv-magazine-usa.com/feed/", ("energy",)),
    _feed("electrek", "Electrek", "https://electrek.co/feed/", ("energy",)),
    _feed("canary_media", "Canary Media", "https://www.canarymedia.com/rss.rss", ("energy",)),
    _feed("cleantechnica", "CleanTechnica", "https://cleantechnica.com/feed/", ("energy",)),
    _feed("grants_by_agency", "Grants.gov (new, by agency)", "https://www.grants.gov/rss/GG_NewOppByAgency.xml",
          ("grants",), 24),
    _feed("federal_register_usda", "Federal Register (USDA)",
          "https://www.federalregister.gov/api/v1/documents.rss?conditions[agencies][]=agriculture-department",
          ("grants", "homestead"), 24),
    _feed("sba", "SBA news", "https://www.sba.gov/rss", ("grants", "money"), 24),
    _feed("calculated_risk", "Calculated Risk (housing)", "https://www.calculatedriskblog.com/feeds/posts/default",
          ("money",), 24),
    _feed("sciencedaily", "ScienceDaily", "https://www.sciencedaily.com/rss/top/science.xml", ("science",)),
    _feed("phys_org", "Phys.org", "https://phys.org/rss-feed/", ("science",)),
    _feed("npr", "NPR", "https://feeds.npr.org/1001/rss.xml", ("news",), 3),
    _feed("bbc_world", "BBC World", "https://feeds.bbci.co.uk/news/world/rss.xml", ("news",), 3),
    _feed("ars_technica", "Ars Technica", "https://feeds.arstechnica.com/arstechnica/index", ("news", "tech")),
    _feed("the_verge", "The Verge", "https://www.theverge.com/rss/index.xml", ("news", "tech")),
    _feed("bring_a_trailer", "Bring a Trailer (auctions)", "https://bringatrailer.com/feed/", ("listings",)),
)
SEARCH = Source("searxng", "Your search engine (SearXNG)", "search", "", tuple(AREAS), 6)
BY_ID = {s.source_id: s for s in CATALOG + (SEARCH,)}


def source(source_id: str) -> Optional[Source]:
    """The source with this id, or None."""
    return BY_ID.get(source_id)


def for_areas(areas) -> list[Source]:
    """The catalog's feeds covering any of these areas (every feed when none are named)."""
    wanted = set(areas or ())
    return [s for s in CATALOG if not wanted or wanted & set(s.areas)]


def _context() -> ssl.SSLContext:
    """TLS with certifi's certificates where it's installed (the PC's own store misses some), else the system's."""
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def get(url: str) -> str:
    """One page or feed, as text: MIA's user agent, certifi, 20 seconds, at most 3 MB. SourceRefused on a 401, 403 or
    429 (the source turned the reader away); OSError for anything else."""
    request = urllib.request.Request(url, headers={"User-Agent": AGENT})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT, context=_context()) as answer:
            return answer.read(MAX_BYTES).decode("utf-8", errors="replace")
    except urllib.error.HTTPError as problem:
        if problem.code in (401, 403, 429):
            raise SourceRefused(f"{url} answered {problem.code}") from None
        raise


def fetch_feed(src: Source, watch, get_text: Callable[[str], str] = get) -> list[dict]:
    """The feed adapter: every item in the source's feed, as raw items (the watch's words are matched later)."""
    from core.good_news import parse_feed

    text = get_text(src.url)
    if "<rss" not in text[:3000] and "<feed" not in text[:3000] and "<rdf" not in text[:3000].lower():
        if "captcha" in text.lower() or "access denied" in text.lower():
            raise SourceRefused(f"{src.name} showed a block page")
        return []
    return parse_feed(text, src.source_id)


def fetch_search(src: Source, watch, context=None, search: Optional[Callable] = None) -> list[dict]:
    """The search adapter: the watch's own words (the person's, DEC-0122) through their SearXNG, scrubbed
    (DEC-0053). Raw items carry the result's own site as `site`, so the find names where it came from."""
    from core import online_lookup

    if search is None:
        found = online_lookup.search(context, watch.words)
    else:
        found = search(watch.words)
    items = []
    for r in found.get("results", []):
        link = r.get("url") or r.get("link") or ""
        if link and r.get("title"):
            from urllib.parse import urlparse

            items.append({"source": src.source_id, "title": r["title"], "link": link,
                          "summary": r.get("content") or r.get("snippet") or "", "published": "",
                          "site": urlparse(link).netloc.removeprefix("www.")})
    return items


ADAPTERS = {"feed": fetch_feed, "search": fetch_search}
