"""
core.turn_trace
=================

One line per Assistant turn: how MIA got to what she said (DEC-0067, choice
4: native traces before Langfuse; phase 2 of
docs/PERSONALITY_AND_ECOSYSTEM_AUDIT.md). The route that answered (a fixed
reply, a plain-word command, a question plan, the model), what was asked and
said, the tools offered and called, the memories used, which model and which
computer answered, and how long it took.

The Fix-It Log keeps where she stumbled; this keeps every turn, so "why did
she answer like that?" has an answer, and the conversation corpus and Zac's
ratings can be read against what really happened.

Personal: each person's own, in their folder, never sent anywhere. Private
and off-the-record turns are never traced, as the Fix-It Log never logs them.
Text is redacted the Fix-It Log's way (passwords, emails, card numbers).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from core.atomic_write import atomic_write_text
from core.logger import get_logger

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_FILE = "turn_traces.jsonl"
MAX_KEPT = 2000  # about a month of everyday use
MAX_TEXT = 1200


class TurnTraces:
    def __init__(self, context=None, data_dir: Optional[Path] = None) -> None:
        self.context = context
        self.data_dir = Path(data_dir) if data_dir is not None else _DATA_DIR
        self._file = self.data_dir / _FILE
        self.traces: list[dict] = []
        self._load()

    def _load(self) -> None:
        try:
            lines = self._file.read_text(encoding="utf-8").splitlines()
        except FileNotFoundError:
            lines = []
        except OSError:
            log.exception("Couldn't read the turn traces; starting a new list")
            lines = []
        self.traces = []
        for line in lines:
            try:
                self.traces.append(json.loads(line))
            except ValueError:
                continue

    def add(self, trace: dict) -> None:
        self.traces = (self.traces + [trace])[-MAX_KEPT:]
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._file, "\n".join(json.dumps(t, ensure_ascii=False) for t in self.traces) + "\n")

    def recent(self, count: int = 50) -> list[dict]:
        return self.traces[-count:]


def record(context, conversation, prompt: str, turn, seconds: float, surface: str = "") -> None:
    """Trace one finished turn. Never raises, and never traces a private one."""
    try:
        traces = getattr(context, "traces", None)
        if traces is None:
            return
        privacy = conversation.current_privacy() if hasattr(conversation, "current_privacy") else ""
        if privacy:
            return
        from core.failure_log import redact

        llm = getattr(context, "llm", None)
        backend = getattr(llm, "backend", None) if llm is not None else None
        reply = " ".join(getattr(turn, "replies", []) or [])
        traces.add({
            "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "conversation": getattr(conversation, "conversation_id", ""),
            "mode": getattr(conversation, "mode", None) or "",
            "surface": surface,
            "route": getattr(turn, "route", "") or "",
            "asked": redact(prompt or "", MAX_TEXT),
            "said": redact(reply, MAX_TEXT),
            "words": len(reply.split()),
            "tools_offered": len(getattr(turn, "tools_offered", []) or []),
            "tools_called": list(getattr(turn, "tools_called", []) or []),
            "memories": len(getattr(turn, "used", []) or []),
            "model": getattr(backend, "_model", "") or "",
            "where": getattr(llm, "level", "") if llm is not None else "",
            "model_answered": bool(getattr(turn, "llm_available", True)),
            "seconds": round(seconds, 2),
        })
    except Exception:  # a trace is never in the way of an answer
        log.exception("Couldn't trace this turn")
