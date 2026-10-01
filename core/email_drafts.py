"""
core.email_drafts
===================

Email drafts (2026-10-01, accounts stage 3): the Assistant can write an
email for you, and you choose what happens to it: **Send** (only when you
press Send, from your own address, core/mail_send.py), **Copy** it, or
**open it in your mail app** (a mailto: link). MIA never sends anything
by herself; no Assistant tool can send.

Each person's drafts are their own (`data/profiles/<id>/email_drafts.json`,
core/personal_data.py), so the phone can show and send the draft its
person just asked for.
"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import quote

from core.atomic_write import atomic_write_text
from core.logger import get_logger

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_DRAFTS_FILE = _DATA_DIR / "email_drafts.json"
_KEEP = 50

DRAFT, SENT, DISCARDED = "draft", "sent", "discarded"

_ADDRESS = re.compile(r"[^@\s<>,;]+@[^@\s<>,;]+\.[^@\s<>,;]+")


@dataclass
class EmailDraft:
    draft_id: str
    to: list[str]
    subject: str
    body: str
    created_at: str
    status: str = DRAFT
    sent_at: str = ""
    cc: list[str] = field(default_factory=list)

    @staticmethod
    def from_dict(data: dict) -> "EmailDraft":
        return EmailDraft(
            draft_id=data["draft_id"], to=list(data.get("to", [])), subject=data.get("subject", ""),
            body=data.get("body", ""), created_at=data.get("created_at", ""), status=data.get("status", DRAFT),
            sent_at=data.get("sent_at", ""), cc=list(data.get("cc", [])),
        )


def addresses_in(text: str) -> list[str]:
    """Pure logic. Every email address written in some text, in order, once."""
    return list(dict.fromkeys(a.strip(".").lower() for a in _ADDRESS.findall(text or "")))


def mailto_url(draft: EmailDraft) -> str:
    """Pure logic. Opens the person's own mail app with the draft filled in."""
    query = f"subject={quote(draft.subject)}&body={quote(draft.body)}"
    if draft.cc:
        query += f"&cc={quote(','.join(draft.cc))}"
    return f"mailto:{','.join(quote(a, safe='@') for a in draft.to)}?{query}"


def as_text(draft: EmailDraft) -> str:
    """Pure logic. What Copy puts on the clipboard: subject line, then the body."""
    return f"Subject: {draft.subject}\n\n{draft.body}" if draft.subject else draft.body


def as_dict(draft: EmailDraft) -> dict:
    """For the phone: the draft plus its mailto link."""
    return {**asdict(draft), "mailto": mailto_url(draft), "text": as_text(draft)}


class EmailDrafts:
    def __init__(self, context, data_dir: Optional[Path] = None) -> None:
        # Whose data: a person's own folder (core/personal_data.py), or data/ by default.
        self.data_dir = Path(data_dir) if data_dir is not None else _DATA_DIR
        self._drafts_file = self.data_dir / "email_drafts.json" if data_dir is not None else _DRAFTS_FILE
        self.context = context
        self._drafts: list[EmailDraft] = []
        if self._drafts_file.exists():
            try:
                self._drafts = [EmailDraft.from_dict(d) for d in json.loads(self._drafts_file.read_text(encoding="utf-8"))]
            except (OSError, ValueError, KeyError, TypeError):
                log.exception("email_drafts.json unreadable, starting empty.")

    def _save(self) -> None:
        self._drafts = self._drafts[-_KEEP:]
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._drafts_file, json.dumps([asdict(d) for d in self._drafts], indent=2))

    def create(self, to: list[str], subject: str, body: str, cc: Optional[list[str]] = None) -> EmailDraft:
        draft = EmailDraft(draft_id=uuid.uuid4().hex[:10], to=list(to), subject=subject.strip(), body=body.strip(),
                           created_at=datetime.now().isoformat(timespec="seconds"), cc=list(cc or []))
        self._drafts.append(draft)
        self._save()
        return draft

    def get(self, draft_id: str) -> Optional[EmailDraft]:
        return next((d for d in self._drafts if d.draft_id == draft_id), None)

    def update(self, draft_id: str, to: Optional[list[str]] = None, subject: Optional[str] = None,
               body: Optional[str] = None) -> Optional[EmailDraft]:
        draft = self.get(draft_id)
        if draft is None or draft.status != DRAFT:
            return None
        if to is not None:
            draft.to = list(to)
        if subject is not None:
            draft.subject = subject.strip()
        if body is not None:
            draft.body = body.strip()
        self._save()
        return draft

    def mark(self, draft_id: str, status: str) -> None:
        draft = self.get(draft_id)
        if draft is not None:
            draft.status = status
            if status == SENT:
                draft.sent_at = datetime.now().isoformat(timespec="seconds")
            self._save()

    def open_drafts(self) -> list[EmailDraft]:
        return [d for d in reversed(self._drafts) if d.status == DRAFT]

    def latest(self) -> Optional[EmailDraft]:
        return self._drafts[-1] if self._drafts else None

    def count(self) -> int:
        return len(self._drafts)
