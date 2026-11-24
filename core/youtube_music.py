"""
core.youtube_music
====================

YouTube in MIA's Music app (the game layer's step 3, docs/future/GAME_LAYER_PLAN.md; Zac 2026-11-24: "look things up
on YouTube and stream them... build playlists, play music or a specific song").

**Within YouTube's terms.** A song plays through YouTube's own embedded player (`embed_url`, the privacy-enhanced
youtube-nocookie.com host), which YouTube allows any site to show; nothing is downloaded. Saving a song keeps only its
link: its video id, title and channel, as a library track with no file (core/music_manager.py `Track.youtube_id`),
so it sits in playlists and search beside his own files. Ripping YouTube audio to MP3 breaks YouTube's terms and
usually copyright, so MIA doesn't; his own files, Creative Commons audio and purchases with files are what's kept
offline (YouTube Music Premium is the legitimate offline route for its catalogue).

**Search** (`search`): YouTube's Data API (search.list, music videos), with a key of his own
(`set_key`; kept sealed at rest in `KEY_FILE`, core/at_rest.py, and never shown back or put in a proposal). Only
when looking things up online is allowed (core/online_lookup.allowed: online, not a child, not turned off), and only
his search words leave the computer, scrubbed (`online_lookup.scrub`). A link he pastes needs no key
(`video_id`). Titles from YouTube are page text from the web, shown as names only, never read as instructions.
"""

from __future__ import annotations

import html
import json
import re
from typing import Callable, Optional
from urllib.parse import urlencode

from core.at_rest import open_text
from core.atomic_write import atomic_write_text
from core.data_root import DATA_DIR
from core.logger import get_logger

log = get_logger(__name__)

KEY_FILE = DATA_DIR / "youtube_key.json"
SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
EMBED = "https://www.youtube-nocookie.com/embed/"
LIMIT = 8
TIMEOUT = 10
_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
_FROM_LINK = re.compile(r"(?:youtube(?:-nocookie)?\.com/(?:watch\?(?:.*&)?v=|embed/|shorts/|live/|v/)|youtu\.be/)"
                        r"([A-Za-z0-9_-]{11})")


class NeedsKey(RuntimeError):
    """A YouTube search with no key set up: what to do about it, in words."""


def video_id(text: str) -> str:
    """Pure logic. The 11-character video id from a YouTube link (watch, youtu.be, shorts, embed, music.youtube.com)
    or a bare id; "" when it's neither."""
    text = str(text or "").strip()
    if _ID.match(text):
        return text
    found = _FROM_LINK.search(text)
    return found.group(1) if found else ""


def embed_url(ids: list[str], autoplay: bool = True) -> str:
    """Pure logic. YouTube's embedded player for these videos in order (the first plays, the rest follow); "" for
    none. Only well-formed ids go in."""
    ids = [i for i in ids if _ID.match(str(i or ""))]
    if not ids:
        return ""
    query = {"autoplay": "1" if autoplay else "0", "rel": "0", "modestbranding": "1"}
    if len(ids) > 1:
        query["playlist"] = ",".join(ids[1:50])
    return EMBED + ids[0] + "?" + urlencode(query)


def has_key() -> bool:
    """Whether a YouTube key is set up on this computer."""
    return bool(_key())


def _key() -> str:
    """The stored key, or "" (none, or a file that won't open)."""
    return key_in(KEY_FILE)


def key_in(path) -> str:
    """The key kept in a key file, or "" (no file, or one that won't open: a sealed file whose key is gone is set
    aside by open_text, never lost)."""
    if not path.exists():
        return ""
    try:
        return str(json.loads(open_text(path)).get("key", "") or "")
    except (OSError, ValueError, AttributeError):
        log.exception("Couldn't read the YouTube key")
        return ""


def set_key(key: str) -> str:
    """Keeps his YouTube Data API key (sealed at rest); an empty one removes it. ValueError for one that can't be a
    key. Returns what happened, never the key."""
    key = str(key or "").strip()
    if not key:
        if KEY_FILE.exists():
            KEY_FILE.unlink()
        return "The YouTube key is removed."
    if not re.fullmatch(r"[A-Za-z0-9_-]{20,60}", key):
        raise ValueError("That doesn't look like a YouTube API key (it's about 39 letters and numbers).")
    KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(KEY_FILE, json.dumps({"key": key}))
    return "YouTube search is set up."


def _fetch(url: str) -> bytes:
    """GETs YouTube's API with a short timeout."""
    import urllib.request

    request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "MIA"})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as answer:
        return answer.read()


def results_from(payload: dict) -> list[dict]:
    """Pure logic. YouTube's search answer as songs: [{video_id, title, channel, thumb}], only well-formed ids, titles
    unescaped and cut to a sane length."""
    found = []
    for item in (payload or {}).get("items", []) or []:
        vid = str(((item or {}).get("id") or {}).get("videoId", ""))
        snippet = (item or {}).get("snippet") or {}
        if not _ID.match(vid):
            continue
        thumbs = snippet.get("thumbnails") or {}
        thumb = ((thumbs.get("medium") or thumbs.get("default") or {}).get("url", ""))
        found.append({"video_id": vid, "title": html.unescape(str(snippet.get("title", "")))[:150] or "Untitled",
                      "channel": html.unescape(str(snippet.get("channelTitle", "")))[:80],
                      "thumb": thumb if str(thumb).startswith("https://i.ytimg.com/") else ""})
    return found


def search(context, words: str, fetch: Optional[Callable[[str], bytes]] = None, limit: int = LIMIT) -> list[dict]:
    """Songs on YouTube for his words (see the module's opening). NeedsKey without a key; RuntimeError when it isn't
    allowed now or YouTube can't be reached, with why."""
    from core.online_lookup import allowed, scrub

    ok, why = allowed(context)
    if not ok:
        raise RuntimeError(why)
    words = scrub(words)[:150]
    if not words:
        raise RuntimeError("What should I look for?")
    key = _key()
    if not key:
        raise NeedsKey("YouTube search needs a YouTube Data API key of your own (free, from Google Cloud Console: "
                       "make a project, turn on YouTube Data API v3, create an API key), entered in Music → "
                       "YouTube. A YouTube link you paste plays without one.")
    url = SEARCH_URL + "?" + urlencode({"part": "snippet", "type": "video", "videoCategoryId": "10",
                                         "maxResults": max(1, min(limit, 25)), "q": words, "key": key,
                                         "safeSearch": "moderate"})
    try:
        payload = json.loads((fetch or _fetch)(url))
    except Exception as problem:  # noqa: BLE001 - the key never goes into the message
        log.warning("YouTube search failed: %s", type(problem).__name__)
        raise RuntimeError("YouTube didn't answer (no internet, or the key isn't working).") from None
    return results_from(payload)[:limit]
