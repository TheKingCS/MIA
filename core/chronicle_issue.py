"""
core.chronicle_issue
======================

*MIA: The Chronicles*, the weekly issue (build plan step 17, DEC-0085 and
DEC-0086; the Story Bible is `docs/chronicles/`, the archive `core/saga.py`).

**The material** (`material()`): approved archive events, marked for the
series, that no issue has used yet, oldest first: the series follows the real
timeline. Personal moments never come in here.

**The script** (`draft()`): one scene a panel, made in code from each event
(its caption says what happened, and names the event behind it); the local
model only writes the characters' lines, in each one's voice from their file,
held to a schema; without a model, the captions carry the issue alone. Every
panel also gets a drawing prompt from the characters' appearances and the
series' visual identity (`docs/chronicles/visual.md`).

**Continuity, checked in code** (`check()`, the Story Bible's five rules):

1. every real panel names an approved, series event;
2. real means built: an event that's planned or imagined is drawn as the
   fictional timeline, never as done;
3. only characters from the Bible speak;
4. nothing private;
5. names are fictional: no real product name (or the Creator's own) anywhere
   in the issue.

An issue with a problem stays a draft and says what's wrong. **Zac approves
each issue** (`approve()`): only then are its events marked as used and the
issue listed in `docs/chronicles/issues.md`. Issues live in `work/saga/issues/`
(their text is the series' own: approved events, fictional names); their
panels are drawn by the local image model (`tools/chronicle_panels.py`, in its
own environment) into `data/chronicles/`, kept off the repo.
"""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Callable, Optional

from core.atomic_write import atomic_write_text
from core.logger import get_logger

log = get_logger(__name__)

ROOT = Path(__file__).resolve().parent.parent
BIBLE = ROOT / "docs" / "chronicles"
PANELS = ROOT / "data" / "chronicles"
PER_ISSUE = 4  # events an issue tells
MODEL = "qwen2.5:14b"
# Real names that must never appear in the series (DEC-0087): the products, their makers, and the Creator's name.
REAL_NAMES = ("claude", "chatgpt", "openai", "anthropic", "codex", "copilot", "github", "qwen", "ollama", "gemini",
              "llama", "zac")
STATUSES = ("draft", "checked", "approved")


def _issues_dir(root: Path) -> Path:
    """Where the series' issues are kept."""
    return root / "issues"


# ------------------------------------------------------------------ the Bible

def cast(bible: Path = BIBLE) -> dict:
    """Series name -> {inside, appearance, voice}, from the Bible's characters."""
    out = {}
    readme = (bible / "characters" / "README.md").read_text(encoding="utf-8")
    for line in readme.splitlines():
        m = re.match(r"^\|\s*\*\*(.+?)\*\*\s*\|[^|]*\|\s*(.+?)\s*\|\s*\[(.+?)\]", line)
        if not m:
            continue
        name, inside, file = m.groups()
        text = (bible / "characters" / file).read_text(encoding="utf-8")
        look = re.search(r"\*\*Appearance:\*\*\s*(.+?)(?:\n\n|\Z)", text, re.S)
        voice = re.search(r"\*\*Voice:\*\*\s*(.+?)(?:\n\n|\Z)", text, re.S)
        out[name] = {"inside": inside, "appearance": " ".join(look.group(1).split()) if look else "",
                     "voice": " ".join(voice.group(1).split()) if voice else ""}
    return out


def series_name(member: str, roster: dict) -> Optional[str]:
    """Pure logic. The series name of someone the archive names by their real name ("claude", "zac")."""
    low = (member or "").lower()
    for name, info in roster.items():
        inside = info["inside"].lower()
        if low and (low == inside or low in inside.split() or inside.startswith(low)):
            return name
    if low in ("zac", "creator"):
        return "The Creator"
    if low in ("ollama", "qwen"):
        return "Ember"
    if low == "ollama-coder":
        return "Anvil"
    return None


# ------------------------------------------------------------------ the material

def material(root: Optional[Path] = None, n: int = PER_ISSUE) -> list[dict]:
    """The next events an issue can tell: approved, meant for the series, not told yet, oldest first, at most
    PER_ISSUE (4).
    """
    from core import saga

    root = root or saga.SAGA
    found = [e for e in saga.events(root) if e.get("approved") == "yes" and e.get("privacy") == "series"
             and not e.get("issue")]
    return sorted(found, key=lambda e: e.get("at", ""))[:n]


# ------------------------------------------------------------------ the script

LINES_PROMPT = """You write dialogue for MIA: The Chronicles, a comic about building an AI called MIA. One panel at a
time: below is what happened (true, from the project's record), who is in the scene and how each one talks. Write one
or two short lines for some of them: plain, warm, specific to what happened, true to each voice. Never use a real
product or company name; only the names given. Don't add events. Reply with JSON: {{"lines": [{{"who": "<a name
below>", "line": "..."}}]}}.

What happened: {summary}
In the scene: {who}"""

SCHEMA = {"type": "object", "properties": {"lines": {"type": "array", "items": {"type": "object", "properties": {
    "who": {"type": "string"}, "line": {"type": "string"}}, "required": ["who", "line"]}}}, "required": ["lines"]}

STYLE = ("comic book panel, clean line art, digital painting, an inventor's private workshop at night, dark graphite "
         "layers, fine holographic lines, electric cyan light")


def _ollama(prompt: str, schema: dict) -> str:
    """Asks the local model (qwen2.5:14b) with a JSON schema for its reply, at temperature 0.6 for some variety in the
    lines.
    """
    import urllib.request

    body = json.dumps({"model": MODEL, "prompt": prompt, "stream": False, "format": schema,
                       "options": {"temperature": 0.6}}).encode("utf-8")
    request = urllib.request.Request("http://127.0.0.1:11434/api/generate", data=body,
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=300) as answer:
        return json.loads(answer.read()).get("response", "")


def _clean(text: str) -> str:
    """Pure logic. Real names out of archive text, as the series' own (the Creator, Forge...)."""
    out = str(text or "")
    whole, words = [], []
    for name, info in _roster_cache().items():
        inside = re.sub(r"\(.*?\)", "", info["inside"]).strip()  # "Qwen Coder (local)" -> "Qwen Coder"
        if name in ("MIA", "The Creator"):
            continue
        whole.append((inside, name))
        words.extend((w, name) for w in inside.split() if re.fullmatch(r"[A-Za-z][\w-]{2,}", w))
    taken = set()
    for real, name in sorted(whole, key=lambda p: -len(p[0])) + sorted(words, key=lambda p: -len(p[0])):
        if real.lower() in taken:
            continue  # "Qwen" is Ember's and Anvil's: the whole names went first
        out = re.sub(rf"\b{re.escape(real)}\b", name, out, flags=re.IGNORECASE)
        taken.add(real.lower())
    return re.sub(r"\bZac\b", "the Creator", out)


_ROSTER: dict = {}


def _roster_cache() -> dict:
    """The series' characters from the Story Bible, read once."""
    if not _ROSTER:
        _ROSTER.update(cast())
    return _ROSTER


def scene(event: dict, roster: dict, ask: Optional[Callable] = None) -> dict:
    """One panel from one event: its caption in code, its lines from the model, its drawing prompt."""
    who = [n for n in dict.fromkeys(series_name(m, roster) for m in event.get("involved", [])) if n]
    if "MIA" not in who:
        who = ["MIA"] + who
    real = event.get("timeline") == "real" and event.get("status") == "built"
    caption = _clean(event.get("summary") or event.get("title", ""))
    caption = (caption if real else f"One day, perhaps: {caption}")[:400]
    lines = []
    if ask is not False:
        try:
            said = json.loads((ask or _ollama)(LINES_PROMPT.format(
                summary=caption, who="; ".join(f"{n}: {_clean(roster.get(n, {}).get('voice', ''))}" for n in who)),
                SCHEMA))
            lines = [{"who": l["who"], "line": " ".join(str(l["line"]).split())[:220]}
                     for l in said.get("lines", [])[:3] if l.get("who") and l.get("line")]
        except Exception:
            log.info("Chronicles: no lines for %s; the caption carries it", event.get("id"))
    looks = "; ".join(f"{n}: {roster[n]['appearance'][:160]}" for n in who if roster.get(n, {}).get("appearance"))
    return {"event": event["id"], "real": real, "caption": caption, "lines": lines, "who": who,
            "draw": _clean(f"{STYLE}. {looks}")[:900]}  # the Bible's files name the real people: the prompt never


def draft(number: Optional[int] = None, root: Optional[Path] = None, ask: Optional[Callable] = None,
          today: Optional[date] = None) -> Optional[dict]:
    """The next issue from the material, checked; None when there's nothing new to tell."""
    from core import saga

    root = root or saga.SAGA
    events = material(root)
    if not events:
        return None
    roster = _roster_cache()
    taken = [int(p.stem[2:]) for p in _issues_dir(root).glob("I-*.json")] if _issues_dir(root).exists() else []
    number = number or (max(taken) + 1 if taken else 1)
    first = events[0]
    issue = {"id": f"I-{number:04d}", "number": number, "title": _clean(first.get("title", "")) or "Untitled",
             "week": (today or date.today()).isocalendar()[:2], "events": [e["id"] for e in events],
             "panels": [scene(e, roster, ask) for e in events], "status": "draft",
             "made": datetime.now().isoformat(timespec="seconds")}
    issue["problems"] = check(issue, {e["id"]: e for e in saga.events(root)}, roster)
    issue["status"] = "checked" if not issue["problems"] else "draft"
    _save(issue, root)
    return issue


def _save(issue: dict, root: Path) -> None:
    """Writes an issue atomically (I-0001.json)."""
    _issues_dir(root).mkdir(parents=True, exist_ok=True)
    atomic_write_text(_issues_dir(root) / f"{issue['id']}.json", json.dumps(issue, indent=1, ensure_ascii=False))


# ------------------------------------------------------------------ continuity (pure)

def check(issue: dict, events: dict, roster: dict) -> list[str]:
    """Pure logic. Every way an issue breaks the Story Bible's rules ([] when it keeps them)."""
    problems = []
    names = set(roster) | {"MIA", "The Creator", "Narrator"}
    for i, panel in enumerate(issue.get("panels", []), 1):
        event = events.get(panel.get("event"))
        if event is None or event.get("approved") != "yes":
            problems.append(f"Panel {i}: names {panel.get('event') or 'no event'}, which isn't an approved event (rule 1).")
            continue
        if panel.get("real") and not (event.get("timeline") == "real" and event.get("status") == "built"):
            problems.append(f"Panel {i}: shows {event['id']} as real, but it's {event.get('status')} (rule 2).")
        if event.get("privacy") != "series":
            problems.append(f"Panel {i}: {event['id']} is {event.get('privacy')} (rule 4).")
        for line in panel.get("lines", []):
            if line.get("who") not in names:
                problems.append(f"Panel {i}: {line.get('who')!r} isn't a character in the Bible (rule 3).")
    text = json.dumps({k: issue.get(k) for k in ("title", "panels")}, ensure_ascii=False).lower()
    for real in REAL_NAMES:
        if re.search(rf"\b{real}\b", text):
            problems.append(f"The issue says {real!r}: names in the series are fictional (rule 5).")
    return problems


# ------------------------------------------------------------------ Zac's yes

def issues(root: Optional[Path] = None) -> list[dict]:
    """Every issue, by number."""
    from core import saga

    folder = _issues_dir(root or saga.SAGA)
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(folder.glob("I-*.json"))] if folder.exists() else []


def approve(issue_id: str, root: Optional[Path] = None, bible: Path = BIBLE) -> dict:
    """Zac approves an issue: its events are marked as told, and it's listed in the Bible's issues."""
    from core import saga

    root = root or saga.SAGA
    issue = next((i for i in issues(root) if i["id"] == issue_id.upper()), None)
    if issue is None:
        raise ValueError(f"No issue {issue_id}.")
    if issue["status"] != "checked":
        raise ValueError("It has continuity problems to fix first: " + "; ".join(issue.get("problems", [])[:3]))
    for event in saga.events(root):
        if event["id"] in issue["events"]:
            event["issue"] = issue["id"]
            saga._save(event, root)
    issue["status"], issue["approved"] = "approved", datetime.now().isoformat(timespec="seconds")
    _save(issue, root)
    listing = bible / "issues.md"
    text = listing.read_text(encoding="utf-8")
    row = (f"| {issue['number']:03d} | {issue['title']} | {issue['week'][0]}-W{issue['week'][1]:02d} | approved | "
           f"{', '.join(issue['events'])} |")
    text = text.replace("| — | *none yet* | | | |\n", "") if "*none yet*" in text else text
    marker = "|---|---|---|---|---|\n"
    text = text.replace(marker, marker + row + "\n", 1)
    atomic_write_text(listing, text)
    return issue


def due(today: Optional[date] = None, root: Optional[Path] = None) -> bool:
    """Sundays, on the PC: there's untold material and no issue drafted this week."""
    from core import loops

    today = today or date.today()
    if today.weekday() != 6 or not loops._has_repo() or not material(root):
        return False
    week = list(today.isocalendar()[:2])
    return not any(list(i.get("week", [])) == week for i in issues(root))


def launch() -> None:
    """This week's issue, drafted and drawn in a process of its own (the models take a few minutes)."""
    import os
    import subprocess
    import sys

    if os.environ.get("PYTEST_CURRENT_TEST"):
        return  # never from a test run
    from core.dev_lab import _python

    PANELS.mkdir(parents=True, exist_ok=True)
    with open(PANELS / "last_draft.log", "w", encoding="utf-8") as out:
        subprocess.Popen([_python(), "-m", "tools.chronicle_issue", "draft"], cwd=str(ROOT), stdout=out,
                         stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
                         | getattr(subprocess, "DETACHED_PROCESS", 0) if sys.platform == "win32" else 0)


def panel_prompts(issue: dict) -> list[dict]:
    """What tools/chronicle_panels.py draws: [{file, prompt}]."""
    return [{"file": f"{issue['id']}-{i:02d}.png", "prompt": p["draw"]} for i, p in enumerate(issue["panels"], 1)]
