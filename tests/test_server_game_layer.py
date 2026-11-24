"""
tests.test_server_game_layer
==============================

The game layer's routes on the real server (server/app.py): the Achievements page and the cards not yet seen, a
card closed (POST /api/achievements/seen, refused with no ids), YouTube search without a key saying how to get one,
the key refused when it can't be one and never echoed back, and the page's security policy allowing only YouTube's
player and thumbnails from outside. Each refuses a stranger.
And the browser's tab-icon request answered without an error.
"""

from __future__ import annotations

import pytest

import core.music_manager as music_module
import core.youtube_music as yt
from tests.test_server_app import _login, _profile_id, client, context  # noqa: F401  (the server's own fixtures)


@pytest.fixture
def owner(client, context, tmp_path, monkeypatch):  # noqa: F811
    """The signed-in owner's headers, with the music library and the YouTube key file in a temporary folder.
    Nothing reaches YouTube from a test."""
    data = tmp_path / "music_data"
    data.mkdir()
    monkeypatch.setattr(music_module, "_TRACKS_FILE", data / "music_tracks.json")
    monkeypatch.setattr(music_module, "_PLAYLISTS_FILE", data / "music_playlists.json")
    monkeypatch.setattr(yt, "KEY_FILE", data / "youtube_key.json")
    monkeypatch.setattr(yt, "_fetch", lambda url: (_ for _ in ()).throw(OSError("no network in tests")))
    return {"Authorization": f"Bearer {_login(client, context)}"}


def test_an_unlock_is_offered_as_a_card_once_and_is_in_the_log(client, context, owner):  # noqa: F811
    """A reward unlocked shows in /api/achievements/new; closed, it's gone from there and stays in the page's log."""
    from core import progress_history

    progress_history.subscribe(context)
    context.profiles.unlock_reward(_profile_id(context), "eggs_first_dozen")
    offered = client.get("/api/achievements/new", headers=owner).json()
    assert [c["id"] for c in offered["cards"]] == ["eggs_first_dozen"]
    assert client.post("/api/achievements/seen", json={"ids": []}, headers=owner).status_code == 400
    assert client.post("/api/achievements/seen", json={"ids": ["eggs_first_dozen"]}, headers=owner).status_code == 200
    assert client.get("/api/achievements/new", headers=owner).json()["cards"] == []
    page = client.get("/api/achievements", headers=owner).json()
    assert page["earned"][0]["name"] == "First Dozen"


def test_youtube_search_without_a_key_says_how_and_the_key_is_never_echoed(client, owner):  # noqa: F811
    """No key: needs_key with the steps. A bad key is refused; a good one is kept, and nothing sent back holds it."""
    found = client.get("/api/music/youtube/search?q=wagon%20wheel", headers=owner).json()
    assert found["needs_key"] and "YouTube Data API" in found["problem"]
    assert client.post("/api/music/youtube/key", json={"key": "nope"}, headers=owner).status_code == 400
    key = "AIza" + "x" * 35
    answer = client.post("/api/music/youtube/key", json={"key": key}, headers=owner)
    assert answer.status_code == 200 and key not in answer.text
    assert yt.has_key()
    assert key not in client.get("/api/music", headers=owner).text


def test_the_routes_refuse_a_stranger_and_the_policy_allows_only_youtubes_player(client):  # noqa: F811
    """No sign-in, no answer; the security policy frames only youtube-nocookie and loads images only from ytimg."""
    for path in ("/api/achievements", "/api/achievements/new", "/api/music/youtube/search?q=x"):
        assert client.get(path).status_code == 401
    assert client.post("/api/achievements/seen", json={"ids": ["x"]}).status_code == 401
    policy = client.get("/api/health").headers["Content-Security-Policy"]
    assert "frame-src https://www.youtube-nocookie.com;" in policy and "https://i.ytimg.com" in policy
    assert "script-src 'self';" in policy


def test_a_song_asked_for_by_voice_is_offered_to_the_frame_once(client, context, owner):  # noqa: F811
    """play_on_youtube with a link: /api/music/youtube/next offers it; once the frame says it started, it's not offered
    again."""
    from core.personal_data import view_for
    from core.youtube_actions import _play

    _play(view_for(context, _profile_id(context)), {"query": "https://youtu.be/ccccccccccc"})
    assert client.get("/api/music/youtube/next", headers=owner).json()["video_id"] == "ccccccccccc"
    assert client.post("/api/music/youtube/next/played", headers=owner).status_code == 200
    assert client.get("/api/music/youtube/next", headers=owner).json() == {}


def test_the_browsers_tab_icon_request_is_answered_without_an_error(client):  # noqa: F811
    """/favicon.ico, asked for by every browser, gets 204 (no icon yet), not a 404 in the console."""
    assert client.get("/favicon.ico").status_code == 204
