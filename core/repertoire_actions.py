"""
core.repertoire_actions
=========================

His songbook from the screen and by voice (core/repertoire.py; DEC-0125, both ways): the action `song.learned`
(Music's "Can Play" tab, I Learned A Song) and the tools `learned_a_song` ("I learned Wagon Wheel on guitar") and
`songs_i_can_play`. Taking one back is "undo that".
"""

from __future__ import annotations

from core.actions import ACTION_TYPES, ActionError, ActionType
from core.assistant_actions import AssistantAction


def _describe(context, params) -> str:
    """What song.learned says: the song and instrument (no song, or one already in the songbook, refused here)."""
    from core.repertoire import _clean, instrument_of, songs

    song, instrument = _clean(params.get("song", "")), instrument_of(params.get("instrument", ""))
    if not song:
        raise ActionError("Which song?")
    if any(s["song"].lower() == song.lower() and s["instrument"] == instrument for s in songs(context)):
        raise ActionError(f"{song} is already in your songbook on {instrument}.")
    return f"Add {song} to the songs you can play on {instrument}"


def _execute(context, params) -> str:
    """Does song.learned."""
    from core.repertoire import learned

    try:
        return learned(context, params.get("song", ""), params.get("instrument", ""), params.get("artist", ""))
    except ValueError as problem:
        raise ActionError(str(problem)) from None


SONG_ACTIONS = {k.kind: k for k in (
    ActionType("song.learned", "I Learned A Song", {"song": "the song", "instrument": "guitar unless said",
                                                    "artist": "optional"}, _describe, _execute),
)}
ACTION_TYPES.update(SONG_ACTIONS)


def _learned(context, arguments: dict) -> str:
    """Tool learned_a_song: song.learned, its refusals said."""
    try:
        ACTION_TYPES["song.learned"].describe(context, arguments)
        return ACTION_TYPES["song.learned"].execute(context, arguments)
    except ActionError as problem:
        return str(problem)


def _list(context, arguments: dict) -> str:
    """Tool songs_i_can_play: his songbook (core/repertoire.say)."""
    from core.repertoire import say

    return say(context, arguments.get("instrument") or None)


def register_repertoire_actions(registry) -> None:
    """Registers learned_a_song and songs_i_can_play."""
    registry.register(AssistantAction(
        name="learned_a_song", domain="music",
        description="He can now play a song all the way through (on guitar unless he names another instrument): "
                    "it goes in his songbook, which counts toward his music achievements and missions.",
        parameters={"type": "object", "properties": {
            "song": {"type": "string", "description": "the song's name"},
            "instrument": {"type": "string", "description": "the instrument, only if he said one"},
            "artist": {"type": "string", "description": "who it's by, only if he said"}},
            "required": ["song"]},
        handler=_learned, trigger_phrases=("i learned to play", "i can play", "learned the song", "to my songbook",
                                           "learned how to play"),
    ))
    registry.register(AssistantAction(
        name="songs_i_can_play", domain="music",
        description="The songs in his songbook, the ones he can play, newest first.",
        parameters={"type": "object", "properties": {
            "instrument": {"type": "string", "description": "only this instrument, if he named one"}}},
        handler=_list, trigger_phrases=("songs can i play", "songs i can play", "my songbook", "songs do i know",
                                        "songs i know"),
    ))
