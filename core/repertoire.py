"""
core.repertoire
=================

The songs he can play (the game layer, Zac 2026-11-24: "sometimes its a song unlocked on the guitar"). A song
learned on an instrument is a `song_learned` life event in his own history, so it's dated, undone by "undo that"
(`life_events.reversed_ids`), and never kept twice. The list (`songs`) and its count (`count`, the rewards stat
`songs_learned`, core/rewards_manager.py's Songbook chain) are read from those events, and an objective can count
them ("learn 3 songs this month", core/mission_trophies.STATS).

Used by the action `song.learned` (Music's "Can Play" tab) and the tools `learned_a_song` and `songs_i_can_play`
(core/repertoire_actions.py). The guitar path's own check "play one whole song through" stays where it is
(core/guitar.py); this is the songbook it fills.
"""

from __future__ import annotations

from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

INSTRUMENTS = ("guitar", "banjo", "mandolin", "ukulele", "bass", "fiddle", "piano", "harmonica", "drums", "voice")


def _where(context):
    """Where his songs are kept: his own history (the household's when there's no personal one)."""
    return getattr(context, "personal_life_events", None) or getattr(context, "life_events", None)


def _clean(text: str, limit: int = 80) -> str:
    """Pure logic. Words with their spaces tidied and cut to a sane length."""
    return " ".join(str(text or "").split())[:limit]


def instrument_of(said: str) -> str:
    """Pure logic. The instrument he named (one of `INSTRUMENTS`, "singing" as voice), or guitar when he named none."""
    said = str(said or "").lower()
    if "sing" in said:
        return "voice"
    return next((i for i in INSTRUMENTS if i in said), "guitar")


def songs(context) -> list[dict]:
    """The songs he can play, newest first: [{song, artist, instrument, when, event_id}], an undone one left out."""
    from core import life_events

    try:
        events = life_events.events_for(context, types=("song_learned", "undone"))
    except Exception:  # noqa: BLE001 - a history that can't be read lists nothing
        log.exception("Couldn't read the songs learned")
        return []
    undone = life_events.reversed_ids(events)
    return [{"song": e.payload.get("song", ""), "artist": e.payload.get("artist", ""),
             "instrument": e.payload.get("instrument", "guitar"), "when": e.at, "event_id": e.event_id}
            for e in events if e.type == "song_learned" and e.event_id not in undone]


def count(context) -> float:
    """How many songs he can play (each song on each instrument once)."""
    return float(len(songs(context)))


def learned(context, song: str, instrument: str = "", artist: str = "") -> str:
    """Adds a song he can now play, dated today, and says so; ValueError for no song or one already in his songbook on
    that instrument. Said as activity.logged, so a Songbook tier or a mission counting songs moves at once."""
    from core import life_events

    song, artist, instrument = _clean(song), _clean(artist, 60), instrument_of(instrument or "guitar")
    if not song:
        raise ValueError("Which song?")
    if any(s["song"].lower() == song.lower() and s["instrument"] == instrument for s in songs(context)):
        raise ValueError(f"{song} is already in your songbook on {instrument}.")
    where = _where(context)
    if where is None:
        raise ValueError("Your songbook isn't on this MIA.")
    life_events.record(where, "song_learned", f"Learned {song} on {instrument}", [],
                       {"song": song, "artist": artist, "instrument": instrument})
    events = getattr(context, "events", None)
    if events is not None:
        events.publish("activity.logged", source="repertoire", category="song_learned")
    n = len(songs(context))
    return f"{song} is in your songbook on {instrument}. That's {n} song{'s' if n != 1 else ''} you can play."


def say(context, instrument: Optional[str] = None) -> str:
    """The songs he can play (on one instrument when he names it), newest first, ten at most."""
    found = songs(context)
    if instrument:
        found = [s for s in found if s["instrument"] == instrument_of(instrument)]
    if not found:
        return "No songs in your songbook yet. When you can play one through, tell me \"I learned ... on guitar\"."
    names = [s["song"] + (f" ({s['artist']})" if s["artist"] else "") + (f" on {s['instrument']}"
                                                                        if s["instrument"] != "guitar" else "")
             for s in found[:10]]
    more = f", and {len(found) - 10} more" if len(found) > 10 else ""
    return f"You can play {len(found)} song{'s' if len(found) != 1 else ''}: " + "; ".join(names) + more + "."
