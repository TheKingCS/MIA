"""
tests.test_web_proposals
==========================

Mission ideas and field recordings on the web and by voice (core/web_proposals.py,
core/assistant_proposal_actions.py), on the real Discovery and Lite capture managers with their files in a temporary
folder.
"""

import pytest

import core.web_proposals as web_proposals
import tests.test_discovery_manager as discovery_tests
import tests.test_lite_capture_manager as capture_tests
from core.actions import ACTION_TYPES, ActionError
from core.assistant_proposal_actions import _decide_capture, _decide_idea, _list, _suggest
from core.lite_capture_manager import LiteCaptureManager


class _Model:
    """A stand-in model that always replies the same."""

    def __init__(self, reply):
        """Keeps the reply."""
        self.reply = reply

    def generate(self, prompt):
        """The reply, whatever the prompt."""
        return self.reply


@pytest.fixture
def ideas(tmp_path, monkeypatch):
    """A context with skills, missions and Discovery in a temporary folder, signed in as p1, with a model."""
    data_dir = discovery_tests.isolated_paths.__wrapped__(tmp_path, monkeypatch)
    discovery_tests._write_skill_definitions(data_dir)
    context = discovery_tests._make_context()
    discovery_tests._make_manager(context)
    context.llm = _Model(discovery_tests._WELL_FORMED_REPLY)
    monkeypatch.setattr(web_proposals, "_pid", lambda c: "p1")
    return context


def test_a_suggested_idea_waits_then_accepting_makes_a_mission_by_mia(ideas):
    assert web_proposals.mission_idea(ideas) == {"available": True, "idea": None}
    idea = web_proposals.suggest(ideas)["idea"]
    assert idea["name"] == "Build a Grow Tower" and idea["xp"] == 30 and len(idea["skills"]) == 2
    assert web_proposals.mission_idea(ideas)["idea"]["id"] == idea["id"]
    assert "already an idea waiting" in web_proposals.suggest(ideas)["error"]
    ACTION_TYPES["mission_idea.accept"].execute(ideas, {"proposal_id": idea["id"]})
    made = [m for m in ideas.missions.all_missions() if m.name == "Build a Grow Tower"]
    assert len(made) == 1 and made[0].assigned_by == "mia"
    assert web_proposals.mission_idea(ideas)["idea"] is None
    with pytest.raises(ActionError):
        ACTION_TYPES["mission_idea.accept"].execute(ideas, {"proposal_id": idea["id"]})


def test_an_idea_naming_an_unknown_skill_is_never_kept(ideas):
    ideas.llm = _Model(discovery_tests._WELL_FORMED_REPLY.replace("framing:10", "juggling:10"))
    assert "couldn't come up with" in web_proposals.suggest(ideas)["error"]
    assert web_proposals.mission_idea(ideas)["idea"] is None


def test_by_voice_suggest_then_set_aside(ideas):
    said = _suggest(ideas, {})
    assert "Build a Grow Tower" in said and said.endswith("Want it?")
    assert "already an idea waiting" in _suggest(ideas, {})
    assert "Set Build a Grow Tower aside" in _decide_idea(ideas, {"accept": False})
    assert "no mission idea waiting" in _decide_idea(ideas, {"accept": True})
    assert all(m.name != "Build a Grow Tower" for m in ideas.missions.all_missions())


def test_another_persons_idea_cant_be_decided(ideas, monkeypatch):
    idea = web_proposals.suggest(ideas)["idea"]
    monkeypatch.setattr(web_proposals, "_pid", lambda c: "p2")
    with pytest.raises(ActionError):
        ACTION_TYPES["mission_idea.reject"].execute(ideas, {"proposal_id": idea["id"]})


@pytest.fixture
def recordings(tmp_path, monkeypatch):
    """A context with two field recordings waiting (one for p1, one for p2) and the journal."""
    capture_dir = capture_tests.isolated_paths.__wrapped__(tmp_path, monkeypatch)
    context = capture_tests._make_context(capture_dir, transcript="Saw a heron by the creek.")
    capture_tests._write_capture(capture_dir, "a", captured_at="2026-09-14T14:32:00", profile_id="p1")
    capture_tests._write_capture(capture_dir, "b", captured_at="2026-09-13T08:00:00", profile_id="p2")
    context.lite_captures = LiteCaptureManager(context)
    monkeypatch.setattr(web_proposals, "_pid", lambda c: "p1")
    return context


def test_check_finds_recordings_and_each_person_sees_only_their_own(recordings):
    assert web_proposals.check_captures(recordings) == {"found": 2}
    rows = web_proposals.field_captures(recordings)["captures"]
    assert [r["words"] for r in rows] == ["Saw a heron by the creek."] and rows[0]["when"] == "2026-09-14 14:32"


def test_keeping_puts_the_words_in_the_journal_and_leaving_out_does_not(recordings):
    web_proposals.check_captures(recordings)
    assert "1 waiting" in _list(recordings, {})
    assert "in your journal" in _decide_capture(recordings, {"number": 1, "keep": True})
    entries = recordings.journal.all_entries()
    assert len(entries) == 1 and entries[0].body == "Saw a heron by the creek." and "field-capture" in entries[0].tags
    assert _list(recordings, {}) == "No field recordings waiting."


def test_checking_without_the_voice_says_why(recordings):
    recordings.voice = None
    assert "PC's voice" in web_proposals.check_captures(recordings)["error"]
