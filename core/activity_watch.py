"""
core.activity_watch
=====================

What he's working on (DEC-0197; Zac, 2026-11-17, Q-44: "Yes, mia should know what I am working on"; DEC-0217,
Q-74: it may shape when and which offers she makes). On the PC, MIA notes **the app and window title in front of
him**, so she can tie work to a project and answer "where was I?".

**The safeguards** (the review's, kept as DEC-0197 says):
- **names and titles only**: the program's name and its window's title, cut to `TITLE_CHARS`; never the screen,
  keystrokes or contents;
- **skipped**: password managers and private browser windows (`SKIP_APPS`, `SKIP_WORDS`), and MIA's own window;
- **an indicator while it's on**: the sidebar says so (`/api/shell` carries `noting`), and Settings shows it;
- **an erase button**: `activity.erase` (Settings, or "erase what you noted about my apps"), undoable like any
  change for a few minutes, then gone;
- **his own, kept 7 days** (`KEEP_DAYS`): `activity.json` in his folder (a personal store), sealed at rest like
  the others; never sent anywhere; never in a private or personal turn;
- **off with one press** (`activity.noting`, the setting `activity.on`); stop everything holds it too.

**How** (`foreground`): on Windows, the foreground window's title and its program (user32 and psutil); elsewhere
nothing yet (on MIA OS, a KWin script, Prompt 10). A background job samples every 30 seconds
(core/background_jobs.py, `activity_watch`); the same app and title within `JOIN_SECONDS` extends one span.

**What she does with it** (`working_on`): the app and title he spent most of the last `RECENT_MINUTES` on, and the
project whose name it mentions, if one does. Asked "what am I working on?" (`what_am_i_working_on`), she says so.
**When she speaks up** (DEC-0217, Q-74: what he's working on may shape when and which offers come, never creating
one): `focus` says he's focused (the window in front of him now, and one app and title for `FOCUS_MIN` of the last
`FOCUS_WINDOW` minutes); the communication gate then holds non-urgent offers as it does in flow, except one about
the project he's focused on (`about`).
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Optional

from core.actions import ACTION_TYPES, ActionError, ActionType
from core.atomic_write import atomic_write_text
from core.data_root import DATA_DIR
from core.logger import get_logger

log = get_logger(__name__)

_FILE = DATA_DIR / "activity.json"
SETTING = "activity.on"
KEEP_DAYS = 7
JOIN_SECONDS = 120  # the same app and title again within this extends its span
RECENT_MINUTES = 30
TITLE_CHARS = 120
FOCUS_WINDOW = 15  # minutes looked at for focus
FOCUS_MIN = 10  # minutes on one app and title in that window that count as focused
FOCUS_FRESH = 120  # seconds: the last look must be this recent (he's still there)
SKIP_APPS = ("keepass", "1password", "bitwarden", "lastpass", "dashlane", "keeper", "credentialuibroker",
             "lockapp", "logonui")
SKIP_WORDS = ("inprivate", "incognito", "private browsing", "password", "sign in", "log in")
OWN_TITLES = ("MIA ", "MIA —", "MIA ·")  # her own window


def keep_this(app: str, title: str) -> bool:
    """Pure logic. Whether a window may be noted: not a password manager, a private window, a sign-in, or MIA."""
    a, t = (app or "").lower(), (title or "").lower()
    if not a and not t:
        return False
    if any(s in a for s in SKIP_APPS) or any(w in t for w in SKIP_WORDS):
        return False
    return not any((title or "").startswith(o) for o in OWN_TITLES)


def foreground() -> Optional[tuple[str, str]]:
    """(program name, window title) of the window in front of him, or None where that can't be read (only Windows
    for now)."""
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        from ctypes import wintypes

        import psutil

        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return None
        length = user32.GetWindowTextLengthW(hwnd)
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        name = psutil.Process(pid.value).name().rsplit(".", 1)[0] if pid.value else ""
        return name, buffer.value
    except Exception:  # noqa: BLE001 - a window that can't be read is skipped
        return None


class ActivityLog:
    """What he worked on, as spans of one app and title (activity.json in his folder, written through
    atomic_write_text so an erase can be undone)."""

    def __init__(self, context=None, data_dir: Optional[Path] = None) -> None:
        """Loads the spans from a person's folder (or data/); an unreadable file starts empty."""
        from core.at_rest import open_text

        self.context = context
        self.data_dir = Path(data_dir) if data_dir is not None else _FILE.parent
        self._file = self.data_dir / _FILE.name
        self._spans: list[dict] = []
        if self._file.exists():
            try:
                self._spans = [s for s in json.loads(open_text(self._file)).get("spans", []) if isinstance(s, dict)]
            except (OSError, ValueError, TypeError, AttributeError):
                log.exception("activity.json unreadable, starting empty.")

    def _load(self) -> None:
        """Reads the file again (after an undo restored it)."""
        self.__init__(self.context, self.data_dir)

    def _save(self) -> None:
        """Writes the spans atomically."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._file, json.dumps({"spans": self._spans}, indent=1, ensure_ascii=False))

    def note(self, app: str, title: str, now: Optional[datetime] = None) -> bool:
        """Notes the window in front of him, if it may be noted; True when something was kept. Spans older than
        KEEP_DAYS go."""
        if not keep_this(app, title):
            return False
        now = now or datetime.now()
        at = now.isoformat(timespec="seconds")
        title = " ".join((title or "").split())[:TITLE_CHARS]
        last = self._spans[-1] if self._spans else None
        if last and last["app"] == app and last["title"] == title and \
                (now - datetime.fromisoformat(last["end"])).total_seconds() <= JOIN_SECONDS:
            last["end"] = at
        else:
            self._spans.append({"app": app, "title": title, "start": at, "end": at})
        cutoff = (now - timedelta(days=KEEP_DAYS)).isoformat(timespec="seconds")
        self._spans = [s for s in self._spans if s["end"] >= cutoff]
        self._save()
        return True

    def spans(self, since: Optional[datetime] = None) -> list[dict]:
        """The spans, oldest first, or those ending after `since`."""
        cut = since.isoformat(timespec="seconds") if since else ""
        return [dict(s) for s in self._spans if s["end"] >= cut]

    def erase(self) -> int:
        """Forgets everything noted; returns how many spans went."""
        gone = len(self._spans)
        self._spans = []
        self._save()
        return gone


def noting(context) -> bool:
    """Whether MIA notes his active app (`activity.on`, on since Zac's yes to Q-44; one press turns it off)."""
    from core import person_settings

    return bool(person_settings.get(context, SETTING, True))


def sample(context, now: Optional[datetime] = None, read: Callable[[], Optional[tuple[str, str]]] = foreground) -> bool:
    """One look at the window in front of him, kept when noting is on; the background job calls this."""
    store = getattr(context, "activity", None)
    if store is None or not noting(context):
        return False
    found = read()
    return store.note(found[0], found[1], now) if found else False


def _seconds(span: dict) -> float:
    """Pure logic. How long a span lasted (a single look counts as 30 seconds)."""
    return max(30.0, (datetime.fromisoformat(span["end"]) - datetime.fromisoformat(span["start"])).total_seconds())


def main_thing(spans: list[dict]) -> Optional[dict]:
    """Pure logic. The app and title with the most time among these spans, with its minutes; None for none."""
    totals: dict = {}
    for s in spans:
        key = (s["app"], s["title"])
        totals[key] = totals.get(key, 0.0) + _seconds(s)
    if not totals:
        return None
    (app, title), secs = max(totals.items(), key=lambda kv: kv[1])
    return {"app": app, "title": title, "minutes": round(secs / 60)}


def project_for(title: str, projects: list) -> Optional[str]:
    """Pure logic. The name of the project the title mentions (every word of the name, as words), or None."""
    words = set(re.findall(r"[a-z0-9]+", (title or "").lower()))
    for p in projects:
        name_words = set(re.findall(r"[a-z0-9]+", (getattr(p, "name", "") or "").lower())) - {"the", "a", "my"}
        if name_words and name_words <= words:
            return p.name
    return None


def working_on(context, now: Optional[datetime] = None) -> Optional[dict]:
    """What he's working on: {app, title, minutes, project or None}, from the last RECENT_MINUTES; None when nothing
    was noted (or noting is off)."""
    store = getattr(context, "activity", None)
    if store is None or not noting(context):
        return None
    now = now or datetime.now()
    found = main_thing(store.spans(now - timedelta(minutes=RECENT_MINUTES)))
    if found is None:
        return None
    projects = getattr(context, "projects", None)
    found["project"] = project_for(found["title"], projects.all_projects() if projects is not None else [])
    return found


def focus(context, now: Optional[datetime] = None) -> Optional[dict]:
    """He's focused (see the module's opening): {app, title, minutes, project}; None when he isn't, noting is off or
    nothing's been noted lately."""
    store = getattr(context, "activity", None)
    if store is None or not noting(context):
        return None
    now = now or datetime.now()
    spans = store.spans(now - timedelta(minutes=FOCUS_WINDOW))
    if not spans or (now - datetime.fromisoformat(spans[-1]["end"])).total_seconds() > FOCUS_FRESH:
        return None
    found = main_thing(spans)
    if found is None or found["minutes"] < FOCUS_MIN:
        return None
    projects = getattr(context, "projects", None)
    found["project"] = project_for(found["title"], projects.all_projects() if projects is not None else [])
    return found


def about(text: str, focus_name: str) -> bool:
    """Pure logic. Whether an offer's words are about what he's focused on (every word of its name, as words)."""
    name = set(re.findall(r"[a-z0-9]+", (focus_name or "").lower())) - {"the", "a", "my"}
    return bool(name) and name <= set(re.findall(r"[a-z0-9]+", (text or "").lower()))


def said(context) -> str:
    """"What am I working on?" in words."""
    if not noting(context):
        return "I'm not noting which app you're in; you can turn that on in Settings."
    found = working_on(context)
    if found is None:
        return "I haven't seen you working on anything in the last half hour."
    where = f"{found['app']}: {found['title']}" if found["title"] else found["app"]
    line = f"Mostly {where}, about {found['minutes']} minute{'s' if found['minutes'] != 1 else ''} lately."
    return line + (f" That looks like your {found['project']} project." if found.get("project") else "")


# ------------------------------------------------------------------ actions


def _describe_noting(context, params) -> str:
    """The card's sentence for `activity.noting`: on or off."""
    return ("Note which app and window title is in front of you (names and titles only, kept 7 days)"
            if params.get("on") else "Stop noting which app you're in")


def _set_noting(context, params) -> str:
    """Turns noting on or off (a setting of his, undoable)."""
    from core import person_settings

    on = bool(params.get("on"))
    person_settings.put(context, SETTING, on)
    return "I'll note which app you're in (names and titles only)." if on else "I've stopped noting which app you're in."


def _describe_erase(context, params) -> str:
    """The card's sentence for `activity.erase`; ActionError with nothing to erase."""
    store = getattr(context, "activity", None)
    if store is None:
        raise ActionError("There's nothing noted on this MIA.")
    count = len(store.spans())
    if not count:
        raise ActionError("There's nothing noted to erase.")
    return f"Erase what I noted about your apps ({count} stretch{'es' if count != 1 else ''} of the last 7 days)"


def _erase(context, params) -> str:
    """Forgets everything noted about his apps."""
    gone = context.activity.erase()
    return f"Erased {gone} stretch{'es' if gone != 1 else ''} of what you were working on."


ACTIVITY_ACTIONS = {a.kind: a for a in (
    ActionType("activity.noting", "Note My Active App", {"on": "true to note, false to stop"}, _describe_noting,
               _set_noting),
    ActionType("activity.erase", "Erase", {}, _describe_erase, _erase),
)}
ACTION_TYPES.update(ACTIVITY_ACTIONS)


def register_activity_actions(registry) -> None:
    """Registers what_am_i_working_on, set_activity_noting and erase_activity."""
    from core.actions import run_as_tool
    from core.assistant_actions import AssistantAction

    registry.register(AssistantAction(
        name="what_am_i_working_on", domain="system",
        description="What the person has mostly been working on in the last half hour (the app and window title in "
                    "front of them, and the project it belongs to), from what MIA noted (core/activity_watch.py).",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=lambda context, arguments: said(context),
        trigger_phrases=("what am i working on", "where was i", "what was i working on", "what have i been doing"),
        subjects=("working", "doing"),
    ))
    registry.register(AssistantAction(
        name="set_activity_noting", domain="system",
        description="Turn on or off MIA noting which app and window title is in front of the person.",
        parameters={"type": "object", "properties": {"on": {"type": "boolean", "description": "true to note"}},
                    "required": ["on"]},
        handler=lambda context, arguments: run_as_tool(context, "activity.noting", {"on": bool(arguments.get("on"))}),
        trigger_phrases=("stop noting my apps", "stop watching what i'm working on", "start noting my apps",
                         "note what i'm working on"),
        subjects=("noting", "apps"),
    ))
    registry.register(AssistantAction(
        name="erase_activity", domain="system",
        description="Erase everything MIA noted about which apps the person used.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=lambda context, arguments: run_as_tool(context, "activity.erase", {}),
        trigger_phrases=("erase what you noted about my apps", "forget which apps i used", "erase my activity"),
        subjects=("erase", "activity"),
        destructive=True,
    ))
