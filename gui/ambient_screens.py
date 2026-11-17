"""
gui.ambient_screens
=====================

MIA's ambient view on the second monitor, flowing with however many monitors there are (DEC-0231; Zac, 2026-11-17,
Q-80: "MIA should be adaptable and understanding of available monitors so if I turn one off she flows with just 1").

`AmbientScreens` watches the monitors (Qt's screenAdded, screenRemoved and primaryScreenChanged, and the main window
moving between screens) and keeps one rule (`ambient_target`, pure logic): with a monitor the main window isn't on,
the ambient view (`web/ambient.html`, core/ambient.py) fills it, frameless and out of the taskbar; with one monitor
there is no ambient window, and Home on the main screen holds the same things. A monitor turned off or unplugged takes
its window with it at once; turned back on, the view returns, with nothing to set. `gui.ambient_screen` (on by
default) turns it off.

The page is the local web server's, signed in as whoever is signed in here, like Home's own window
(modules/web_home); `ambient_url` builds its address (the sign-in token in the fragment, never sent to the server).
Nothing here reads or changes a record.
"""

from __future__ import annotations

from typing import Optional, Sequence
from urllib.parse import urlencode

from core.logger import get_logger

log = get_logger(__name__)

KEY = "gui.ambient_screen"


def ambient_target(screens: Sequence[str], main: Optional[str]) -> Optional[str]:
    """Pure logic. The screen the ambient view goes on: the first one the main window isn't on, or None when there's
    only one (or none)."""
    others = [s for s in screens if s != main]
    return others[0] if len(screens) > 1 and others else None


def ambient_url(base: str, token: str, scale: float = 1.0, high_contrast: bool = False) -> str:
    """Pure logic. The ambient page's address: in the desktop window, the look settings in the query, the sign-in
    token in the fragment."""
    query = {"desktop": "1"}
    if scale and scale != 1.0:
        query["scale"] = f"{scale:g}"
    if high_contrast:
        query["contrast"] = "high"
    return f"{base}/web/ambient.html?{urlencode(query)}#token={token}"


class AmbientScreens:
    """The ambient window on the second monitor, made, moved and closed as monitors come and go (see the module's
    opening)."""

    def __init__(self, context, main_window) -> None:
        """Nothing shown yet: `start()` connects to the monitors and places the view."""
        self.context = context
        self.main_window = main_window
        self._view = None
        self._on: Optional[str] = None  # the screen the view is on
        self._started = False
        self._stopped = False

    def enabled(self) -> bool:
        """Whether the ambient view is wanted (`gui.ambient_screen`, on by default)."""
        return bool(self.context.config.get(KEY, True))

    def start(self) -> None:
        """Connects to the monitors and the main window's screen, then places the view; a second call does nothing."""
        if self._started:
            return
        from PySide6.QtGui import QGuiApplication

        app = QGuiApplication.instance()
        if app is None:
            return
        self._started = True
        app.screenAdded.connect(lambda _s: self.update())
        app.screenRemoved.connect(lambda _s: self.update())
        app.primaryScreenChanged.connect(lambda _s: self.update())
        handle = self.main_window.windowHandle()
        if handle is not None:
            handle.screenChanged.connect(lambda _s: self.update())
        self.context.events.subscribe("profile.switched", self._on_profile_switched)
        self.update()

    def _on_profile_switched(self, **_kwargs) -> None:
        """Someone else signed in: the page is signed in as them."""
        self.reload()

    def stop(self) -> None:
        """The main window is closing (or rebuilt for another person): the view closes and nothing here acts again."""
        self._stopped = True
        self.context.events.unsubscribe("profile.switched", self._on_profile_switched)
        self.close()

    def _address(self) -> Optional[str]:
        """The page's address for whoever is signed in here, or None without a server, a person or a session."""
        from core import accessibility
        from core.person_settings import person_id

        server = getattr(self.context, "phone_server", None)
        who = person_id(self.context)
        if server is None or who is None or not server.ensure_local():
            return None
        token = server.local_session(who)
        if token is None:
            return None
        size, contrast = accessibility.look_for(self.context)
        scale = accessibility.TEXT_SIZES.get(size, ("", 1.0))[1]
        return ambient_url(server.local_url, token, scale, contrast)

    def update(self) -> None:
        """Puts the view where the rule says (`ambient_target`), or closes it; any failure is only logged. Nothing
        after `stop()`."""
        if self._stopped:
            return
        try:
            from PySide6.QtGui import QGuiApplication

            screens = {s.name(): s for s in QGuiApplication.screens()}
            main = self.main_window.screen()
            target = ambient_target(list(screens), main.name() if main is not None else None) if self.enabled() \
                else None
            if target is None:
                self.close()
                return
            self._show_on(screens[target])
        except Exception:  # noqa: BLE001 - the ambient view never stops the window
            log.exception("Couldn't place the ambient view")

    def _show_on(self, screen) -> None:
        """Opens the view (made the first time) full screen on that screen."""
        from PySide6.QtCore import Qt, QUrl

        if self._view is None:
            url = self._address()
            if url is None:
                return
            from PySide6.QtWebEngineWidgets import QWebEngineView

            self._view = QWebEngineView()
            self._view.setWindowTitle("MIA · Ambient")
            self._view.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
            self._view.setUrl(QUrl(url))
        if self._on != screen.name():
            self._view.hide()
            self._view.setScreen(screen)
            self._view.setGeometry(screen.geometry())
            self._on = screen.name()
        self._view.showFullScreen()
        log.info("Ambient view on %s", screen.name())

    def reload(self) -> None:
        """Signs the page in as whoever is signed in now (closed and made again)."""
        self.close()
        self.update()

    def close(self) -> None:
        """Closes the view, if it's open."""
        if self._view is not None:
            self._view.close()
            self._view.deleteLater()
            self._view = None
            self._on = None
            log.info("Ambient view closed")
