"""
core.lite_capture_manager
============================

The receiving/processing side of "MIA Lite" (`docs/VISION.md`'s
Core/Home split section, "MIA Lite — a fourth tier, lighter than
Core") — scoped directly with the user across 4 real questions before
any code: hardware (a mode on the existing Receiver, no new device),
capture scope v1 (voice notes only), sync mechanism (opportunistic
wireless, eventually), and processing model (MIA proposes, the user
confirms — same discipline `core/discovery_manager.py` already
established for Mission proposals).

**What this manager is NOT**: the device-side capture/recording and
the actual wireless sync transport. Neither can be built or tested
here — there's no real Receiver hardware in this dev sandbox, the same
real constraint `docs/VISION.md`'s Core voice-loop entry point is
already honest about being unbuilt for. This manager picks up from
wherever a real capture eventually lands — a watched folder,
`lite_captures/`, same "manual for now, automated later once real
hardware exists" precedent `core/finance_manager.py` and
`core/homestead_manager.py` already established for their own
external sources.

**The manifest contract this manager defines** (no real device
software exists yet to have defined it already — same situation
`docs/MIA_HOME_SYNC_PLAN.md` was in before the Homestead side
existed): a capture is a `<capture_id>.json` manifest
(`captured_at`, `audio_filename`, optional `profile_id`) paired with a
`.wav` file of the same id. Transcription happens HERE, not on the
device — the whole point of "Lite" is the field device does no local
inference at all; `core.voice_manager.VoiceManager`'s existing offline
Vosk backend already does this job, no new speech tech needed.

**The proposal**: a transcribed capture becomes a real, persisted
`CaptureProposal` (pending review) — never auto-applied. Deliberately
NOT a destination-classification decision for an LLM to get wrong
(journal vs. mission vs. memory) — every accepted capture always
becomes a Journal entry (the transcript, a deterministic timestamp
title, tagged "field-capture"), the one destination that's always a
correct fit for "something said out loud in the field." Real personal
facts are additionally extracted from the same transcript via the
exact same pipeline a real chat message already goes through
(`core.assistant_chat.build_memory_extraction_prompt()`/
`parse_extracted_memories()`) — triggered on accept, same "MIA notices
things silently in the background" precedent that pipeline already has
everywhere else it's used, not a second thing to separately confirm
(see `gui/home_dashboard.py`'s own trigger for this, same shape as its
interview-notes extraction). "Mission update" as a destination is
deliberately NOT attempted — mapping free voice text onto a specific
Mission/Objective reliably is a real, separate, harder classification
problem.
"""

from __future__ import annotations

import json
import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.app_context import AppContext
from core.logger import get_logger
from core.atomic_write import atomic_write_text

log = get_logger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DATA_DIR = _PROJECT_ROOT / "data"
_PROPOSALS_FILE = _DATA_DIR / "capture_proposals.json"
_DEFAULT_CAPTURE_DIR = _PROJECT_ROOT / "lite_captures"
_PROCESSED_SUBDIR = "processed"
_FAILED_SUBDIR = "failed"

CAPTURE_PROPOSAL_STATUSES = ("pending", "accepted", "rejected")


@dataclass
class CaptureProposal:
    proposal_id: str
    profile_id: Optional[str] = None
    status: str = "pending"
    captured_at: str = ""  # from the device manifest — when the recording actually happened
    created_at: str = ""  # when this proposal was generated (transcription time)
    resolved_at: str = ""  # ISO datetime, set on accept/reject
    source_filename: str = ""  # the manifest's own filename, for traceability
    transcript: str = ""
    journal_title: str = ""
    journal_entry_id: str = ""  # set once accepted

    def to_dict(self) -> dict:
        return {
            "proposal_id": self.proposal_id,
            "profile_id": self.profile_id,
            "status": self.status,
            "captured_at": self.captured_at,
            "created_at": self.created_at,
            "resolved_at": self.resolved_at,
            "source_filename": self.source_filename,
            "transcript": self.transcript,
            "journal_title": self.journal_title,
            "journal_entry_id": self.journal_entry_id,
        }

    @staticmethod
    def from_dict(data: dict) -> "CaptureProposal":
        return CaptureProposal(
            proposal_id=data.get("proposal_id", uuid.uuid4().hex[:10]),
            profile_id=data.get("profile_id"),
            status=data.get("status", "pending"),
            captured_at=data.get("captured_at", ""),
            created_at=data.get("created_at", ""),
            resolved_at=data.get("resolved_at", ""),
            source_filename=data.get("source_filename", ""),
            transcript=data.get("transcript", ""),
            journal_title=data.get("journal_title", ""),
            journal_entry_id=data.get("journal_entry_id", ""),
        )


def format_capture_journal_title(captured_at: str) -> str:
    """Pure formatting logic — testable without Qt. Fully deterministic,
    no LLM involved in naming a Journal entry (see this module's own
    docstring for why — always-correct beats "maybe clever")."""
    try:
        when = datetime.fromisoformat(captured_at)
        return f"Field Note — {when.strftime('%b %-d, %Y %-I:%M %p')}"
    except ValueError:
        return "Field Note"


class LiteCaptureManager:
    def __init__(self, context: AppContext) -> None:
        self.context = context
        self._proposals: list[CaptureProposal] = []
        self._load()

        try:
            self.capture_folder_path.mkdir(parents=True, exist_ok=True)
            (self.capture_folder_path / _PROCESSED_SUBDIR).mkdir(exist_ok=True)
            (self.capture_folder_path / _FAILED_SUBDIR).mkdir(exist_ok=True)
        except OSError:
            # Same "don't crash over a missing/unmounted folder" stance
            # as FinanceManager/ReferenceLibraryManager —
            # scan_for_new_captures() below already no-ops gracefully
            # if the folder isn't there.
            log.warning("Could not create/access lite capture folder: %s", self.capture_folder_path)

    @property
    def capture_folder_path(self) -> Path:
        configured = self.context.config.get("lite_capture.import_folder", "")
        if configured:
            return Path(configured).expanduser()
        return _DEFAULT_CAPTURE_DIR

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not _PROPOSALS_FILE.exists():
            return
        try:
            raw = json.loads(_PROPOSALS_FILE.read_text(encoding="utf-8"))
            self._proposals = [CaptureProposal.from_dict(d) for d in raw.get("proposals", [])]
        except (json.JSONDecodeError, OSError):
            log.exception("Failed to load capture_proposals.json — starting with no proposals.")
            self._proposals = []

    def _save(self) -> None:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        atomic_write_text(_PROPOSALS_FILE,
            json.dumps({"proposals": [p.to_dict() for p in self._proposals]}, indent=2),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------

    def scan_for_new_captures(self) -> list[CaptureProposal]:
        """Called by a periodic timer (core/application.py) — scans the
        watched folder's top level (not the processed/failed
        subfolders) for `*.json` manifests, transcribes the paired
        `.wav` via `core.voice_manager.VoiceManager`, and creates a
        real pending CaptureProposal for each. A manifest whose audio
        can't be transcribed right now (voice backend unavailable) is
        left in place, untouched, so a LATER scan can retry it once
        voice becomes available — only moved to failed/ for a
        genuinely malformed manifest, never for a transient reason.
        Returns the proposals newly created *this call*."""
        if self.context.voice is None or not self.capture_folder_path.is_dir():
            return []

        new_proposals: list[CaptureProposal] = []
        for manifest_path in sorted(self.capture_folder_path.glob("*.json")):
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                log.warning("Could not read capture manifest %s — moving to failed/.", manifest_path.name)
                self._move_file(manifest_path, _FAILED_SUBDIR)
                continue

            audio_filename = manifest.get("audio_filename", "")
            audio_path = self.capture_folder_path / audio_filename if audio_filename else None
            if not audio_filename or audio_path is None or not audio_path.exists():
                log.warning("Capture manifest %s names no real audio file — moving to failed/.", manifest_path.name)
                self._move_file(manifest_path, _FAILED_SUBDIR)
                continue

            transcript = self.context.voice.transcribe(audio_path)
            if not transcript:
                log.info(
                    "Capture %s not transcribed yet (voice backend unavailable) — retrying next scan.",
                    manifest_path.name,
                )
                continue

            now = datetime.now().isoformat(timespec="seconds")
            captured_at = manifest.get("captured_at") or now
            proposal = CaptureProposal(
                proposal_id=uuid.uuid4().hex[:10],
                profile_id=manifest.get("profile_id"),
                captured_at=captured_at,
                created_at=now,
                source_filename=manifest_path.name,
                transcript=transcript,
                journal_title=format_capture_journal_title(captured_at),
            )
            self._proposals.append(proposal)
            new_proposals.append(proposal)
            self._move_file(manifest_path, _PROCESSED_SUBDIR)
            self._move_file(audio_path, _PROCESSED_SUBDIR)
            log.info("New field capture transcribed: '%s'", proposal.journal_title)

        if new_proposals:
            self._save()
        return new_proposals

    def _move_file(self, file_path: Path, subdir: str) -> None:
        destination = self.capture_folder_path / subdir / file_path.name
        try:
            shutil.move(str(file_path), str(destination))
        except OSError as exc:
            log.warning("Could not move %s to %s: %s", file_path, destination, exc)

    # ------------------------------------------------------------------
    # Review
    # ------------------------------------------------------------------

    def all_proposals(self) -> list[CaptureProposal]:
        return list(self._proposals)

    def pending_proposals(self) -> list[CaptureProposal]:
        return [p for p in self._proposals if p.status == "pending"]

    def get_proposal(self, proposal_id: str) -> Optional[CaptureProposal]:
        return next((p for p in self._proposals if p.proposal_id == proposal_id), None)

    def accept_proposal(self, proposal_id: str) -> Optional[CaptureProposal]:
        """Turns a pending proposal into a real Journal entry — the one
        destination this manager ever commits to on its own (see
        module docstring for why). Refuses (leaves the proposal
        pending) if Journal isn't wired — never silently discards a
        real capture just because the destination it needs isn't
        available. Real memory extraction from the transcript is a
        separate, GUI-side step (needs an async LLM call this core
        manager has no business owning) — see
        gui/home_dashboard.py's own trigger for it."""
        proposal = self.get_proposal(proposal_id)
        if proposal is None or proposal.status != "pending":
            return proposal
        if self.context.journal is None:
            log.warning("Cannot accept capture proposal '%s' — Journal service unavailable.", proposal_id)
            return proposal

        entry = self.context.journal.add_entry(title=proposal.journal_title, body=proposal.transcript, tags=["field-capture"])
        proposal.status = "accepted"
        proposal.resolved_at = datetime.now().isoformat(timespec="seconds")
        proposal.journal_entry_id = entry.entry_id
        self._save()
        log.info("Capture proposal accepted: '%s'", proposal.journal_title)
        return proposal

    def reject_proposal(self, proposal_id: str) -> Optional[CaptureProposal]:
        proposal = self.get_proposal(proposal_id)
        if proposal is None or proposal.status != "pending":
            return proposal
        proposal.status = "rejected"
        proposal.resolved_at = datetime.now().isoformat(timespec="seconds")
        self._save()
        log.info("Capture proposal rejected: '%s'", proposal.journal_title)
        return proposal
