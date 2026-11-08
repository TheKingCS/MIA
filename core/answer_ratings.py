"""
core.answer_ratings
=====================

Zac's 👍 and 👎 on MIA's answers (DEC-0067's tuning, step 3): what she was
asked, what she said, on which device, and how it landed. Personal: each
person's own, in their folder (core/personal_data.py).

Two uses. Now: the conversation corpus (tools/conversation_check.py) can be
checked against real answers he liked or didn't. Later: the examples a
fine-tune learns her voice from (step 4), which needs a few hundred of them.
A 👎 still goes to the Fix-It Log too (core/failure_log.py), so it gets
fixed; this only adds the record of what was right.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from core.at_rest import open_text
from core.atomic_write import atomic_write_text
from core.logger import get_logger

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_FILE = "answer_ratings.json"
UP, DOWN = "up", "down"
SURFACES = ("glasses", "phone", "pc")
MAX_TEXT = 4000  # one answer, kept whole enough to learn from
MAX_KEPT = 5000


class AnswerRatings:
    """A person's 👍 and 👎 on her answers (answer_ratings.json in their own folder, the latest 5,000, written
    through atomic_write_text): what was asked, what she said, where, any note, and which model answered.
    """
    def __init__(self, context=None, data_dir: Optional[Path] = None) -> None:
        """Loads the ratings from the person's folder (or data/)."""
        self.context = context
        self.data_dir = Path(data_dir) if data_dir is not None else _DATA_DIR
        self._file = self.data_dir / _FILE
        self.ratings: list[dict] = []
        self._load()

    def _load(self) -> None:
        """Reads the ratings; a missing file gives none, a damaged one is logged and starts a new list. Sealed at rest (DEC-0126): a sealed file is opened; one that won't open is copied aside and starts empty."""
        try:
            self.ratings = json.loads(open_text(self._file)).get("ratings", [])
        except FileNotFoundError:
            self.ratings = []
        except (OSError, ValueError):
            log.exception("Couldn't read the answer ratings; starting a new list")
            self.ratings = []

    def _save(self) -> None:
        """Writes the latest ratings atomically."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._file, json.dumps({"ratings": self.ratings[-MAX_KEPT:]}, indent=1, ensure_ascii=False))

    def rate(self, rating: str, asked: str, answer: str, surface: str = "", note: str = "", model: str = "") -> dict:
        """Keeps one rating (up or down, else ValueError) with what was asked and answered (each cut to 4,000
        characters), the surface it came from, a note and the model.
        """
        if rating not in (UP, DOWN):
            raise ValueError("A rating is up or down.")
        entry = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "rating": rating,
                 "asked": (asked or "")[:MAX_TEXT], "answer": (answer or "")[:MAX_TEXT],
                 "surface": surface if surface in SURFACES else "", "note": (note or "")[:MAX_TEXT], "model": model}
        self.ratings.append(entry)
        self._save()
        return entry

    def counts(self) -> dict:
        """How many answers were rated up and down."""
        return {UP: sum(1 for r in self.ratings if r["rating"] == UP),
                DOWN: sum(1 for r in self.ratings if r["rating"] == DOWN)}
