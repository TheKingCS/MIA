"""
tests.test_repertoire
=======================

His songbook (core/repertoire.py): a song learned is dated in his own history, never twice on the same instrument,
counted toward the Songbook achievements at once and by a mission objective, and taken back by "undo that".
"""

import pytest

from core import life_events, progress_history, repertoire
from core.actions import ACTION_TYPES, ActionCenter, ActionError
from core.repertoire_actions import _learned, _list
from core.rewards_manager import RewardsManager
from tests.engine_world import build_world


def _world(tmp_path, monkeypatch):
    """The engine's small household with rewards and unlocks kept in the history."""
    world = build_world(tmp_path, monkeypatch)
    world.rewards = RewardsManager(world)
    progress_history.subscribe(world)
    return world


def test_a_song_learned_is_in_his_own_history_once_per_instrument(tmp_path, monkeypatch):
    """Wagon Wheel on guitar, then on banjo: two; on guitar again: refused. Kept in his own folder, not the
    household's."""
    world = _world(tmp_path, monkeypatch)
    assert "1 song" in repertoire.learned(world, "Wagon Wheel")
    repertoire.learned(world, "Wagon Wheel", "on the banjo")
    with pytest.raises(ValueError):
        repertoire.learned(world, "wagon wheel", "guitar")
    assert [(s["song"], s["instrument"]) for s in repertoire.songs(world)] == [("Wagon Wheel", "banjo"),
                                                                                ("Wagon Wheel", "guitar")]
    mine = life_events.LifeEventLog(world, data_dir=world.me.data_dir)
    assert len([e for e in mine.all_events() if e.type == "song_learned"]) == 2


def test_the_first_song_unlocks_its_achievement_at_once_and_a_mission_counts_songs(tmp_path, monkeypatch):
    """First Song unlocks the moment it's added; "learn 2 songs" counts only the ones after it was set."""
    world = _world(tmp_path, monkeypatch)
    repertoire.learned(world, "Country Roads")
    assert world.rewards.is_unlocked(world.me.profile_id, "songbook_first_song")
    mission = world.missions.add_mission("Campfire set", profile_id=world.me.profile_id)
    world.missions.add_objective(mission.mission_id, "2 songs learned", "records", 2, stat_id="songs_learned")
    repertoire.learned(world, "Ring of Fire")
    assert world.missions.objective_progress(mission.mission_id, 0) == 1


def test_from_the_screen_it_asks_first_and_undo_takes_it_back(tmp_path, monkeypatch):
    """song.learned is refused with no song; approved, it's in the songbook; undone, it's gone."""
    world = _world(tmp_path, monkeypatch)
    with pytest.raises(ActionError):
        ACTION_TYPES["song.learned"].describe(world, {"song": " "})
    center = ActionCenter()
    proposal = center.propose(world, "song.learned", {"song": "Jolene", "instrument": "guitar"})
    center.approve(world, proposal.proposal_id)
    assert repertoire.count(world) == 1
    center.undo(world, proposal.proposal_id)
    assert repertoire.count(world) == 0


def test_by_voice_he_adds_a_song_and_hears_his_songbook(tmp_path, monkeypatch):
    """learned_a_song and songs_i_can_play; a repeat is said, not an error."""
    world = _world(tmp_path, monkeypatch)
    assert "No songs" in _list(world, {})
    _learned(world, {"song": "Wagon Wheel", "artist": "Old Crow Medicine Show"})
    assert "already" in _learned(world, {"song": "Wagon Wheel"})
    assert "Wagon Wheel (Old Crow Medicine Show)" in _list(world, {})
