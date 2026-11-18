"""
gui.os_shell
==============

MIA's shell in her own desktop session on MIA OS (FW-03, DEC-0227, DEC-0278): one frameless, full-screen window
showing her web front end, run by KWin as the session's one client (`os/files/mia-session`). Ordinary windows open
beside it.

    python -m gui.os_shell                          # in the MIA session
    python -m gui.os_shell --screenshot out.png --after 25   # for the VM test: save what it shows, then quit

**How it finds her.** It reads the session file her runtime writes (`core/desktop_session.py`), which holds the local
address and a sign-in token, and opens her front end.

**When she isn't there.** It shows a short "MIA is starting" page and looks once a second. If no session file
appears within `WAIT_SECONDS` (30, REQ-UX-022), or her server doesn't answer, it shows a **recovery page** instead. The page is written here, with no server, and offers:
- trying again;
- a terminal;
- her log;
- signing out to choose the Plasma session.

Those four are links with this window's own scheme (`mia-shell:`), handled here and never by a page from the network.

**What it says.** It prints one line when it settles, "showing: front end" or "showing: recovery", so the VM test can
tell which.

Qt is imported only inside `main`, so the pure parts (`step`, `waiting_page`, `recovery_page`, `action_for`)
test without a display.
"""

from __future__ import annotations

import html
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable, Optional

from core import desktop_session

WAIT_SECONDS = 30
SCHEME = "mia-shell"
ACTIONS = ("retry", "terminal", "log", "signout")


def answers(url: str, timeout: float = 2.0) -> bool:
    """Whether her server answers at this address (its front end's page)."""
    try:
        with urllib.request.urlopen(url.split("#", 1)[0], timeout=timeout) as r:
            return 200 <= r.status < 400
    except (urllib.error.URLError, OSError, ValueError):
        return False


def step(session: Optional[dict], reachable: Callable[[str], bool], now: float, deadline: float) -> tuple:
    """Pure logic. One look for her: ("open", url) when her session is there and her server answers, ("recover", None)
    once the wait is over, else ("wait", None)."""
    if session is not None:
        url = desktop_session.front_end_url(session)
        if reachable(url):
            return "open", url
    return ("recover", None) if now >= deadline else ("wait", None)


def waiting_page() -> str:
    """Pure logic. What's shown while it looks for her (for up to WAIT_SECONDS)."""
    return ("<!doctype html><html><head><meta charset='utf-8'><title>MIA</title>"
            "<style>body{font:18px system-ui,sans-serif;margin:40vh 10vw;background:#0d1117;color:#e6edf3}</style>"
            "</head><body><p>MIA is starting…</p></body></html>")


def recovery_page(why: str) -> str:
    """Pure logic. The page shown when she isn't answering: what's wrong, and the four ways on."""
    links = {"retry": "Try again", "terminal": "Open a terminal", "log": "Show MIA's log",
             "signout": "Sign out (choose Plasma at the login screen)"}
    items = "".join(f'<li><a href="{SCHEME}:{a}">{html.escape(t)}</a></li>' for a, t in links.items())
    return ("<!doctype html><html><head><meta charset='utf-8'><title>MIA isn't answering</title>"
            "<style>body{font:18px system-ui,sans-serif;margin:10vh 10vw;background:#0d1117;color:#e6edf3}"
            "a{color:#7fd4ff}li{margin:.8em 0}</style></head><body>"
            f"<h1>MIA isn't answering</h1><p>{html.escape(why)}</p><p>Your computer works without her:</p>"
            f"<ul>{items}</ul></body></html>")


def action_for(url: str) -> Optional[str]:
    """Pure logic. Which of the recovery page's actions a link asks for, or None for anything else."""
    scheme, _, rest = (url or "").partition(":")
    return rest if scheme == SCHEME and rest in ACTIONS else None


def run_action(action: str) -> None:
    """Does one recovery action outside the window (a terminal, the log, signing out); `retry` is the window's own."""
    commands = {
        "terminal": ["konsole"],
        "log": ["konsole", "-e", "journalctl", "--user", "-u", "mia-runtime", "-f"],
        "signout": ["loginctl", "terminate-session", ""],  # this session (its id comes from the environment)
    }
    command = commands.get(action)
    if command is None:
        return
    if action == "signout":
        import os

        command[-1] = os.environ.get("XDG_SESSION_ID", "")
    try:
        subprocess.Popen(command, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except OSError as problem:
        print(f"couldn't run {command[0]}: {problem}", flush=True)


def main(argv: Optional[list] = None) -> int:
    """Opens the shell full screen; with `--screenshot PATH --after SECONDS`, saves what it shows and quits."""
    args = list(sys.argv[1:] if argv is None else argv)
    shot = args[args.index("--screenshot") + 1] if "--screenshot" in args else ""
    after = float(args[args.index("--after") + 1]) if "--after" in args else 20.0
    path = desktop_session.path_from_env()

    from PySide6.QtCore import Qt, QTimer, QUrl
    from PySide6.QtWebEngineCore import QWebEnginePage
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv[:1])

    class Page(QWebEnginePage):
        """Keeps the recovery page's own links (`mia-shell:`) in this window."""

        def acceptNavigationRequest(self, url, kind, main_frame):  # noqa: N802 - Qt's name
            """Handles a `mia-shell:` link here; every other address loads as usual."""
            action = action_for(url.toString())
            if action is None:
                return super().acceptNavigationRequest(url, kind, main_frame)
            if action == "retry":
                QTimer.singleShot(0, show)
            else:
                run_action(action)
            return False

    view = QWebEngineView()
    view.setPage(Page(view))
    view.setWindowTitle("MIA")
    view.setWindowFlags(Qt.WindowType.FramelessWindowHint)

    state = {"deadline": 0.0}

    def show() -> None:
        """Starts looking for her: the waiting page now, then a look each second (the window never freezes)."""
        state["deadline"] = time.monotonic() + WAIT_SECONDS
        view.setHtml(waiting_page())
        look()

    def look() -> None:
        """One look: her front end when she answers, the recovery page once the wait is over, else again in a second."""
        session = desktop_session.read(path) if path else None
        what, url = step(session, answers, time.monotonic(), state["deadline"] if path else 0.0)
        if what == "open":
            view.setUrl(QUrl(url))
            print("showing: front end", flush=True)
        elif what == "recover":
            why = ("Her runtime didn't start within 30 seconds." if path else
                   "This session doesn't know where to find her (no session file is set).")
            view.setHtml(recovery_page(why))
            print("showing: recovery", flush=True)
        else:
            QTimer.singleShot(1000, look)

    view.showFullScreen()
    show()
    if shot:
        def save() -> None:
            """Saves the window as it looks now and quits (the VM test)."""
            view.grab().save(shot)
            print(f"saved: {shot}", flush=True)
            app.quit()
        QTimer.singleShot(int(after * 1000), save)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
