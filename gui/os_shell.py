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

Those four are links with this window's own scheme (`mia-shell:`), handled here, only while the recovery page is
showing: such a link on any other page does nothing.

**When her runtime is restarted.** The front end it loaded holds a sign-in that ended with the old runtime. Every
few seconds the shell reads the session file again; when it's gone or names a new sign-in, it looks for her afresh.

**What it says.** It prints one line when it settles, "showing: front end" or "showing: recovery", and writes it
with the time to `shell-state` beside the session file (also "front end loaded" once the page is in), so the VM
test can tell which and how fast. `os/files/mia-shell` starts it again if it dies.

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
WATCH_SECONDS = 5  # how often the shell checks her runtime is still the one whose front end it loaded


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


def restarted(loaded: Optional[dict], now: Optional[dict]) -> bool:
    """Pure logic. Whether her runtime was restarted since the front end was loaded: the session file is gone, or
    it names another address or sign-in."""
    return loaded is not None and (now is None or now != loaded)


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


def state_file(session_path: Optional[Path]) -> Optional[Path]:
    """Pure logic. Where the shell says what it shows, beside the session file (`shell-state`); None without one."""
    return Path(session_path).parent / "shell-state" if session_path else None


def announce(what: str, where: Optional[Path], now: Optional[float] = None) -> None:
    """Says what the shell shows: printed, and written with the time (seconds since the epoch) to `where`, so a
    test or the session can see it reached her front end and how fast. Never raises."""
    print(f"showing: {what}", flush=True)
    if where is None:
        return
    try:
        where.write_text(f"{what}\t{time.time() if now is None else now:.2f}\n", encoding="utf-8")
    except OSError:
        pass


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
    """Opens the shell full screen; with `--screenshot PATH --after SECONDS`, saves what it shows and quits. Each
    state it reaches (front end, front end loaded, recovery) is announced beside the session file. While her front
    end shows, it checks every few seconds that her runtime is still the one it loaded from (`watch`)."""
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
            """Handles a `mia-shell:` link here, and only while this window's own recovery page is showing: a page
            from anywhere else that carries such a link is refused. Every other address loads as usual."""
            action = action_for(url.toString())
            if action is None:
                return super().acceptNavigationRequest(url, kind, main_frame)
            if not state.get("recovery"):
                return False
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
    said = state_file(path)
    view.loadFinished.connect(lambda ok: announce("front end loaded", said) if ok and
                              view.url().scheme().startswith("http") else None)

    def show() -> None:
        """Starts looking for her: the waiting page now, then a look each second (the window never freezes)."""
        state["deadline"] = time.monotonic() + WAIT_SECONDS
        state["recovery"], state["loaded"] = False, None
        view.setHtml(waiting_page())
        look()

    def look() -> None:
        """One look: her front end when she answers, the recovery page once the wait is over, else again in a second."""
        session = desktop_session.read(path) if path else None
        what, url = step(session, answers, time.monotonic(), state["deadline"] if path else 0.0)
        if what == "open":
            state["loaded"] = session
            view.setUrl(QUrl(url))
            announce("front end", said)
            QTimer.singleShot(WATCH_SECONDS * 1000, watch)
        elif what == "recover":
            why = ("Her runtime didn't start within 30 seconds." if path else
                   "This session doesn't know where to find her (no session file is set).")
            state["recovery"] = True
            view.setHtml(recovery_page(why))
            announce("recovery", said)
        else:
            QTimer.singleShot(1000, look)

    def watch() -> None:
        """While her front end is showing: when her runtime was restarted (its session file is gone or names a new
        sign-in), the page it loaded holds a sign-in that no longer works, so the shell looks for her again."""
        if state.get("loaded") is None:
            return
        gone = not answers(desktop_session.front_end_url(state["loaded"]))  # a runtime killed outright leaves its file
        state["misses"] = state.get("misses", 0) + 1 if gone else 0
        if restarted(state["loaded"], desktop_session.read(path) if path else None) or state["misses"] >= 2:
            state["misses"] = 0
            show()
        else:
            QTimer.singleShot(WATCH_SECONDS * 1000, watch)

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
