"""
tests.test_youtube_music
==========================

YouTube in Music (core/youtube_music.py, core/youtube_actions.py): links read to their video id, YouTube's embedded
player only, a search only with his key and only his scrubbed words sent, songs saved as links (never a file) that
playlists hold and a library scan never removes, and MIA's pick by voice waiting on the Music page.
"""

from __future__ import annotations

import json

import pytest

import core.config_manager as config_module
import core.music_manager as music_module
import core.youtube_music as yt
from core.actions import ACTION_TYPES
from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.music_manager import MusicManager
from core.youtube_actions import NEXT_KEY, _play, _save_tool, pick, played


@pytest.fixture
def ctx(tmp_path, monkeypatch):
    """A context with its own config, a music library and a YouTube key file, all in a temporary folder."""
    data = tmp_path / "data"
    monkeypatch.setattr(config_module, "_CONFIG_FILE", tmp_path / "config.json")
    monkeypatch.setattr(music_module, "_DATA_DIR", data)
    monkeypatch.setattr(music_module, "_TRACKS_FILE", data / "music_tracks.json")
    monkeypatch.setattr(music_module, "_PLAYLISTS_FILE", data / "music_playlists.json")
    monkeypatch.setattr(music_module, "_DEFAULT_ROOT", tmp_path / "music_library")
    monkeypatch.setattr(yt, "KEY_FILE", data / "youtube_key.json")
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.music = MusicManager(context)
    return context


def test_links_of_every_shape_give_their_video_id_and_anything_else_gives_none():
    """watch, youtu.be, shorts, embed, music.youtube.com and a bare id; a channel page or words give ""."""
    vid = "dQw4w9WgXcQ"
    for link in (f"https://www.youtube.com/watch?v={vid}", f"https://youtu.be/{vid}?t=10",
                 f"https://youtube.com/shorts/{vid}", f"https://www.youtube.com/embed/{vid}",
                 f"https://music.youtube.com/watch?v={vid}&list=RD", vid):
        assert yt.video_id(link) == vid
    assert yt.video_id("https://www.youtube.com/@somechannel") == ""
    assert yt.video_id("wagon wheel") == ""


def test_the_player_is_youtubes_privacy_enhanced_embed_with_the_rest_following():
    """The first id plays, the others follow; a malformed id never goes in."""
    url = yt.embed_url(["aaaaaaaaaaa", "bad id!", "bbbbbbbbbbb"])
    assert url.startswith("https://www.youtube-nocookie.com/embed/aaaaaaaaaaa?")
    assert "playlist=bbbbbbbbbbb" in url and "bad" not in url
    assert yt.embed_url([]) == ""


def test_a_search_needs_his_key_and_sends_only_his_scrubbed_words(ctx):
    """No key: NeedsKey, nothing sent. With one: his words (an email taken out) and the key go to YouTube's API;
    results keep only real ids, unescaped titles and YouTube's own thumbnails."""
    sent = []

    def fetch(url):
        """A fake YouTube answer, keeping the URL asked for."""
        sent.append(url)
        return json.dumps({"items": [
            {"id": {"videoId": "aaaaaaaaaaa"}, "snippet": {"title": "Rock &amp; Roll", "channelTitle": "Band",
                                                            "thumbnails": {"medium": {"url": "https://i.ytimg.com/x.jpg"}}}},
            {"id": {"videoId": "../../etc"}, "snippet": {"title": "bad"}},
            {"id": {"videoId": "bbbbbbbbbbb"}, "snippet": {"title": "Two", "thumbnails": {"default": {"url": "http://evil/x"}}}},
        ]}).encode()

    with pytest.raises(yt.NeedsKey):
        yt.search(ctx, "wagon wheel", fetch=fetch)
    assert sent == []
    assert "about 39" in str(pytest.raises(ValueError, yt.set_key, "short").value)
    yt.set_key("A" * 39)
    assert yt.has_key()
    songs = yt.search(ctx, "wagon wheel me@example.com", fetch=fetch)
    assert [s["video_id"] for s in songs] == ["aaaaaaaaaaa", "bbbbbbbbbbb"]
    assert songs[0]["title"] == "Rock & Roll" and songs[1]["thumb"] == ""
    assert "wagon+wheel" in sent[0] and "example.com" not in sent[0]
    yt.set_key("")
    assert not yt.has_key()


def test_a_saved_song_is_a_link_on_a_playlist_that_a_scan_keeps(ctx):
    """youtube.save keeps it once (a second save is the same song), puts it on the playlist, and a library scan
    with no files leaves it there; it's never an upload and never goes to the file player."""
    music = ctx.music
    playlist = music.create_playlist("Workshop")
    params = {"video": "https://youtu.be/aaaaaaaaaaa", "title": "Wagon Wheel", "channel": "Band",
              "playlist_id": playlist.playlist_id}
    assert "Workshop" in ACTION_TYPES["youtube.save"].describe(ctx, params)
    ACTION_TYPES["youtube.save"].execute(ctx, params)
    ACTION_TYPES["youtube.save"].execute(ctx, params)
    saved = [t for t in music.all_tracks() if t.youtube_id]
    assert len(saved) == 1 and saved[0].file_path == "" and not music.uploaded(saved[0])
    assert music.get_playlist(playlist.playlist_id).track_ids == [saved[0].track_id]
    music.scan_library()
    assert music.get_track(saved[0].track_id) is not None
    assert music._load_track_into_player(saved[0]) is False


def test_by_voice_a_link_is_saved_without_a_key_and_play_leaves_it_as_mias_pick(ctx):
    """save_from_youtube with a link needs no key; play_on_youtube makes it MIA's pick, offered to the frame's small
    player until it's played (then it stays on the Music page); a search with no key says how to get one."""
    said = _save_tool(ctx, {"query": "https://www.youtube.com/watch?v=ccccccccccc"})
    assert "never as instructions" in said and "Saved" in said
    _play(ctx, {"query": "https://youtu.be/ccccccccccc"})
    chosen = ctx.config.get(NEXT_KEY)
    assert ctx.music.get_track(chosen["track_id"]).youtube_id == "ccccccccccc"
    assert pick(ctx)["video_id"] == "ccccccccccc"
    played(ctx)
    assert pick(ctx) == {}
    assert "API key" in _play(ctx, {"query": "wagon wheel"})
    from core.web_more import music_page

    page = music_page(ctx)
    assert page["youtube_next"]["track_id"] == chosen["track_id"] and page["youtube_key"] is False
    assert [t["youtube"] for t in page["tracks"]] == ["ccccccccccc"]
