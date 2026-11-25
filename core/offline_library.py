"""
core.offline_library
======================

Her offline library, chosen and fetched (Zac, 2026-11-22: "add as many offline resources as you think would help her
to be the most useful offline assistant for all the use cases we have talked about"). The packs are Kiwix ZIM files,
read by core/reference_library_manager.py; this module says which packs she should have, gets them, and keeps them
current.

**The catalog** (`PACKS`): each pack Kiwix publishes that serves something MIA does, by its Kiwix name and flavour,
on a shelf (homestead and growing, building and repair, food and water, health, preparedness, energy, animals,
vehicles, electronics and radio, computers, learning, everyday life, reference, maps), in one of three sets:
`essential` (the self-reliance core, a few tens of gigabytes), `standard` (everyday life, tools and learning) and `big`
(Wikipedia with its pictures, Wiktionary, the Gutenberg technology shelf, the Army's field manuals, his country's
map). The map is the one for his country (`core/region.country_of`), never named in code.

**What's published now** (`published`): Kiwix's own OPDS catalog (library.kiwix.org), read at most once a day and
kept beside the packs (`.fetch/catalog.xml`), gives each pack's newest file, its size and its metalink.

**Getting a pack** (`fetch`, `run_queue`): packs wait in a queue (`.fetch/queue.json`) and are downloaded one at a
time, smallest first, in the background. Each file's size and SHA-256 come from its metalink on Kiwix's own server
(lb.download.kiwix.org, over HTTPS); the bytes come from the mirrors it lists, the fastest first (`ranked`), one
falling well below what it showed left and the mirrors tried again, resumed where a download stopped (HTTP Range), and a file whose hash doesn't match is thrown away, never installed. Only then is it moved into the
library, and the older version of the same pack removed. A download never leaves less than `FREE_FLOOR` free on the
disk. One runner at a time (a lock file), so MIA and the command line (`python -m tools.offline_library`) never fetch
the same file twice; a restart picks the queue up again (`resume`).

**Her own index** (core/pack_index.py): after the downloads, each pack Kiwix didn't index (and every PDF inside a
pack) is indexed by her, so all of it can be searched; `resume` also indexes packs copied in by hand.

**Asking her** (`look_up`): the person's question searched in every pack (Kiwix's index and hers), each pack's best
articles read whole and cut to where the answer is (core/reference_reader.py), the best passages kept by how much of
the question they hold, with how to talk about them (naturally, every fact from the text); `read_further` reads one
source at length. Each passage is named by pack and article (and its ref, to read further) so she can say where
it came from, and framed as outside text (core/browser_safety.outside), so a pack's words are information, never
instructions to her. `passages` gives the same passages as data ({pack, article, text, ref}) for a screen: a plan's mission guide shows them (T-0060).

Fetching is the action `library.fetch` (his yes; it downloads gigabytes); looking things up needs none.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import threading
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from core.actions import ACTION_TYPES, ActionError, ActionType
from core.logger import get_logger

log = get_logger(__name__)

CATALOG_URL = "https://library.kiwix.org/catalog/v2/entries?count=-1&lang=eng"
CATALOG_HOURS = 24
AGENT = "MIA-offline-library/1.0"
FREE_FLOOR = 40 * 10**9  # never fill the disk past this
CHUNK = 1 << 20
PROBE = 4 << 20  # bytes read from each mirror to see how fast it is
PROBE_BLOCK = 64 << 10
SLOW = 300_000  # bytes a second: slower than this (or a quarter of what it showed) for STALL seconds: crawling
STALL = 60
TRIES = 16  # mirrors tried, and tried again, for one file
SETS = ("essential", "standard", "big")


@dataclass(frozen=True)
class Pack:
    """One pack she should have: its Kiwix name and flavour, its shelf, its set and why it's there."""
    name: str
    flavour: str
    shelf: str
    set: str
    why: str

    @property
    def key(self) -> str:
        """The pack's id here: its name, with its flavour when it has one."""
        return f"{self.name}_{self.flavour}" if self.flavour else self.name


def _p(name, flavour, shelf, set_, why):
    """One catalog row."""
    return Pack(name, flavour, shelf, set_, why)


PACKS: tuple[Pack, ...] = (
    # Homestead and growing
    _p("appropedia_en_all", "maxi", "Homestead and growing", "essential",
       "appropriate technology: building, water, food, energy, sanitation for a self-reliant life"),
    _p("cd3wdproject.org_en_all", "", "Homestead and growing", "essential",
       "over 900 technical manuals for small farms and workshops (CD3WD)"),
    _p("wikiciv_en_all", "maxi", "Homestead and growing", "essential", "making things from scratch, step by step"),
    _p("gardenology_en_all", "", "Homestead and growing", "essential", "a plant and garden encyclopedia"),
    _p("gardening.stackexchange.com_en_all", "", "Homestead and growing", "essential",
       "gardeners' questions answered: soil, pests, pruning, growing"),
    _p("sustainability.stackexchange.com_en_all", "", "Homestead and growing", "essential", "sustainable living"),
    _p("gutenberg_en_lcc-s", "", "Homestead and growing", "standard",
       "the classic agriculture books: farming, orchards, livestock, forestry, beekeeping"),
    _p("lrnselfreliance_en_all", "", "Homestead and growing", "standard",
       "videos on beekeeping, gardening and self-reliance"),
    # Building and repair
    _p("diy.stackexchange.com_en_all", "", "Building and repair", "essential",
       "home improvement answered by contractors: framing, wiring, plumbing, roofing"),
    _p("woodworking.stackexchange.com_en_all", "", "Building and repair", "essential", "woodworking and joinery"),
    _p("engineering.stackexchange.com_en_all", "", "Building and repair", "essential",
       "structural and mechanical engineering questions"),
    _p("ifixit_en_all", "", "Building and repair", "essential", "repair guides for tools, machines and devices"),
    _p("wikibooks_en_all", "maxi", "Building and repair", "standard",
       "open textbooks, among them the cookbook, how-tos and trades"),
    _p("gutenberg_en_lcc-t", "", "Building and repair", "big",
       "the classic technology books: building, carpentry, masonry, metalwork, engines"),
    _p("armypubs_en_all", "", "Building and repair", "big",
       "the US Army's field manuals: construction, survival, first aid, water, vehicles"),
    # Food and water
    _p("usda-2015_en", "", "Food and water", "essential", "the USDA guide to safe home canning"),
    _p("zimgit-food-preparation_en", "", "Food and water", "essential", "preserving and preparing food"),
    _p("zimgit-water_en", "", "Food and water", "essential", "collecting and purifying water"),
    _p("cooking.stackexchange.com_en_all", "", "Food and water", "essential", "cooking questions answered"),
    _p("homebrew.stackexchange.com_en_all", "", "Food and water", "essential", "brewing, wine and fermenting"),
    _p("canadian-prepper_en_preppingfood", "", "Food and water", "standard", "long-term food storage (videos)"),
    # Health
    _p("wikipedia_en_medicine", "maxi", "Health and first aid", "essential",
       "WikiMed, the largest medical encyclopedia, with pictures"),
    _p("mdwiki_en_all", "maxi", "Health and first aid", "essential", "healthcare articles curated by doctors"),
    _p("medlineplus.gov_en_all", "", "Health and first aid", "essential", "trusted health information"),
    _p("zimgit-medicine_en", "", "Health and first aid", "essential", "field and emergency medicine books"),
    _p("irp.fas.org_en_military-medicine", "", "Health and first aid", "essential",
       "military medicine manuals for care far from help"),
    _p("nhs.uk_en_medicines", "", "Health and first aid", "essential", "medicines, how and when to take them"),
    _p("fitness.stackexchange.com_en_all", "", "Health and first aid", "standard", "training and exercise"),
    # Preparedness
    _p("ready.gov_en_all", "", "Preparedness", "essential", "planning for storms, fire and outages"),
    _p("zimgit-post-disaster_en", "", "Preparedness", "essential", "what to do after a disaster"),
    _p("zimgit-knots_en", "", "Preparedness", "essential", "knots, lashings and ladders, illustrated"),
    _p("outdoors.stackexchange.com_en_all", "", "Preparedness", "essential", "the outdoors: camping, navigation, safety"),
    _p("canadian-prepper_en_winterprepping", "", "Preparedness", "standard", "getting ready for winter (videos)"),
    # Energy
    _p("energypedia_en_all", "maxi", "Energy", "essential", "solar, wind, biogas and small power systems"),
    _p("solar.lowtechmagazine.com_mul_all", "", "Energy", "essential", "low-tech answers to energy and living"),
    # Animals
    _p("wikivet.net_en_all", "maxi", "Animals", "essential", "veterinary medicine, livestock included"),
    _p("pets.stackexchange.com_en_all", "", "Animals", "essential", "caring for animals"),
    # Vehicles and machines
    _p("mechanics.stackexchange.com_en_all", "", "Vehicles and machines", "essential",
       "fixing cars, trucks and motorcycles"),
    _p("bicycles.stackexchange.com_en_all", "", "Vehicles and machines", "standard", "bicycles and their repair"),
    # Electronics and radio
    _p("ham.stackexchange.com_en_all", "", "Electronics and radio", "essential", "amateur radio"),
    _p("electronics.stackexchange.com_en_all", "", "Electronics and radio", "standard",
       "electronics and electrical engineering"),
    _p("arduino.stackexchange.com_en_all", "", "Electronics and radio", "standard", "Arduino projects and sensors"),
    _p("raspberrypi.stackexchange.com_en_all", "", "Electronics and radio", "standard", "Raspberry Pi"),
    _p("3dprinting.stackexchange.com_en_all", "", "Electronics and radio", "standard", "3D printing"),
    # Computers (MIA OS is Linux)
    _p("archlinux_en_all", "maxi", "Computers", "standard", "the ArchWiki, the best Linux reference"),
    _p("unix.stackexchange.com_en_all", "", "Computers", "standard", "Unix and Linux answered"),
    _p("askubuntu.com_en_all", "", "Computers", "standard", "Linux desktop questions"),
    _p("superuser.com_en_all", "", "Computers", "standard", "computer questions of every kind"),
    _p("security.stackexchange.com_en_all", "", "Computers", "standard", "keeping computers and accounts safe"),
    _p("devdocs_en_python", "", "Computers", "standard", "Python's documentation"),
    _p("devdocs_en_bash", "", "Computers", "standard", "Bash's documentation"),
    _p("devdocs_en_git", "", "Computers", "standard", "Git's documentation"),
    _p("devdocs_en_javascript", "", "Computers", "standard", "JavaScript's documentation"),
    _p("devdocs_en_html", "", "Computers", "standard", "HTML's documentation"),
    _p("devdocs_en_css", "", "Computers", "standard", "CSS's documentation"),
    # Learning
    _p("libretexts.org_en_eng", "", "Learning", "standard", "engineering textbooks"),
    _p("libretexts.org_en_math", "", "Learning", "standard", "mathematics textbooks"),
    _p("libretexts.org_en_phys", "", "Learning", "standard", "physics textbooks"),
    _p("libretexts.org_en_bio", "", "Learning", "standard", "biology textbooks (soil, plants, animals)"),
    _p("phet_en_all", "", "Learning", "standard", "interactive science and maths simulations"),
    _p("wikiversity_en_all", "maxi", "Learning", "standard", "tutorials and courses"),
    _p("openmusictheory.com_en_all", "", "Learning", "standard", "music theory, for the guitar"),
    _p("music.stackexchange.com_en_all", "", "Learning", "standard", "music practice and theory"),
    # Everyday life
    _p("money.stackexchange.com_en_all", "", "Everyday life", "standard", "personal finance and money"),
    _p("law.stackexchange.com_en_all", "", "Everyday life", "standard", "law questions in plain words"),
    _p("travel.stackexchange.com_en_all", "", "Everyday life", "standard", "travel"),
    _p("wikivoyage_en_all", "maxi", "Everyday life", "standard", "the travel guide, with maps and pictures"),
    _p("photo.stackexchange.com_en_all", "", "Everyday life", "standard", "photography"),
    _p("workplace.stackexchange.com_en_all", "", "Everyday life", "standard", "work and the workplace"),
    _p("interpersonal.stackexchange.com_en_all", "", "Everyday life", "standard", "getting on with people"),
    # Reference
    _p("theworldfactbook_en_all", "", "Reference", "standard", "facts about every country"),
    _p("wikipedia_en_all", "maxi", "Reference", "big", "all of English Wikipedia, with its pictures"),
    _p("wiktionary_en_all", "nopic", "Reference", "big", "the dictionary"),
)

# His country's map (OpenStreetMap as a pack), by core/region's country; none for a country not listed.
MAPS = {"US": "maps_en_united-states-of-america", "CA": "maps_en_canada", "GB": "maps_en_united-kingdom",
        "AU": "maps_en_australia", "NZ": "maps_en_new-zealand"}


def packs_for(context) -> list[Pack]:
    """Every pack she should have here: the catalog, and the map of his country."""
    from core import region

    found = list(PACKS)
    try:
        name = MAPS.get(region.country_of(context))
    except Exception:  # noqa: BLE001 - no country known: no map
        name = None
    if name:
        found.append(Pack(name, "", "Maps", "big", "his country's map: roads, places and landmarks, offline"))
    return found


def in_set(pack: Pack, which: str) -> bool:
    """Pure logic. Whether a pack is in the set asked for: essential, standard (with the essentials), all."""
    if which == "all":
        return True
    if which == "standard":
        return pack.set in ("essential", "standard")
    return pack.set == which


# ---- what's published now ------------------------------------------------------------------------------------

_ATOM = {"a": "http://www.w3.org/2005/Atom"}


def parse_catalog(xml_text: str) -> dict:
    """Pure logic. Kiwix's OPDS catalog as {pack key: {title, size, metalink, file, date}}, the newest of each; only
    metalinks on Kiwix's own servers over HTTPS (`_kiwix`)."""
    found: dict = {}
    root = ET.fromstring(xml_text)
    for entry in root.findall("a:entry", _ATOM):
        name = (entry.findtext("a:name", "", _ATOM) or "").strip()
        flavour = (entry.findtext("a:flavour", "", _ATOM) or "").strip()
        link = next((l for l in entry.findall("a:link", _ATOM) if l.get("type") == "application/x-zim"), None)
        if not name or link is None:
            continue
        meta = link.get("href", "")
        if not _kiwix(meta):
            continue  # a metalink only from Kiwix's own servers, over HTTPS
        file = meta.rsplit("/", 1)[-1].removesuffix(".meta4")
        key = f"{name}_{flavour}" if flavour else name
        date = (entry.findtext("a:updated", "", _ATOM) or "")[:10]
        row = {"title": (entry.findtext("a:title", "", _ATOM) or name).strip(), "size": int(link.get("length") or 0),
               "metalink": meta, "file": file, "date": date}
        if key not in found or file > found[key]["file"]:
            found[key] = row
    return found


def _fetch_dir(root: Path) -> Path:
    """The library's working folder: the catalog, the queue, partial downloads (never listed as packs)."""
    folder = Path(root) / ".fetch"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _kiwix(url: str) -> bool:
    """Pure logic. Whether a URL is one of Kiwix's own, over HTTPS (where the catalog's metalinks must be)."""
    from urllib.parse import urlparse

    host = (urlparse(url).hostname or "").lower()
    return url.startswith("https://") and (host == "kiwix.org" or host.endswith(".kiwix.org"))


def _public(url: str) -> bool:
    """Pure logic. Whether a mirror's URL names a public host (never this computer or the home network: the hash
    guards the bytes, this guards where she asks)."""
    import ipaddress
    from urllib.parse import urlparse

    host = (urlparse(url).hostname or "").lower()
    if not host or host == "localhost" or host.endswith(".local"):
        return False
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return True
    return not (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved)


def _get(url: str, timeout: float = 60.0, headers: Optional[dict] = None):
    """One HTTPS request (redirects followed); the open response. URLError and OSError pass up."""
    request = urllib.request.Request(url, headers={"User-Agent": AGENT, **(headers or {})})
    return urllib.request.urlopen(request, timeout=timeout)  # noqa: S310 (fixed Kiwix hosts and their mirrors)


def _in_tests(get: Callable) -> bool:
    """Whether this is the test suite asking with the real network (it never may)."""
    import sys

    return "pytest" in sys.modules and get is _get


def published(root: Path, get: Callable = _get, now: Optional[float] = None) -> dict:
    """What Kiwix publishes now (parse_catalog), from the copy kept beside the packs when it's under a day old,
    else read again; the old copy when Kiwix can't be reached; {} when there's none (and inside the test suite,
    never the network)."""
    kept = Path(root) / ".fetch" / "catalog.xml"
    fresh = kept.exists() and (now or time.time()) - kept.stat().st_mtime < CATALOG_HOURS * 3600
    if not fresh and not _in_tests(get):
        kept = _fetch_dir(root) / "catalog.xml"
        try:
            with get(CATALOG_URL, timeout=120) as response:
                text = response.read().decode("utf-8")
            parse_catalog(text)  # never keep one that doesn't read
            kept.write_text(text, encoding="utf-8")
        except (urllib.error.URLError, OSError, ET.ParseError) as problem:
            log.info("Kiwix's catalog couldn't be read now: %s", problem)
    try:
        return parse_catalog(kept.read_text(encoding="utf-8")) if kept.exists() else {}
    except (OSError, ET.ParseError):
        return {}


# ---- what's here ---------------------------------------------------------------------------------------------

_DATED = re.compile(r"^(?P<key>.+)_(?P<date>\d{4}-\d{2})\.zim$")


def installed(root: Path) -> dict:
    """Pure logic over the folder. The packs in the library by key: {key: file name} (the newest when two)."""
    found: dict = {}
    for path in sorted(Path(root).glob("*.zim")):
        m = _DATED.match(path.name)
        key = m.group("key") if m else path.stem
        if key not in found or path.name > found[key]:
            found[key] = path.name
    return found


def status(context, root: Path, catalog: Optional[dict] = None) -> list[dict]:
    """The library page's shelves: each pack she should have, with its size, whether it's here, whether a newer one
    is published, and how its download is going."""
    catalog = published(root) if catalog is None else catalog
    have, queue = installed(root), _read_queue(root)
    rows = []
    for pack in packs_for(context):
        row = catalog.get(pack.key) or {}
        here = have.get(pack.key, "")
        rows.append({"key": pack.key, "title": row.get("title", pack.key), "shelf": pack.shelf, "set": pack.set,
                     "why": pack.why, "size_gb": round(row.get("size", 0) / 1e9, 2), "here": bool(here),
                     "newer": bool(here and row.get("file") and row["file"] > here),
                     "published": bool(row), "state": queue["state"].get(pack.key, "")})
    return rows


# ---- getting them --------------------------------------------------------------------------------------------

def _read_queue(root: Path) -> dict:
    """The download queue: {"waiting": [keys], "state": {key: "waiting" | "fetching 40%" | "fetched" | "failed: why"},
    "remove": [older files still to delete]}. No file is an empty queue; one that can't be read just now (Windows,
    another reader) is tried again, never taken as empty."""
    path = Path(root) / ".fetch" / "queue.json"  # read without making the folder
    for attempt in range(20):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return {"waiting": list(data.get("waiting", [])), "state": dict(data.get("state", {})),
                    "remove": list(data.get("remove", []))}
        except FileNotFoundError:
            break
        except ValueError:
            log.warning("The download queue didn't read; starting it afresh.")
            break
        except OSError:
            time.sleep(0.05 * (attempt + 1))  # another reader holds it a moment
    else:
        raise OSError("the download queue couldn't be read")
    return {"waiting": [], "state": {}, "remove": []}


def _write_queue(root: Path, queue: dict) -> None:
    """Keeps the queue (a plain file beside the packs; never one of his records); a replace Windows refuses while
    someone reads it is tried again."""
    path = _fetch_dir(root) / "queue.json"
    tmp = path.with_suffix(f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(queue, indent=1), encoding="utf-8")
    for attempt in range(20):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            time.sleep(0.05 * (attempt + 1))
    os.replace(tmp, path)


class _QueueLock:
    """The queue's read-change-write, one at a time across processes (MIA and the command line) and threads."""

    def __init__(self, root: Path):
        """The lock file beside the queue."""
        self.path = _fetch_dir(root) / "queue.lock"
        self.handle = None

    def __enter__(self):
        """Waits for the lock."""
        _queue_lock.acquire()
        self.handle = open(self.path, "a+b")
        if os.name == "nt":
            import msvcrt

            self.handle.seek(0)
            for _ in range(200):
                try:
                    msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    time.sleep(0.05)
        else:
            import fcntl

            fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX)
        return self

    def __exit__(self, *exc) -> None:
        """Lets it go."""
        try:
            if os.name == "nt":
                import msvcrt

                self.handle.seek(0)
                try:
                    msvcrt.locking(self.handle.fileno(), msvcrt.LK_UNLCK, 1)
                except OSError:
                    pass
            self.handle.close()
        finally:
            _queue_lock.release()


_queue_lock = threading.Lock()


def choose(context, root: Path, which: str = "", keys: Optional[list] = None, catalog: Optional[dict] = None) -> list:
    """Pure logic over the catalog. The packs to fetch: a set (essential, standard, all) or the keys named, only ones
    she should have, published now, and not already here at their newest; smallest first. ActionError for none."""
    catalog = published(root) if catalog is None else catalog
    mine = {p.key: p for p in packs_for(context)}
    if keys:
        unknown = [k for k in keys if k not in mine]
        if unknown:
            raise ActionError(f"Those aren't packs in her library's catalog: {', '.join(unknown[:5])}.")
        wanted = [mine[k] for k in keys]
    elif which in ("essential", "standard", "all", "big"):
        wanted = [p for p in mine.values() if in_set(p, which)]
    else:
        raise ActionError("Say which: the essentials, the standard library, all of it, or the packs by name.")
    have = installed(root)
    todo = [p.key for p in wanted if p.key in catalog and have.get(p.key, "") < catalog[p.key]["file"]]
    if not todo:
        raise ActionError("Those packs are already here and up to date (or Kiwix can't be reached to say).")
    return sorted(todo, key=lambda k: catalog[k]["size"])


def describe(context, root: Path, which: str = "", keys: Optional[list] = None) -> str:
    """The card's sentence: how many packs and how many gigabytes, and whether they fit."""
    catalog = published(root)
    todo = choose(context, root, which, keys, catalog)
    size = sum(catalog[k]["size"] for k in todo)
    free = shutil.disk_usage(root).free
    if free - size < FREE_FLOOR:
        raise ActionError(f"That's {size / 1e9:.0f} GB and only {free / 1e9:.0f} GB is free: it would leave too "
                          "little room. Fetch a smaller set, or free some space.")
    return (f"Download {len(todo)} offline reference pack{'s' if len(todo) != 1 else ''} into her library "
            f"({size / 1e9:.1f} GB, from Kiwix; each checked against Kiwix's own hash)")


def fetch(context, root: Path, which: str = "", keys: Optional[list] = None, start: bool = True) -> str:
    """Puts the packs in the queue (under the queue's lock, shared with the command line) and starts the downloads
    in the background (a runner already going takes them); said when each set is done."""
    describe(context, root, which, keys)  # the same checks as the card
    todo = choose(context, root, which, keys)
    with _QueueLock(root):
        queue = _read_queue(root)
        for key in todo:
            if key not in queue["waiting"]:
                queue["waiting"].append(key)
            queue["state"][key] = "waiting"
        _write_queue(root, queue)
    if start:
        threading.Thread(target=run_queue, args=(context, root), name="offline library", daemon=True).start()
    return f"Fetching {len(todo)} pack{'s' if len(todo) != 1 else ''} in the background; the Knowledge page shows how far."


def parse_metalink(xml_text: str) -> dict:
    """Pure logic. A metalink's file: {name, size, sha256, urls (https first, by priority; never a mirror on this
    computer or the home network: `_public`)}."""
    ns = {"m": "urn:ietf:params:xml:ns:metalink"}
    root = ET.fromstring(xml_text)
    file = root.find("m:file", ns)
    if file is None:
        raise ValueError("no file in the metalink")
    sha = next((h.text for h in file.findall("m:hash", ns) if h.get("type") == "sha-256"), "") or ""
    urls = sorted(((int(u.get("priority") or 99), (u.text or "").strip()) for u in file.findall("m:url", ns)),
                  key=lambda pu: (not pu[1].startswith("https://"), pu[0]))
    return {"name": file.get("name", ""), "size": int(file.findtext("m:size", "0", ns) or 0), "sha256": sha.strip(),
            "urls": [u for _p, u in urls if u.startswith(("https://", "http://")) and _public(u)]}


def _resumes(response, have: int) -> bool:
    """Whether an answer to a Range request carries the rest from exactly where the file stopped (206, its
    Content-Range starting at `have`)."""
    if getattr(response, "status", 200) != 206:
        return False
    headers = getattr(response, "headers", None)
    told = (headers.get("Content-Range", "") if headers is not None else "") or ""
    return not told or told.replace("bytes ", "").split("-", 1)[0].strip() == str(have)


def _hash_of(path: Path) -> str:
    """A file's SHA-256."""
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(CHUNK * 4), b""):
            digest.update(block)
    return digest.hexdigest()


class _Crawling(OSError):
    """A mirror slower than SLOW for STALL seconds: the next one is tried, from where this one stopped."""


def fastest(urls: list[str], get: Callable = _get, clock: Callable = time.monotonic) -> list[str]:
    """The mirrors fastest first (`ranked`), as URLs."""
    return [url for url, _rate in ranked(urls, get, clock)]


def ranked(urls: list[str], get: Callable = _get, clock: Callable = time.monotonic) -> list[tuple[str, float]]:
    """The mirrors fastest first with the rate each showed (bytes a second): each asked for its first PROBE bytes
    for a few seconds, in PROBE_BLOCK reads (so a crawling one can't hold the probe for minutes); one that fails or
    sends nothing goes last (never left out: the hash still decides). Kiwix's order breaks ties."""
    timed = []
    for n, url in enumerate(urls[:8]):
        started, got = clock(), 0
        try:
            with get(url, timeout=10, headers={"Range": f"bytes=0-{PROBE - 1}"}) as response:
                while got < PROBE and clock() - started < 8:
                    block = response.read(PROBE_BLOCK)  # small reads: a crawling mirror can't hold the probe long
                    if not block:
                        break
                    got += len(block)
        except (urllib.error.URLError, OSError):
            got = 0
        rate = got / max(clock() - started, 1e-3)
        timed.append((-rate, n, url))
    return [(url, -r) for r, _n, url in sorted(timed)] + [(url, 0.0) for url in urls[8:]]


def download(meta: dict, partial: Path, get: Callable = _get, progress: Callable = lambda done, total: None,
             clock: Callable = time.monotonic) -> None:
    """One file from its mirrors into `partial`, resumed from what's already there; then its hash checked against
    the metalink's. The mirrors are probed once (`ranked`) and tried fastest first; one that falls below a quarter of
    what it showed (never more than 4 x SLOW, nor less than SLOW) for STALL seconds is left for the next, ranked lower,
    which resumes. TRIES counts only tries that moved nothing (a slow mirror that still delivered isn't one). A mirror that won't resume from exactly where it stopped is passed
    over, never allowed to overwrite what's here; a partial larger than the file is thrown away. OSError when no mirror finishes it; ValueError
    (and the partial file removed) when the hash is wrong."""
    if not re.fullmatch(r"[0-9a-f]{64}", meta.get("sha256", "")):
        raise ValueError("Kiwix's metalink gave no SHA-256 for it")
    problems = []
    if partial.exists() and partial.stat().st_size > meta["size"]:
        partial.unlink()  # more than the file: never right
    big = meta["size"] > 50 * PROBE
    failed: set = set()  # mirrors that errored or won't resume: not asked again for this file
    crawled: dict = {}  # mirror -> how many times it crawled: its rate counts for less each time
    rates = dict(ranked(meta["urls"], get, clock)) if big else {}  # probed once a file, never on every retry
    misses = 0
    while misses < TRIES:
        have = partial.stat().st_size if partial.exists() else 0
        if have >= meta["size"]:
            break
        left = [u for u in meta["urls"] if u not in failed]
        if not big:
            left = [u for u in left if u not in crawled]
        if not left:
            break
        order = sorted(((u, rates.get(u, 0.0)) for u in left), key=lambda ur: -ur[1] / (4 ** crawled.get(ur[0], 0)))
        url, shown = order[0]
        floor = max(SLOW, min(shown / 4, 4 * SLOW))  # well below what it showed, but a steady 1.2 MB/s never is
        started_at = have
        try:
            headers = {"Range": f"bytes={have}-"} if have else {}
            with get(url, timeout=60, headers=headers) as response:
                if have and not _resumes(response, have):
                    problems.append(f"{url.split('/')[2]}: won't resume")
                    failed.add(url)
                    continue  # never throw away what's already here: the next mirror
                with open(partial, "ab" if have else "wb") as out:
                    window_start, window_bytes = clock(), 0
                    for block in iter(lambda: response.read(CHUNK), b""):
                        out.write(block)
                        have += len(block)
                        window_bytes += len(block)
                        progress(have, meta["size"])
                        if clock() - window_start >= STALL:
                            if window_bytes < floor * STALL:
                                raise _Crawling(f"slower than {int(floor) // 1000} kB/s")
                            window_start, window_bytes = clock(), 0
        except _Crawling as problem:
            problems.append(f"{url.split('/')[2]}: {problem}")
            crawled[url] = crawled.get(url, 0) + 1
            if (partial.stat().st_size if partial.exists() else 0) <= started_at:
                misses += 1  # a crawl that still moved the file on isn't a lost try
            continue
        except (urllib.error.URLError, OSError) as problem:
            problems.append(f"{url.split('/')[2]}: {problem}")
            failed.add(url)
            misses += 1
            continue
    if not partial.exists() or partial.stat().st_size != meta["size"]:
        raise OSError("no mirror finished it (" + "; ".join(problems[-3:]) + ")")
    if _hash_of(partial) != meta["sha256"]:
        partial.unlink(missing_ok=True)
        raise ValueError("it didn't match Kiwix's hash, so it was thrown away")


class _RunnerLock:
    """One runner at a time across processes: an exclusive lock on `.fetch/runner.lock`, held while it runs."""

    def __init__(self, root: Path):
        """The lock file beside the queue."""
        self.path = _fetch_dir(root) / "runner.lock"
        self.handle = None

    def __enter__(self) -> bool:
        """True when this one holds it; False when another runner does."""
        self.handle = open(self.path, "a+b")
        try:
            if os.name == "nt":
                import msvcrt

                self.handle.seek(0)
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except OSError:
            self.handle.close()
            self.handle = None
            return False

    def __exit__(self, *exc) -> None:
        """Lets it go."""
        if self.handle is not None:
            try:
                if os.name == "nt":
                    import msvcrt

                    self.handle.seek(0)
                    msvcrt.locking(self.handle.fileno(), msvcrt.LK_UNLCK, 1)
            finally:
                self.handle.close()


def _set_state(root: Path, key: str, state: str, done: bool = False) -> None:
    """One pack's state in the queue (and out of the waiting list when it's finished, fetched or failed), under the
    queue's lock."""
    with _QueueLock(root):
        queue = _read_queue(root)
        queue["state"][key] = state
        if done:
            queue["waiting"] = [k for k in queue["waiting"] if k != key]
        _write_queue(root, queue)


def run_queue(context, root: Path, get: Callable = _get, catalog: Optional[dict] = None) -> dict:
    """Downloads every waiting pack, one at a time, then installs each checked one (the file named by Kiwix's catalog,
    moved into the library and dated so it's listed at once; its older version removed, or listed to remove when
    Windows still holds it open); then her index, then anything queued meanwhile. Returns {"fetched": n, "failed": n} or {"busy": True} when another runner holds the lock.
    Never raises."""
    if _in_tests(get):
        return {"fetched": 0, "failed": 0}  # the suite never downloads for real
    root = Path(root)
    fetched = failed = 0
    with _RunnerLock(root) as mine:
        if not mine:
            return {"busy": True}
        catalog = published(root, get) if catalog is None else catalog
        _remove_old(context, root)
        while True:
            waiting = _read_queue(root)["waiting"]
            if not waiting:
                _index(context, root)  # her index for what came; then anything queued meanwhile
                if _read_queue(root)["waiting"]:
                    continue
                break
            key = waiting[0]
            row = catalog.get(key)
            try:
                if not row:
                    raise ValueError("Kiwix doesn't publish it now")
                with get(row["metalink"], timeout=60) as response:
                    meta = parse_metalink(response.read().decode("utf-8"))
                if meta["name"] != row["file"]:
                    raise ValueError("Kiwix's metalink names another file")
                partial = _fetch_dir(root) / (meta["name"] + ".partial")
                have = partial.stat().st_size if partial.exists() else 0
                if shutil.disk_usage(root).free - (meta["size"] - have) < FREE_FLOOR:
                    raise OSError("not enough free space for it")
                shown = [-1]

                def progress(done, total, key=key, shown=shown):
                    """The queue says how far, every whole percent."""
                    pct = int(done * 100 / max(total, 1))
                    if pct != shown[0]:
                        shown[0] = pct
                        try:
                            _set_state(root, key, f"fetching {pct}%")
                        except OSError:
                            pass  # the progress line isn't the download

                download(meta, partial, get, progress)
                final = root / meta["name"]
                os.replace(partial, final)
                past = time.time() - 60
                os.utime(final, (past, past))  # settled: the library lists it at once (it skips files still copying)
                older = [old.name for old in Path(root).glob("*.zim")
                         if (m := _DATED.match(old.name)) and m.group("key") == key and old.name != meta["name"]]
                if older:
                    with _QueueLock(root):
                        queue = _read_queue(root)
                        queue["remove"] = sorted(set(queue["remove"]) | set(older))
                        _write_queue(root, queue)
                    _remove_old(context, root)
                _set_state(root, key, "fetched", done=True)
                fetched += 1
                log.info("Fetched the offline pack %s", meta["name"])
            except Exception as problem:  # noqa: BLE001 - one pack's failure never stops the rest
                _set_state(root, key, f"failed: {str(problem)[:160]}", done=True)
                failed += 1
                log.warning("Couldn't fetch the offline pack %s: %s", key, problem)
    if fetched or failed:
        notes = getattr(context, "notifications", None)
        if notes is not None:
            notes.notify("Offline library", f"{fetched} pack{'s' if fetched != 1 else ''} added to her library"
                         + (f", {failed} couldn't be fetched" if failed else "") + ".", source="knowledge")
    return {"fetched": fetched, "failed": failed}


def _remove_old(context, root: Path) -> None:
    """Deletes the older versions an update replaced, closing her own handle on each first; one Windows still holds
    open stays listed and goes next time. Never raises."""
    try:
        with _QueueLock(root):
            queue = _read_queue(root)
            library = getattr(context, "reference_library", None)
            left = []
            for name in queue["remove"]:
                if library is not None:
                    getattr(library, "_archives", {}).pop(Path(name).stem, None)
                try:
                    (Path(root) / name).unlink(missing_ok=True)
                except OSError:
                    left.append(name)
            if left != queue["remove"]:
                queue["remove"] = left
                _write_queue(root, queue)
    except OSError as problem:
        log.info("Older packs couldn't be removed yet: %s", problem)


def _library(context, root: Path):
    """The reference library over this folder (the context's when it's the same folder)."""
    library = getattr(context, "reference_library", None)
    if library is not None and Path(library.root_path).resolve() == Path(root).resolve():
        return library
    from core.reference_library_manager import ReferenceLibraryManager

    library = ReferenceLibraryManager(context)
    library._root_path = Path(root)
    return library


def _index(context, root: Path) -> int:
    """Her own index for each pack that wants one and hasn't got it (core/pack_index.py), its state said in the
    queue while it's built. Never raises."""
    from core import pack_index

    try:
        return pack_index.index_missing(_library(context, root), root,
                                        lambda stem, n: _set_state(root, "index:" + stem, f"indexing ({n:,} read)"))
    except Exception as problem:  # noqa: BLE001
        log.warning("The offline packs couldn't be indexed: %s", problem)
        return 0


def _unindexed(root: Path) -> bool:
    """Whether some pack here has no index file of hers yet (one that wants none is decided when it's opened)."""
    from core import pack_index

    return any(not pack_index.index_path(root, p).exists() for p in Path(root).glob("*.zim"))


def resume(context, root: Path) -> bool:
    """At start: picks a waiting queue up again in the background, indexes packs copied in by hand, and removes
    older versions left over. True when there was something to do."""
    if not _read_queue(root)["waiting"] and not _unindexed(root) and not _read_queue(root)["remove"]:
        return False
    threading.Thread(target=run_queue, args=(context, root), name="offline library", daemon=True).start()
    return True


# ---- asking her ----------------------------------------------------------------------------------------------

_WORD = re.compile(r"[a-z0-9]{3,}")
_STOP = {"the", "and", "for", "how", "what", "with", "can", "you", "does", "should", "when", "why", "from", "that",
         "this", "are", "into", "about", "best", "way", "make", "get", "use", "need", "much", "many", "which"}


def _terms(text: str) -> set:
    """Pure logic. The words of a question worth matching."""
    return {w for w in _WORD.findall((text or "").lower()) if w not in _STOP}


def rank(question: str, snippets: list, keep: int = 4) -> list:
    """Pure logic. The passages that hold the most of the question's words (the title counts double), best first."""
    terms = _terms(question)
    def score(s):
        """How many of the question's words the passage holds."""
        title, body = _terms(s.article_title), _terms(s.snippet)
        return 2 * len(terms & title) + len(terms & body)
    return [s for s in sorted(snippets, key=score, reverse=True) if score(s) > 0][:keep]


def passages(library, question: str, keep: int = 4) -> list[dict]:
    """The best passages in the offline library for a question: each pack's best articles read whole and cut to
    where the question's words gather (core/reference_reader.py), Kiwix's index and hers, weighed by how rare each
    word is, then ranked by meaning where her embedding model answers (about half the question's words held); for a
    plain canning question, never the pickle and relish recipes (`reference_reader.not_pickling`):
    [{pack, article, text, ref}]; [] with no packs or nothing matching. Raises on a search that fails (look_up says so)."""
    from core import reference_reader

    question = " ".join(str(question or "").split())[:300]
    if not question or library is None or not library.list_packs():
        return []
    words = reference_reader.terms(question)
    found = reference_reader.weighed(reference_reader.not_pickling(question, reference_reader.gather(library, question)),
                                     words)
    meant = reference_reader.by_meaning(getattr(library, "context", None), question, found)
    return [{k: p[k] for k in ("pack", "article", "text", "ref")}
            for p in reference_reader.rank(meant if meant is not None else found, keep, len(words))]


# Said to the model, never to him: with no pack or nothing matching, she answers from what she knows (the live sweep,
# 2026-11-25: "how much space do goats need?" was answered "Her offline library has no packs yet", nothing else)
FROM_WHAT_YOU_KNOW = ("Answer from what you know, as general guidance, in your own words; don't mention the library "
                      "unless they ask where it comes from.")
NO_PACKS = "The offline library has no packs yet (they can be fetched on the Knowledge page). " + FROM_WHAT_YOU_KNOW


def look_up(library, question: str, keep: int = 4) -> str:
    """Her answer's material from the offline library: the best passages for the question (`passages`), each named
    by pack and article with its ref on a line of its own, framed as outside text and followed by how to talk about
    them (core/reference_reader.HOW_TO_TALK); or, when there are no packs or nothing matches, a line for the model to
    answer from what it knows (`FROM_WHAT_YOU_KNOW`), never one said to him as the answer."""
    from core.browser_safety import outside

    question = " ".join(str(question or "").split())[:300]
    if not question:
        return "Say what to look up."
    if library is None or not library.list_packs():
        return NO_PACKS
    try:
        found = passages(library, question, keep)
    except Exception as problem:  # noqa: BLE001 - a damaged pack never breaks the turn
        log.warning("The offline library's search failed: %s", problem)
        return "The offline library couldn't be searched just now. " + FROM_WHAT_YOU_KNOW
    if not found:
        return f"Nothing in the offline library matches \"{question}\". " + FROM_WHAT_YOU_KNOW
    from core.reference_reader import HOW_TO_TALK

    text = "\n\n".join(f"From {p['pack']}, \"{p['article']}\"\nref: {p['ref']}\n{p['text']}" for p in found)
    return outside(text, "From her offline library") + "\n" + HOW_TO_TALK


def read_further(library, ref: str, focus: str = "") -> str:
    """One source read at length (core/reference_reader.read), framed as outside text with how to talk about it; a
    plain sentence for a ref that isn't here."""
    from core.browser_safety import outside
    from core.reference_reader import HOW_TO_TALK, read

    try:
        found = read(library, ref, focus)
    except Exception as problem:  # noqa: BLE001 - a damaged pack never breaks the turn
        log.warning("A reference couldn't be read: %s", problem)
        found = None
    if not found:
        return "That reference isn't in her library now: look it up again."
    return outside(f"From {found['pack']}, \"{found['article']}\":\n{found['text']}", "From her offline library") \
        + "\n" + HOW_TO_TALK


# ---- the action ----------------------------------------------------------------------------------------------

def _root(context) -> Path:
    """The library's folder (core/reference_library_manager.root_path)."""
    library = getattr(context, "reference_library", None)
    if library is None:
        from core.reference_library_manager import ReferenceLibraryManager

        library = ReferenceLibraryManager(context)
    return Path(library.root_path)


def _keys(params: dict) -> list:
    """The packs named in an action's parameters."""
    keys = params.get("keys") or []
    return [str(k) for k in (keys if isinstance(keys, list) else [keys])][:100]


LIBRARY_ACTIONS: dict[str, ActionType] = {a.kind: a for a in (
    ActionType("library.fetch", "Fetch them",
               {"set": "essential, standard or all (or none, with keys)", "keys": "the packs by key"},
               lambda c, p: describe(c, _root(c), str(p.get("set") or ""), _keys(p)),
               lambda c, p: fetch(c, _root(c), str(p.get("set") or ""), _keys(p))),
)}
ACTION_TYPES.update(LIBRARY_ACTIONS)
