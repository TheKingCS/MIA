"""
core.saga
===========

The Chronicle Archive for *MIA: The Chronicles* (DEC-0084; Zac and ChatGPT,
H-0081: "a dedicated structure that continuously gathers and organizes
information that could become part of future comic issues";
`docs/COUNCIL_AND_CHRONICLES_REVIEW.md` section 7). Not `core/chronicle.py`:
that's each person's own week (DEC-0028). This is the story of MIA's
development.

- **Development events** are the project's history and live in the repo,
  one file each: `work/saga/events/E-0001.json`. Every event keeps its
  sources (`task:T-0030`, `dec:DEC-0077`, `thread:<id>`, `commit:<sha>`),
  whether it's real or fictional, built or imagined, how significant, its
  privacy (series: may appear in the comic; private: kept, never shown) and
  whether Zac approved it.
- **Candidates** are found by rules in code, never a model, and never every
  ordinary interaction (`candidates()`): a finished task (a milestone; one
  tied to decisions counts more), an approved decision (a turning point),
  a merge the lab undid (a setback), the first merge, the first review by
  each provider, a council thread where two or more members spoke (the
  first one counts most). Each waits for Zac: `accept()`, or `drop()` so it
  never comes back. Nothing joins the series by itself.
- **Creator and MIA moments are personal** (DEC-0002): `SagaMoments`, a
  personal store in the person's own folder, never the repo. "MIA, remember
  this for the Chronicles" keeps one; "keep that private" or "not for the
  comic" marks the last one. A moment reaches an issue only when Zac marks
  it for the series, and then only its summary.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from core.at_rest import open_text
from core.atomic_write import atomic_write_text
from core.logger import get_logger

log = get_logger(__name__)

ROOT = Path(__file__).resolve().parent.parent
SAGA = ROOT / "work" / "saga"
CATEGORIES = ("milestone", "moment", "council", "setback", "idea", "character")
PRIVACY = ("series", "private", "never")

REMEMBER = re.compile(r"^\s*(?:(?:hey\s+)?mia[,:]?\s+)?(?:please\s+)?(?:remember|save|keep) (?:this|that)(?: one)? "
                      r"for the chronicles?\b[\s:,.!-]*(.*)$|^\s*(?:that's|that is|this is) chronicle[- ]worthy\b[\s:,.!-]*(.*)$",
                      re.I)
PRIVATE = re.compile(r"^\s*(?:(?:hey\s+)?mia[,:]?\s+)?(?:keep (?:that|this|it) private|(?:that's |that is )?not for "
                     r"the (?:comic|chronicles?))\b", re.I)


def _now() -> str:
    """Now, in UTC, as an ISO timestamp."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# --------------------------------------------------------------- development events (the repo)

def _events_dir(root: Path) -> Path:
    """Where development events are kept (work/saga/events/)."""
    return Path(root) / "events"


def events(root: Path = SAGA) -> list[dict]:
    """Every development event (one E-NNNN.json each), in order; an unreadable one is logged and skipped."""
    out = []
    folder = _events_dir(root)
    for path in sorted(folder.glob("E-*.json")) if folder.exists() else []:
        try:
            out.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            log.warning("Couldn't read %s", path)
    return out


def _decided(root: Path) -> dict:
    """The candidates Zac has accepted or dropped (decided.json), so none comes back; {} when there's none."""
    try:
        return json.loads((Path(root) / "decided.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _write_decided(root: Path, data: dict) -> None:
    """Saves what's been decided, atomically."""
    Path(root).mkdir(parents=True, exist_ok=True)
    atomic_write_text(Path(root) / "decided.json", json.dumps(data, indent=2, sort_keys=True) + "\n")


def _save(event: dict, root: Path) -> None:
    """Saves one event to its own file, atomically."""
    folder = _events_dir(root)
    folder.mkdir(parents=True, exist_ok=True)
    atomic_write_text(folder / f"{event['id']}.json", json.dumps(event, indent=2, ensure_ascii=False) + "\n")


def _next_id(root: Path) -> str:
    """The next free event id (E-0001, E-0002...)."""
    taken = [int(e["id"][2:]) for e in events(root) if str(e.get("id", "")).startswith("E-")]
    return f"E-{(max(taken) + 1) if taken else 1:04d}"


def _decisions(path: Path) -> list[dict]:
    """Approved decisions, with the date they were approved."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    out = []
    for block in re.split(r"^### ", text, flags=re.M)[1:]:
        head = block.splitlines()[0]
        m = re.match(r"(DEC-\d{4}):\s*(.+)", head)
        if not m or not re.search(r"^- Status: (APPROVED|IMPLEMENTED)", block, re.M):
            continue
        when = re.search(r"Approved by: \w+, (\d{4}-\d{2}-\d{2})", block)
        out.append({"id": m.group(1), "title": m.group(2).strip(), "at": when.group(1) if when else ""})
    return out


def _candidate(ref: str, at: str, title: str, summary: str, category: str, significance: int, sources: list[str],
               involved: list[str], subsystem: list[str] = ()) -> dict:
    """A candidate event found by a rule: what it points at, when, its title and summary, its category, how significant,
    its sources and who was involved; always real, built and verified (it came from the records).
    """
    return {"ref": ref, "at": at, "title": title, "summary": summary, "category": category,
            "significance": significance, "sources": sources, "involved": sorted(set(involved) - {""}),
            "subsystem": list(subsystem), "timeline": "real", "status": "built", "evidence": "verified"}


def find(activity: list[dict], tasks: dict, decisions: list[dict], threads: list[list[dict]]) -> list[dict]:
    """Pure logic. Every candidate the records hold, by rule, newest last."""
    found: list[dict] = []
    reviewed_by: set = set()
    merged_once = False
    for e in activity:
        task = tasks.get(e.get("task", ""))
        title = getattr(task, "title", "") or e.get("task", "")
        who = str(e.get("who", ""))
        if e.get("action") == "done" and task is not None:
            commit = re.search(r"commit ([0-9a-f]{7,})", str(e.get("detail", "")))
            found.append(_candidate(f"task:{task.id}", e["at"], title, f"{task.id} finished: {title}.", "milestone",
                                    3 if task.decisions else 2,
                                    [f"task:{task.id}"] + [f"dec:{d}" for d in task.decisions]
                                    + ([f"commit:{commit.group(1)}"] if commit else []), [who, "zac"]))
        elif e.get("action") == "approve" and str(e.get("detail", "")).startswith("reverted"):
            found.append(_candidate(f"revert:{e.get('task')}@{e['at']}", e["at"], f"{title}: undone",
                                    f"Approved into the running MIA, the merge broke a test and the lab undid it by "
                                    f"itself: {str(e.get('detail', ''))[10:200]}", "setback", 3,
                                    [f"task:{e.get('task')}"], ["zac", "mia"]))
        elif e.get("action") == "approve" and str(e.get("detail", "")).startswith("merged") and not merged_once:
            merged_once = True
            found.append(_candidate(f"first-merge:{e.get('task')}", e["at"], "The first change through the lab",
                                    f"{title}: written by an agent, reviewed by another, approved by Zac and merged.",
                                    "milestone", 4, [f"task:{e.get('task')}"], ["zac", "mia"], ["lab"]))
        elif e.get("action") == "review":
            provider = who.rsplit("(", 1)[-1].rstrip(")") if who.endswith(")") else who
            if provider and provider not in reviewed_by:
                reviewed_by.add(provider)
                found.append(_candidate(f"first-review:{provider}", e["at"], f"{provider} reviews for the first time",
                                        f"{who} reviewed {e.get('task')}: {str(e.get('detail', '')).split(':', 1)[0]}.",
                                        "council", 3, [f"task:{e.get('task')}"], [provider]))
    for d in decisions:
        found.append(_candidate(f"dec:{d['id']}", d["at"], d["title"], f"Decided ({d['id']}): {d['title']}.",
                                "milestone", 3, [f"dec:{d['id']}"], ["zac"]))
    first_council = True
    for thread in threads:
        spoke = {m["who"] for m in thread if m.get("kind") == "answer" and m.get("who") not in ("mia", "zac")}
        if len(spoke) < 2:
            continue
        root = thread[0]
        found.append(_candidate(f"thread:{root['id']}", root.get("at", ""),
                                "The first council debate" if first_council else "A council discussion",
                                f"Zac asked: {root.get('text', '')[:160]}", "council", 4 if first_council else 2,
                                [f"thread:{root['id']}"], ["zac", "mia", *spoke], ["council"]))
        first_council = False
    return sorted(found, key=lambda c: c["at"])


def candidates(root: Path = SAGA) -> list[dict]:
    """What's waiting for Zac: every candidate the records hold, minus those he's accepted or dropped."""
    from core import work_activity, work_tasks

    decided = _decided(root)
    try:
        tasks = work_tasks.load()
    except Exception:
        tasks = {}
    threads: dict[str, list[dict]] = {}
    try:
        from core import council

        for m in council.recent(600):
            threads.setdefault(m.get("thread") or m["id"], []).append(m)
    except OSError:
        pass
    found = find(work_activity.events(), tasks, _decisions(ROOT / "docs" / "DECISIONS.md"), list(threads.values()))
    return [c for c in found if c["ref"] not in decided]


def accept(candidate: dict, privacy: str = "series", significance: Optional[int] = None,
           title: str = "", root: Path = SAGA) -> dict:
    """Zac adds a candidate to the archive: an event with its sources, approved."""
    if privacy not in PRIVACY[:2]:
        raise ValueError("A development event is for the series, or private.")
    event = {"id": _next_id(root), **{k: v for k, v in candidate.items() if k != "ref"},
             "title": title.strip() or candidate["title"], "privacy": privacy,
             "significance": significance or candidate.get("significance", 2), "approved": "yes",
             "issue": None, "related": [], "source_ref": candidate["ref"], "added": _now()}
    _save(event, root)
    decided = _decided(root)
    decided[candidate["ref"]] = event["id"]
    _write_decided(root, decided)
    return event


def drop(ref: str, root: Path = SAGA) -> None:
    """Zac says no: the candidate never comes back."""
    decided = _decided(root)
    decided[ref] = "dropped"
    _write_decided(root, decided)


def mark(event_id: str, privacy: str, root: Path = SAGA) -> dict:
    """Marks a development event for the series or private (ValueError for an unknown event or privacy)."""
    found = next((e for e in events(root) if e["id"] == event_id), None)
    if found is None:
        raise ValueError(f"No event {event_id}.")
    if privacy not in PRIVACY[:2]:
        raise ValueError("A development event is for the series, or private.")
    found["privacy"] = privacy
    _save(found, root)
    return found


def note_idea(text: str, who: str = "zac", root: Path = SAGA) -> dict:
    """A story idea or a development moment Zac names himself ("remember this for the Chronicles" in the
    dev window): an event straight away, since he's the one adding it."""
    text = " ".join((text or "").split())
    if not text:
        raise ValueError("Say what to remember.")
    event = {"id": _next_id(root), "at": _now(), "title": text[:80], "summary": text[:600], "category": "idea"
             if re.search(r"\b(idea|imagine|someday|what if|could)\b", text, re.I) else "milestone",
             "timeline": "real", "status": "planned", "evidence": "none", "significance": 3, "sources": [],
             "involved": [who], "subsystem": [], "privacy": "series", "approved": "yes", "issue": None,
             "related": [], "source_ref": "", "added": _now()}
    _save(event, root)
    return event


# --------------------------------------------------------------- personal moments (the person's folder)

_FILE = "saga_moments.json"


class SagaMoments:
    """A person's Creator-and-MIA moments: theirs, in their folder, never the repo."""

    def __init__(self, context=None, data_dir: Optional[Path] = None) -> None:
        """Creator and MIA moments for the Chronicles (personal, DEC-0002): saga_moments.json in data/, kept on this
        device.
        """
        self.context = context
        self.data_dir = Path(data_dir) if data_dir is not None else ROOT / "data"
        self._file = self.data_dir / _FILE
        self.moments: list[dict] = []
        self._load()

    def _load(self) -> None:
        """Reads the moments; an unreadable file is logged and starts a new list. Sealed at rest (DEC-0126): a sealed file is opened; one that won't open is copied aside and starts empty."""
        try:
            self.moments = json.loads(open_text(self._file)).get("moments", [])
        except FileNotFoundError:
            self.moments = []
        except (OSError, ValueError):
            log.exception("Couldn't read the Chronicles moments; starting a new list")
            self.moments = []

    def _save(self) -> None:
        """Writes the moments atomically."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._file, json.dumps({"moments": self.moments}, indent=2, ensure_ascii=False) + "\n")

    def add(self, summary: str, said: str = "", replied: str = "") -> dict:
        """Keeps a moment (what happened, what was said and replied, each trimmed), private and proposed until Zac decides."""
        moment = {"id": f"M-{len(self.moments) + 1:04d}", "at": _now(), "summary": " ".join(summary.split())[:600],
                  "said": said[:600], "replied": replied[:600], "category": "moment", "timeline": "real",
                  "privacy": "private", "approved": "proposed"}
        self.moments.append(moment)
        self._save()
        return moment

    def mark(self, moment_id: str, privacy: str) -> dict:
        """Marks a moment's privacy; only "series" counts as approved for the comic."""
        if privacy not in PRIVACY:
            raise ValueError(f"Privacy is one of {', '.join(PRIVACY)}.")
        found = next((m for m in self.moments if m["id"] == moment_id), None)
        if found is None:
            raise ValueError(f"No moment {moment_id}.")
        found["privacy"] = privacy
        found["approved"] = "yes" if privacy == "series" else "no"
        self._save()
        return found

    def recent(self, count: int = 50) -> list[dict]:
        """The latest moments."""
        return self.moments[-count:]


def remember_command(context, text: str) -> Optional[str]:
    """"MIA, remember this for the Chronicles" (and "keep that private"): MIA's reply, or None.
    Kept as a personal moment, private until Zac says it's for the series."""
    m = REMEMBER.match(text or "")
    moments = getattr(context, "saga_moments", None)
    if moments is None:
        return None
    try:
        from core.child_accounts import is_child
        from core.person_settings import person_id

        if is_child(context, person_id(context)):
            return None
    except Exception:
        log.exception("Couldn't check whether the saga's reader is a child")
    if m:
        said = (m.group(1) or m.group(2) or "").strip()
        asked = replied = ""
        traces = getattr(context, "traces", None)
        last = traces.recent(1)[-1] if traces is not None and traces.recent(1) else {}
        if not said:  # "this" is what was just said
            asked, replied = last.get("asked", ""), last.get("said", "")
            said = asked or replied
        if not said:
            return "Tell me what to remember for the Chronicles, like “remember this for the Chronicles: the first council meeting.”"
        moment = moments.add(said, asked, replied)
        return (f"Kept for the Chronicles ({moment['id']}). It stays private until you mark it for the series; "
                "say “keep that private” to keep it out for good.")
    if PRIVATE.match(text or ""):
        if not moments.recent(1):
            return None
        moment = moments.mark(moments.recent(1)[-1]["id"], "never")
        return f"{moment['id']} stays out of the Chronicles."
    return None
