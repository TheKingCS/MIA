"""
core.assistant_playlist_actions
=================================

Playlists by voice (DEC-0125, 2026-11-08): Music could play a playlist out
loud but not make or change one; the screen's five playlist kinds had no
voice twin. Five tools, each through the screen's own action
(core/assistant_correction_actions.py `_run`, so "undo that" works):

- list_playlists ("what playlists do I have?"), read only;
- make_playlist ("make a playlist called Shop Music"): playlist.add;
- add_to_playlist ("add this song to Shop Music"): playlist.add_track, the
  song named or, for "this song", the one playing now;
- remove_from_playlist, rename_playlist, delete_playlist.
"""

from __future__ import annotations

from core.assistant_actions import AssistantAction, AssistantActionRegistry
from core.assistant_correction_actions import _one, _run

_THIS = ("", "this", "this song", "this one", "this track", "the song", "what's playing", "current song", "it")


def _music(context):
    """The music library, or None where this MIA has none."""
    return getattr(context, "music", None)


def _playlist(music, said):
    """The playlist named, or a question as a str."""
    return _one(music.all_playlists(), said, lambda p: p.name, "playlist")


def _song(music, said, among=None):
    """The song named (or, for "this song", the one playing now), or a question as a str."""
    said = " ".join(str(said or "").lower().split())
    if said in _THIS:
        playing = music.now_playing() if hasattr(music, "now_playing") else None
        if playing is None:
            return "Nothing's playing. Which song?"
        return music.get_track(playing.track_id)
    return _one(among if among is not None else music.all_tracks(), said, lambda t: t.title, "song")


def _action_list_playlists(context, arguments: dict) -> str:
    """Tool list_playlists: each playlist with how many songs it has."""
    music = _music(context)
    if music is None:
        return "There's no music library here."
    lists = music.all_playlists()
    if not lists:
        return "No playlists yet. Say \"make a playlist called ...\"."
    counts = {p.playlist_id: len(music.tracks_for_playlist(p.playlist_id)) for p in lists}
    return "Your playlists: " + ", ".join(
        f"{p.name} ({counts[p.playlist_id]} song{'' if counts[p.playlist_id] == 1 else 's'})" for p in lists) + "."


def _action_make_playlist(context, arguments: dict) -> str:
    """Tool make_playlist: a new, empty playlist with the name said (playlist.add)."""
    if _music(context) is None:
        return "There's no music library here."
    name = " ".join(str(arguments.get("name") or "").split())
    return _run(context, "playlist.add", {"name": name}) if name else "What should the playlist be called?"


def _action_add_to_playlist(context, arguments: dict) -> str:
    """Tool add_to_playlist: a song (the one playing for "this song") onto a playlist (playlist.add_track)."""
    music = _music(context)
    if music is None:
        return "There's no music library here."
    playlist = _playlist(music, arguments.get("playlist"))
    if isinstance(playlist, str):
        return playlist
    song = _song(music, arguments.get("song"))
    if isinstance(song, str) or song is None:
        return song or "I can't find that song."
    return _run(context, "playlist.add_track", {"playlist_id": playlist.playlist_id, "track_id": song.track_id})


def _action_remove_from_playlist(context, arguments: dict) -> str:
    """Tool remove_from_playlist: a song off a playlist (playlist.remove_track)."""
    music = _music(context)
    if music is None:
        return "There's no music library here."
    playlist = _playlist(music, arguments.get("playlist"))
    if isinstance(playlist, str):
        return playlist
    song = _song(music, arguments.get("song"), music.tracks_for_playlist(playlist.playlist_id))
    if isinstance(song, str) or song is None:
        return song or "That song isn't on it."
    return _run(context, "playlist.remove_track", {"playlist_id": playlist.playlist_id, "track_id": song.track_id})


def _action_rename_playlist(context, arguments: dict) -> str:
    """Tool rename_playlist: a playlist's new name (playlist.rename)."""
    music = _music(context)
    if music is None:
        return "There's no music library here."
    playlist = _playlist(music, arguments.get("playlist"))
    if isinstance(playlist, str):
        return playlist
    name = " ".join(str(arguments.get("name") or "").split())
    return _run(context, "playlist.rename", {"playlist_id": playlist.playlist_id, "name": name}) if name \
        else f"What should {playlist.name} be called?"


def _action_delete_playlist(context, arguments: dict) -> str:
    """Tool delete_playlist: deletes a playlist; its songs stay in the library (playlist.delete)."""
    music = _music(context)
    if music is None:
        return "There's no music library here."
    playlist = _playlist(music, arguments.get("playlist"))
    return playlist if isinstance(playlist, str) else _run(context, "playlist.delete",
                                                           {"playlist_id": playlist.playlist_id})


def register_playlist_actions(registry: AssistantActionRegistry) -> None:
    """Registers list_playlists, make_playlist, add_to_playlist, remove_from_playlist, rename_playlist and
    delete_playlist (music)."""
    registry.register_domain_keywords("music", ("playlist", "playlists"))
    def tool(name, description, properties, required, handler, phrases):
        """One tool, its parameters all strings."""
        registry.register(AssistantAction(
            name=name, domain="music", description=description,
            parameters={"type": "object", "properties": {k: {"type": "string", "description": v}
                                                         for k, v in properties.items()}, "required": required},
            handler=handler, trigger_phrases=phrases))

    tool("list_playlists", "The user's playlists and how many songs each has.", {}, [], _action_list_playlists,
         ("my playlists", "which playlists", "what playlists", "list playlists"))
    tool("make_playlist", "Make a new playlist.", {"name": "Its name."}, ["name"], _action_make_playlist,
         ("make a playlist", "new playlist", "create a playlist", "start a playlist"))
    tool("add_to_playlist", "Add a song to a playlist; 'this song' is the one playing now.",
         {"song": "The song's title, or 'this song'.", "playlist": "The playlist's name."}, ["playlist"],
         _action_add_to_playlist, ("to the playlist", "to my playlist", "to playlist", "add this song", "add the song"))
    tool("remove_from_playlist", "Take (remove) a song off a playlist, e.g. 'take X off the Y playlist'. Doesn't play "
         "anything.",
         {"song": "The song's title, or 'this song'.", "playlist": "The playlist's name."}, ["song", "playlist"],
         _action_remove_from_playlist, ("off the playlist", "from the playlist", "off my playlist", "from my playlist"))
    tool("rename_playlist", "Rename a playlist.", {"playlist": "Its name now.", "name": "The new name."},
         ["playlist", "name"], _action_rename_playlist, ("rename the playlist", "rename my playlist", "rename playlist"))
    tool("delete_playlist", "Delete a playlist (its songs stay in the library).", {"playlist": "The playlist's name."},
         ["playlist"], _action_delete_playlist, ("delete the playlist", "delete my playlist", "remove the playlist"))
