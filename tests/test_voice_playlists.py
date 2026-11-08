"""
tests.test_voice_playlists
============================

Playlists by voice (DEC-0125, core/assistant_playlist_actions.py): listed,
made, a song added ("this song" is the one playing), taken off, renamed and
deleted, each through the Music screen's own action.
"""

from types import SimpleNamespace

from core import assistant_playlist_actions as pl


class _Actions:
    """Keeps each proposal and runs it."""

    def __init__(self):
        """Nothing yet."""
        self.proposed = []

    def propose(self, context, kind, params, proposed_by):
        """Keeps it."""
        self.proposed.append((kind, params))
        return SimpleNamespace(proposal_id="p")

    def approve(self, context, proposal_id):
        """Done."""
        return SimpleNamespace(status="executed", result="Done.")


def _context(playing="t2"):
    """A library of two songs, one playlist holding the first, and the second playing."""
    tracks = {"t1": SimpleNamespace(track_id="t1", title="Barn Dance"), "t2": SimpleNamespace(track_id="t2", title="Slow River")}
    shop = SimpleNamespace(playlist_id="p1", name="Shop Music")
    music = SimpleNamespace(
        all_playlists=lambda: [shop], all_tracks=lambda: list(tracks.values()), get_track=tracks.get,
        tracks_for_playlist=lambda pid: [tracks["t1"]] if pid == "p1" else [],
        now_playing=lambda: SimpleNamespace(track_id=playing) if playing else None)
    return SimpleNamespace(music=music, actions=_Actions())


def test_playlists_are_listed_with_their_song_counts():
    """Read only."""
    assert pl._action_list_playlists(_context(), {}) == "Your playlists: Shop Music (1 song)."


def test_each_change_runs_the_music_screen_s_own_action():
    """Make, add (this song is the one playing), remove, rename, delete."""
    cases = [
        (pl._action_make_playlist, {"name": "Garage Music"}, ("playlist.add", {"name": "Garage Music"})),
        (pl._action_add_to_playlist, {"song": "this song", "playlist": "shop music"},
         ("playlist.add_track", {"playlist_id": "p1", "track_id": "t2"})),
        (pl._action_add_to_playlist, {"song": "slow river", "playlist": "shop"},
         ("playlist.add_track", {"playlist_id": "p1", "track_id": "t2"})),
        (pl._action_remove_from_playlist, {"song": "barn dance", "playlist": "shop music"},
         ("playlist.remove_track", {"playlist_id": "p1", "track_id": "t1"})),
        (pl._action_rename_playlist, {"playlist": "shop music", "name": "Garage Music"},
         ("playlist.rename", {"playlist_id": "p1", "name": "Garage Music"})),
        (pl._action_delete_playlist, {"playlist": "shop music"}, ("playlist.delete", {"playlist_id": "p1"})),
    ]
    for handler, args, expected in cases:
        c = _context()
        handler(c, args)
        assert c.actions.proposed == [expected], handler.__name__


def test_this_song_with_nothing_playing_is_asked_about():
    """Nothing playing: she asks which song, nothing changes."""
    c = _context(playing=None)
    assert pl._action_add_to_playlist(c, {"song": "this song", "playlist": "shop"}) == "Nothing's playing. Which song?"
    assert not c.actions.proposed
