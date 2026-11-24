"""
core.youtube_actions
======================

YouTube in Music, from the screen and by voice (core/youtube_music.py; DEC-0125, both ways).

The action `youtube.save` keeps a YouTube song in the library as a link (and on a playlist, when one is named),
from the Music page's YouTube tab. The tools: `find_on_youtube` says the top songs for his words;
`save_from_youtube` saves the top one (or a link he gave) and can put it on a playlist; `play_on_youtube` saves it
and sets it as MIA's pick (`music.youtube_next`): the page he has open starts it in a small YouTube player (web/shell.js,
`pick` and `played`), and it waits at the top of Music to play again. A search needs his YouTube key; a link never does. Removing a saved
song is the library's own `track.delete`.
"""

from __future__ import annotations

from core.actions import ACTION_TYPES, ActionError, ActionType
from core.assistant_actions import AssistantAction

NEXT_KEY = "music.youtube_next"  # MIA's pick: {track_id, title, video_id, at, played}


def pick(context) -> dict:
    """MIA's pick by voice not yet played, for the frame's small player: {track_id, title, video_id, at}, or {}."""
    found = context.config.get(NEXT_KEY) if getattr(context, "config", None) is not None else None
    if not isinstance(found, dict) or found.get("played") or not found.get("video_id"):
        return {}
    return {k: found.get(k, "") for k in ("track_id", "title", "video_id", "at")}


def played(context) -> None:
    """The frame started MIA's pick: marked played (bookkeeping, outside undo), so it isn't started again. It stays
    at the top of Music to play again."""
    from core import undo_log

    found = context.config.get(NEXT_KEY)
    if isinstance(found, dict) and not found.get("played"):
        with undo_log.outside_undo():
            context.config.set(NEXT_KEY, {**found, "played": True})
            context.config.save()


def _music(context):
    """The music library, or ActionError."""
    music = getattr(context, "music", None)
    if music is None:
        raise ActionError("Music isn't on this MIA.")
    return music


def _playlist(context, params):
    """The playlist the params name (by id), None when none is named, ActionError when it's gone."""
    pid = str(params.get("playlist_id", "") or "").strip()
    if not pid:
        return None
    found = _music(context).get_playlist(pid)
    if found is None:
        raise ActionError("That playlist isn't there anymore.")
    return found


def _video(params) -> str:
    """The video id from the params (a link or an id), or ActionError."""
    from core.youtube_music import video_id

    vid = video_id(params.get("video", ""))
    if not vid:
        raise ActionError("That isn't a YouTube link.")
    return vid


def _title(params) -> str:
    """The song's title as given, or "this YouTube song"."""
    return " ".join(str(params.get("title", "") or "").split())[:150] or "this YouTube song"


def _describe_save(context, params) -> str:
    """What youtube.save says: the song kept, and the playlist it goes on."""
    _video(params)
    playlist = _playlist(context, params)
    return f"Save {_title(params)} to your music" + (f" and the playlist {playlist.name}" if playlist else "")


def _save(context, params) -> str:
    """Does youtube.save: the link in the library (a pasted link named by YouTube's oEmbed when it has no title), and
    on the playlist when one is named."""
    from core.youtube_music import title_of

    music, playlist = _music(context), _playlist(context, params)
    vid, title, channel = _video(params), str(params.get("title", "") or ""), str(params.get("channel", "") or "")
    if not title.strip():  # a pasted link: its name from YouTube, when it can be had
        named = title_of(context, vid)
        title, channel = named.get("title", ""), channel or named.get("channel", "")
    track = music.add_youtube(vid, title, channel)
    if playlist is not None:
        music.add_track_to_playlist(playlist.playlist_id, track.track_id)
        return f"Saved {track.title} and put it on {playlist.name}."
    return f"Saved {track.title} to your music."


YOUTUBE_ACTIONS = {k.kind: k for k in (
    ActionType("youtube.save", "Save", {"video": "a YouTube link or id", "title": "its title", "channel": "optional",
                                        "playlist_id": "a playlist (optional)"}, _describe_save, _save),
)}
ACTION_TYPES.update(YOUTUBE_ACTIONS)


def _found(context, words: str):
    """(songs, None) for his words or a link, or (None, what to say instead)."""
    from core.youtube_music import NeedsKey, search, video_id

    vid = video_id(words)
    if vid:
        return [{"video_id": vid, "title": "", "channel": ""}], None
    try:
        songs = search(context, words, limit=5)
    except NeedsKey as problem:
        return None, str(problem)
    except RuntimeError as problem:
        return None, str(problem)
    return (songs, None) if songs else (None, f"Nothing on YouTube for {words}.")


def _named_playlist(context, name: str):
    """The playlist whose name matches (case aside), or None."""
    name = " ".join(str(name or "").lower().split())
    music = getattr(context, "music", None)
    return next((p for p in (music.all_playlists() if music else []) if p.name.lower() == name), None) if name else None


def _find(context, arguments: dict) -> str:
    """Tool find_on_youtube: the top songs for his words, by title and channel (from the web: names only)."""
    songs, problem = _found(context, str(arguments.get("query", "") or ""))
    if songs is None:
        return problem
    return "On YouTube: " + "; ".join(f"{s['title']}" + (f" ({s['channel']})" if s["channel"] else "")
                                      for s in songs) + ". Say which one to save or play."


def _keep(context, arguments: dict):
    """Saves the top song for his words (or his link), on the named playlist too: (track, what was said) or (None,
    why not)."""
    songs, problem = _found(context, str(arguments.get("query", "") or ""))
    if songs is None:
        return None, problem
    top = songs[0]
    params = {"video": top["video_id"], "title": top["title"], "channel": top["channel"]}
    wanted = str(arguments.get("playlist", "") or "").strip()
    if wanted:
        playlist = _named_playlist(context, wanted)
        if playlist is None:
            return None, f"There's no playlist called {wanted}."
        params["playlist_id"] = playlist.playlist_id
    try:
        ACTION_TYPES["youtube.save"].describe(context, params)
        said = ACTION_TYPES["youtube.save"].execute(context, params)
    except ActionError as problem:
        return None, str(problem)
    return context.music.add_youtube(top["video_id"], top["title"], top["channel"]), said


def _framed(said: str) -> str:
    """What the tool says, framed as text from the web for the model: a song's title is YouTube's words."""
    from core.browser_safety import untrusted

    return untrusted(said, "https://www.youtube.com")


def _save_tool(context, arguments: dict) -> str:
    """Tool save_from_youtube: the top song (or his link) kept in the library, on a playlist if he named one; framed
    as web text (`_framed`)."""
    track, said = _keep(context, arguments)
    return _framed(said) if track is not None else said


def _play(context, arguments: dict) -> str:
    """Tool play_on_youtube: the top song saved and set as MIA's pick on the Music page, one press to play; framed as
    web text (`_framed`).
    The pick carries its video id and when it was asked, so the page open starts it in a small player once."""
    track, said = _keep(context, arguments)
    if track is None:
        return said
    from datetime import datetime

    context.config.set(NEXT_KEY, {"track_id": track.track_id, "title": track.title, "video_id": track.youtube_id,
                                  "at": datetime.now().isoformat(timespec="seconds"), "played": False})
    context.config.save()
    return _framed(f"{said} It's playing in a small YouTube player on the page you have open (or press play at the "
                   f"top of Music).")


def register_youtube_actions(registry) -> None:
    """Registers find_on_youtube, save_from_youtube and play_on_youtube (reached by "on YouTube" and "from YouTube",
    never a bare "play", which is the library's own play_track)."""
    query = {"type": "string", "description": "the song or artist to look for, or a YouTube link"}
    registry.register(AssistantAction(
        name="find_on_youtube", domain="music",
        description="Look a song or artist up on YouTube and say the top results (needs his YouTube key; a link "
                    "doesn't). To keep one, save_from_youtube; to hear it, play_on_youtube.",
        parameters={"type": "object", "properties": {"query": query}, "required": ["query"]},
        handler=_find, trigger_phrases=("find on youtube", "search youtube", "look on youtube", "look up on youtube",
                                        "youtube for"),
    ))
    registry.register(AssistantAction(
        name="save_from_youtube", domain="music",
        description="Save a song from YouTube into his music as a link (the top result for his words, or the link "
                    "he gave), on a playlist if he names one. Nothing is downloaded.",
        parameters={"type": "object", "properties": {
            "query": query, "playlist": {"type": "string", "description": "a playlist's name, only if he said one"}},
            "required": ["query"]},
        handler=_save_tool, trigger_phrases=("save from youtube", "add from youtube", "from youtube to my",
                                             "save it from youtube"),
    ))
    registry.register(AssistantAction(
        name="play_on_youtube", domain="music",
        description="Play a song from YouTube: saves the top result (or his link) and puts it ready to play on the "
                    "Music page. Songs in his own library are play_track's.",
        parameters={"type": "object", "properties": {"query": query}, "required": ["query"]},
        handler=_play, trigger_phrases=("play on youtube", "play from youtube", "play it on youtube",
                                        "put on youtube"),
    ))
