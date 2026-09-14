"""
tests.test_lite_capture_manager
==================================

Unit tests for core.lite_capture_manager. format_capture_journal_title()
is tested directly (pure). LiteCaptureManager itself is tested against
a real tmp_path watched folder (genuine file moves/reads, same
reasoning test_finance_manager.py already gives for not mocking the
filesystem) with a _FakeConfig for the config-driven import folder
(same pattern as test_finance_manager.py) and a _FakeVoice stub for
deterministic transcription (no real Vosk model in this dev sandbox).
"""

from __future__ import annotations

import json

import pytest

import core.journal_manager as journal_manager_module
import core.lite_capture_manager as lite_capture_manager_module
from core.app_context import AppContext
from core.event_bus import EventBus
from core.journal_manager import JournalManager
from core.lite_capture_manager import LiteCaptureManager, format_capture_journal_title


class _FakeConfig:
    def __init__(self, overrides: dict) -> None:
        self._overrides = overrides

    def get(self, key: str, default=None):
        return self._overrides.get(key, default)


class _FakeVoice:
    """Stand-in for core.voice_manager.VoiceManager — no real Vosk
    model exists in this dev sandbox, same "gather real facts
    deterministically, stub the one real-hardware-dependent piece"
    convention this whole session's verification scripts already use
    for GenerateWorker/LLM calls."""

    def __init__(self, transcript: str = "Real field note text.", available: bool = True) -> None:
        self._transcript = transcript
        self._available = available

    def transcribe(self, wav_path):
        return self._transcript if self._available else None


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    monkeypatch.setattr(lite_capture_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(lite_capture_manager_module, "_PROPOSALS_FILE", data_dir / "capture_proposals.json")
    monkeypatch.setattr(journal_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(journal_manager_module, "_ENTRIES_FILE", data_dir / "journal_entries.json")
    capture_dir = tmp_path / "lite_captures"
    return capture_dir


def _make_context(capture_dir, transcript="Real field note text.", voice_available=True, with_journal=True) -> AppContext:
    context = AppContext(
        config=_FakeConfig({"lite_capture.import_folder": str(capture_dir)}), events=EventBus(),
    )
    context.voice = _FakeVoice(transcript, available=voice_available)
    if with_journal:
        context.journal = JournalManager(context)
    return context


def _write_capture(capture_dir, capture_id="cap1", captured_at="2026-09-14T14:32:00", audio_filename=None, profile_id=None, write_audio=True):
    capture_dir.mkdir(parents=True, exist_ok=True)
    audio_filename = audio_filename if audio_filename is not None else f"{capture_id}.wav"
    manifest = {"captured_at": captured_at, "audio_filename": audio_filename}
    if profile_id is not None:
        manifest["profile_id"] = profile_id
    (capture_dir / f"{capture_id}.json").write_text(json.dumps(manifest))
    if write_audio and audio_filename:
        (capture_dir / audio_filename).write_bytes(b"fake wav bytes")


# ------------------------------------------------------------------
# format_capture_journal_title (pure)
# ------------------------------------------------------------------

def test_format_capture_journal_title_real_date():
    assert format_capture_journal_title("2026-09-14T14:32:00") == "Field Note — Sep 14, 2026 2:32 PM"


def test_format_capture_journal_title_unparseable_falls_back():
    assert format_capture_journal_title("not-a-date") == "Field Note"


def test_format_capture_journal_title_blank_falls_back():
    assert format_capture_journal_title("") == "Field Note"


# ------------------------------------------------------------------
# scan_for_new_captures
# ------------------------------------------------------------------

def test_scan_creates_a_pending_proposal_from_a_real_capture(isolated_paths):
    capture_dir = isolated_paths
    _write_capture(capture_dir)
    context = _make_context(capture_dir, transcript="I need to check the mower's oil level.")
    manager = LiteCaptureManager(context)

    new_proposals = manager.scan_for_new_captures()

    assert len(new_proposals) == 1
    proposal = new_proposals[0]
    assert proposal.status == "pending"
    assert proposal.transcript == "I need to check the mower's oil level."
    assert proposal.journal_title == "Field Note — Sep 14, 2026 2:32 PM"
    assert proposal.captured_at == "2026-09-14T14:32:00"


def test_scan_moves_manifest_and_audio_to_processed(isolated_paths):
    capture_dir = isolated_paths
    _write_capture(capture_dir)
    context = _make_context(capture_dir)
    manager = LiteCaptureManager(context)

    manager.scan_for_new_captures()

    assert not (capture_dir / "cap1.json").exists()
    assert not (capture_dir / "cap1.wav").exists()
    assert (capture_dir / "processed" / "cap1.json").exists()
    assert (capture_dir / "processed" / "cap1.wav").exists()


def test_scan_does_not_reprocess_already_moved_captures(isolated_paths):
    capture_dir = isolated_paths
    _write_capture(capture_dir)
    context = _make_context(capture_dir)
    manager = LiteCaptureManager(context)

    first_run = manager.scan_for_new_captures()
    second_run = manager.scan_for_new_captures()

    assert len(first_run) == 1
    assert second_run == []


def test_scan_persists_across_a_fresh_load(isolated_paths):
    capture_dir = isolated_paths
    _write_capture(capture_dir)
    context = _make_context(capture_dir)
    manager = LiteCaptureManager(context)
    manager.scan_for_new_captures()

    reloaded = LiteCaptureManager(context)
    assert len(reloaded.all_proposals()) == 1


def test_scan_malformed_manifest_moves_to_failed(isolated_paths):
    capture_dir = isolated_paths
    capture_dir.mkdir(parents=True, exist_ok=True)
    (capture_dir / "bad.json").write_text("{not valid json")
    context = _make_context(capture_dir)
    manager = LiteCaptureManager(context)

    new_proposals = manager.scan_for_new_captures()

    assert new_proposals == []
    assert (capture_dir / "failed" / "bad.json").exists()


def test_scan_manifest_with_no_real_audio_moves_to_failed(isolated_paths):
    capture_dir = isolated_paths
    _write_capture(capture_dir, write_audio=False)
    context = _make_context(capture_dir)
    manager = LiteCaptureManager(context)

    new_proposals = manager.scan_for_new_captures()

    assert new_proposals == []
    assert (capture_dir / "failed" / "cap1.json").exists()


def test_scan_leaves_capture_in_place_when_voice_unavailable_for_retry(isolated_paths):
    capture_dir = isolated_paths
    _write_capture(capture_dir)
    context = _make_context(capture_dir, voice_available=False)
    manager = LiteCaptureManager(context)

    new_proposals = manager.scan_for_new_captures()

    assert new_proposals == []
    assert (capture_dir / "cap1.json").exists()  # left in place, not moved to failed/
    assert manager.all_proposals() == []


def test_scan_with_no_voice_service_returns_empty(isolated_paths):
    capture_dir = isolated_paths
    _write_capture(capture_dir)
    context = _make_context(capture_dir)
    context.voice = None
    manager = LiteCaptureManager(context)
    assert manager.scan_for_new_captures() == []


def test_scan_preserves_profile_id_from_manifest(isolated_paths):
    capture_dir = isolated_paths
    _write_capture(capture_dir, profile_id="p1")
    context = _make_context(capture_dir)
    manager = LiteCaptureManager(context)

    new_proposals = manager.scan_for_new_captures()
    assert new_proposals[0].profile_id == "p1"


def test_scan_defaults_profile_id_to_none(isolated_paths):
    capture_dir = isolated_paths
    _write_capture(capture_dir)
    context = _make_context(capture_dir)
    manager = LiteCaptureManager(context)

    new_proposals = manager.scan_for_new_captures()
    assert new_proposals[0].profile_id is None


# ------------------------------------------------------------------
# accept_proposal / reject_proposal
# ------------------------------------------------------------------

def test_accept_proposal_creates_a_real_journal_entry(isolated_paths):
    capture_dir = isolated_paths
    _write_capture(capture_dir)
    context = _make_context(capture_dir, transcript="Saw a real bear track near the east trail.")
    manager = LiteCaptureManager(context)
    proposal = manager.scan_for_new_captures()[0]

    accepted = manager.accept_proposal(proposal.proposal_id)

    assert accepted.status == "accepted"
    assert accepted.journal_entry_id != ""
    entries = context.journal.all_entries()
    assert len(entries) == 1
    assert entries[0].body == "Saw a real bear track near the east trail."
    assert entries[0].tags == ["field-capture"]


def test_accept_proposal_sets_resolved_at(isolated_paths):
    capture_dir = isolated_paths
    _write_capture(capture_dir)
    context = _make_context(capture_dir)
    manager = LiteCaptureManager(context)
    proposal = manager.scan_for_new_captures()[0]

    accepted = manager.accept_proposal(proposal.proposal_id)
    assert accepted.resolved_at != ""


def test_accept_proposal_persists_across_a_fresh_load(isolated_paths):
    capture_dir = isolated_paths
    _write_capture(capture_dir)
    context = _make_context(capture_dir)
    manager = LiteCaptureManager(context)
    proposal = manager.scan_for_new_captures()[0]
    manager.accept_proposal(proposal.proposal_id)

    reloaded = LiteCaptureManager(context)
    assert reloaded.get_proposal(proposal.proposal_id).status == "accepted"


def test_accept_proposal_twice_does_not_double_create_journal_entries(isolated_paths):
    capture_dir = isolated_paths
    _write_capture(capture_dir)
    context = _make_context(capture_dir)
    manager = LiteCaptureManager(context)
    proposal = manager.scan_for_new_captures()[0]

    manager.accept_proposal(proposal.proposal_id)
    manager.accept_proposal(proposal.proposal_id)  # already accepted — no-op

    assert len(context.journal.all_entries()) == 1


def test_accept_proposal_without_journal_service_leaves_it_pending(isolated_paths):
    capture_dir = isolated_paths
    _write_capture(capture_dir)
    context = _make_context(capture_dir, with_journal=False)
    manager = LiteCaptureManager(context)
    proposal = manager.scan_for_new_captures()[0]

    result = manager.accept_proposal(proposal.proposal_id)

    assert result.status == "pending"


def test_accept_unknown_proposal_returns_none(isolated_paths):
    capture_dir = isolated_paths
    context = _make_context(capture_dir)
    manager = LiteCaptureManager(context)
    assert manager.accept_proposal("does-not-exist") is None


def test_reject_proposal_marks_rejected_with_no_journal_entry(isolated_paths):
    capture_dir = isolated_paths
    _write_capture(capture_dir)
    context = _make_context(capture_dir)
    manager = LiteCaptureManager(context)
    proposal = manager.scan_for_new_captures()[0]

    rejected = manager.reject_proposal(proposal.proposal_id)

    assert rejected.status == "rejected"
    assert rejected.resolved_at != ""
    assert context.journal.all_entries() == []


def test_pending_proposals_excludes_resolved_ones(isolated_paths):
    capture_dir = isolated_paths
    _write_capture(capture_dir, capture_id="cap1")
    _write_capture(capture_dir, capture_id="cap2", captured_at="2026-09-14T15:00:00")
    context = _make_context(capture_dir)
    manager = LiteCaptureManager(context)
    proposals = manager.scan_for_new_captures()
    manager.accept_proposal(proposals[0].proposal_id)

    pending = manager.pending_proposals()
    assert len(pending) == 1
    assert pending[0].proposal_id == proposals[1].proposal_id
