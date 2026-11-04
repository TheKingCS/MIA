"""
core.creations
================

What MIA has made for a person, and every version of it (DEC-0091; ACAF,
`docs/ACAF_REVIEW.md` section 5). A personal store (PERSONAL_STORES): a
person's creations are theirs, even when the records they show are the
household's.

Each creation keeps its id, its kind ("screen"), the blueprint and version
it came from, every version's spec with its check results, who made it and
why, and where it stands:
- **draft**: private, previewed on real data, read-only. Making one is
  automatic.
- **published**: in the person's sidebar. Publishing is an action
  (`creation.publish`, core/creation_actions.py), so it's approved and
  undoable; the record set it shows is made then, not before.
- **retired**: out of the sidebar, kept.

A changed spec is a new version beside the old ones, published only when
approved; `creation.rollback` goes back to the version before. Nothing is
overwritten silently, and nothing outside the creation is ever touched.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.atomic_write import atomic_write_text
from core.logger import get_logger

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_FILE = "creations.json"
DRAFT, PUBLISHED, RETIRED = "draft", "published", "retired"


class CreationError(ValueError):
    """A creation that can't do what was asked; the message says why."""


class Creations:
    def __init__(self, context=None, data_dir: Optional[Path] = None) -> None:
        self.context = context
        self.data_dir = Path(data_dir) if data_dir is not None else _DATA_DIR
        self._file = self.data_dir / _FILE
        self._load()

    def _load(self) -> None:
        try:
            self.items: list[dict] = json.loads(self._file.read_text(encoding="utf-8")).get("creations", [])
        except FileNotFoundError:
            self.items = []
        except (OSError, ValueError):
            log.exception("Couldn't read the creations; starting empty")
            self.items = []

    def _save(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._file, json.dumps({"creations": self.items}, indent=2, ensure_ascii=False) + "\n")

    def get(self, creation_id: str) -> dict:
        found = next((c for c in self.items if c["id"] == creation_id), None)
        if found is None:
            raise CreationError(f"No creation {creation_id}.")
        return found

    def published(self) -> list[dict]:
        return [c for c in self.items if c["status"] == PUBLISHED]

    def draft(self, spec: dict, checks: list[str], made_by: str = "mia", why: str = "", blueprint: str = "",
              creation_id: str = "") -> dict:
        """A new creation, or a new version of one: never published by itself."""
        now = datetime.now().isoformat(timespec="seconds")
        if creation_id:
            found = self.get(creation_id)
            before = found["versions"][-1]["spec"]  # what it shows stays what it showed: only the layout changes
            if before.get("kind", "screen") == "screen":
                spec = {**{k: v for k, v in spec.items() if k not in ("record_set", "source")}, "owner": found["owner"],
                        **({"source": before["source"]} if before.get("source") else {"record_set": before.get("record_set")})}
            else:
                spec = {**spec, "owner": found["owner"]}
        else:
            taken = {c["id"] for c in self.items}
            found = {"id": next(f"C-{n:04d}" for n in range(1, 10_000) if f"C-{n:04d}" not in taken),
                     "kind": spec.get("kind", "screen"), "title": spec.get("title", ""), "owner": spec.get("owner", "personal"),
                     "status": DRAFT, "version": 0, "published_versions": [], "set_id": "", "versions": [],
                     "created": now}
            self.items.append(found)
        found["versions"].append({"version": len(found["versions"]) + 1, "spec": spec, "checks": checks,
                                  "made_by": made_by, "why": why[:500], "blueprint": blueprint, "at": now})
        self._save()
        return found

    def latest(self, creation_id: str) -> dict:
        return self.get(creation_id)["versions"][-1]

    def shown(self, creation_id: str) -> dict:
        """The version in the sidebar, or the latest draft."""
        found = self.get(creation_id)
        if found["version"]:
            return found["versions"][found["version"] - 1]
        return found["versions"][-1]

    def mark_published(self, creation_id: str, version: int, set_id: str) -> dict:
        found = self.get(creation_id)
        found.update(status=PUBLISHED, version=version, set_id=set_id or found["set_id"],
                     title=found["versions"][version - 1]["spec"].get("title", found["title"]))
        found["published_versions"].append(version)
        self._save()
        return found

    def roll_back(self, creation_id: str) -> dict:
        found = self.get(creation_id)
        history = found["published_versions"]
        if len(history) < 2:
            raise CreationError("There's no earlier published version to go back to.")
        history.pop()
        found["version"] = history[-1]
        found["title"] = found["versions"][found["version"] - 1]["spec"].get("title", found["title"])
        self._save()
        return found

    def keep_rows(self, creation_id: str, rows: list[dict]) -> None:
        """An imported file's rows, kept with its draft until it's published (core/record_import.py)."""
        self.get(creation_id)["pending_rows"] = list(rows)
        self._save()

    def take_rows(self, creation_id: str) -> list[dict]:
        found = self.get(creation_id)
        rows = found.pop("pending_rows", None) or []
        self._save()
        return rows

    def log_run(self, creation_id: str, entry: dict, keep: int = 50) -> None:
        """A workflow's run (core/workflows.py): what it did, kept with it, the latest `keep`."""
        found = self.get(creation_id)
        found["runs"] = (found.get("runs") or [])[-(keep - 1):] + [entry]
        self._save()

    def retire(self, creation_id: str) -> dict:
        found = self.get(creation_id)
        found["status"] = RETIRED
        self._save()
        return found
