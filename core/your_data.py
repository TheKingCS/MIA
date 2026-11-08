"""
core.your_data
================

Your Data (docs/SECURITY.md step 8, "beyond"): exactly what MIA keeps about a person, and what she read to answer
them, for the web page Settings → Your Data (web/yourdata.html) beside export and delete (core/account_data.py).

- **What she keeps** (`inventory`): every file in the person's own folder (data/profiles/<id>/), and their
  household's shared files (account_data.household_files), each with what it is in words (`LABELS`, else its name),
  how many records it holds, its size, and whether it's sealed on disk (core/at_rest.py, DEC-0126). Read from the
  files themselves, not from a list kept beside them, so nothing is left off.
- **What she read** (`answers`): the person's recent turns from their traces (core/turn_trace.py): what they asked,
  the tools she used and how many of their memories went into the answer. Private and off-the-record turns were
  never traced, so they never show.

Pure reading: nothing here changes a file.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from core.at_rest import is_sealed, line_sealed, open_text
from core.logger import get_logger

log = get_logger(__name__)

# What a file holds, in words. A file not named here shows by its own name.
LABELS = {
    "conversations.json": "Conversations with MIA",
    "user_memories.json": "What MIA remembers about you",
    "memory_corrections.jsonl": "Memories you corrected (kind and age only)",
    "journal_entries.json": "Your notes",
    "private_journal.json": "Private journal (locked with your passphrase)",
    "private_journal_keys.json": "Private journal's lock",
    "life_notes.json": "Promises, decisions and ideas you kept",
    "turn_traces.jsonl": "How she answered each question",
    "communication_log.json": "Messages MIA chose to send, or not",
    "online_reminders.json": "Reminders",
    "intents.json": "Your reasons",
    "why_checkpoints.json": "Check-ins on your reasons",
    "operating_journal.json": "How you mean to operate",
    "gps_tracks.json": "Walks, rides and drives",
    "password_vault.json": "Password vault (locked with its master password)",
    "answer_ratings.json": "Your ratings of her answers",
    "failure_log.json": "Where she stumbled (redacted)",
    "notifications.json": "Notifications",
    "relationships_people.json": "People in your life",
    "relationships_pets.json": "Pets",
    "financial_snapshots.json": "Net worth snapshots",
    "insurance.json": "Insurance policies",
    "bills.json": "Bills",
    "income.json": "Income",
    "budget_expenses.json": "Spending",
    "debts.json": "Debts",
    "calendar_events.json": "Calendar",
    "kitchen.json": "Kitchen",
}
SKIP = (".tmp", ".part", ".lock")


def label(name: str) -> str:
    """What a file holds, in words: LABELS, else its name made readable ("boss_book.json" → "Boss book")."""
    if name in LABELS:
        return LABELS[name]
    stem = name.split(".")[0].replace("_", " ").replace("-", " ").strip()
    return stem[:1].upper() + stem[1:] if stem else name


def count_records(text: str, name: str) -> Optional[int]:
    """Pure logic. How many records a file's text holds: lines for .jsonl; a list's length; for an object, the
    lengths of its lists added up (or its keys when it has none). None when it isn't JSON."""
    if name.endswith(".jsonl"):
        return sum(1 for line in text.splitlines() if line.strip())
    try:
        data = json.loads(text)
    except ValueError:
        return None
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        lists = [v for v in data.values() if isinstance(v, list)]
        return sum(len(v) for v in lists) if lists else len(data)
    return 1


def describe(path: Path) -> dict:
    """One file: its name, what it is, records, size in bytes, and whether it's sealed (a line-sealed history only
    when every line is). A sealed file that won't open still shows (records unknown)."""
    entry = {"file": path.name, "what": label(path.name), "bytes": path.stat().st_size, "records": None,
             "sealed": False}
    if path.suffix.lower() not in (".json", ".jsonl"):
        return entry
    try:
        if line_sealed(path):  # sealed a line at a time: sealed only when every line is (older lines may be plain)
            lines = [x.strip() for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
            entry["sealed"] = bool(lines) and all(is_sealed(x) for x in lines)
        else:
            with open(path, "rb") as f:
                entry["sealed"] = is_sealed(f.read(16))
        entry["records"] = count_records(open_text(path), path.name)
    except (OSError, ValueError):
        log.info("Couldn't count %s for Your Data", path.name)
    return entry


def files_in(folder: Optional[Path]) -> list[Path]:
    """The data files directly in a folder (no temporary ones, no copies set aside)."""
    if folder is None or not Path(folder).is_dir():
        return []
    return sorted(p for p in Path(folder).iterdir() if p.is_file() and not p.name.startswith(".")
                  and not p.name.endswith(SKIP) and ".unreadable-" not in p.name)


def inventory(context, profile_id: str) -> dict:
    """{"mine": [file, ...], "home": [file, ...]}: the person's own files and their household's shared ones."""
    from core.account_data import household_files

    personal = getattr(context, "personal_data", None)
    mine = files_in(personal.folder(profile_id)) if personal is not None else []
    home = sorted(household_files(context, profile_id), key=lambda p: p.name)
    return {"mine": [describe(p) for p in mine],
            "home": [describe(p) for p in home if p.is_file() and not p.name.endswith(SKIP)]}


def answers(context, count: int = 20) -> list[dict]:
    """The person's latest traced answers, newest first: when, what they asked, the route, the tools she used and how
    many of their memories went in."""
    traces = getattr(context, "traces", None)
    if traces is None:
        return []
    return [{"at": t.get("at", ""), "asked": t.get("asked", ""), "route": t.get("route", ""),
             "tools": [str(n).replace("_", " ") for n in t.get("tools_called") or []],
             "memories": int(t.get("memories") or 0)}
            for t in reversed(traces.recent(count))]


def page(context, profile_id: str) -> dict:
    """The Your Data page: the files, the latest answers, and whether sealing is on."""
    from core import at_rest

    return {**inventory(context, profile_id), "answers": answers(context), "sealing": at_rest.status()["sealing"]}
