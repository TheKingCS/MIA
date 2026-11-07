"""
modules.web_home
==================

"Home (preview)" (2026-10-05, Phase 2, DEC-0012/DEC-0013): MIA's new web
front end (`web/`, Muse's) shown inside the desktop window, so the first
vertical slice (engine → /api/state → web Home → an action → live update)
runs on the real devices (the owner's new computer first, DEC-0015)
before anything else moves over.

How: MIA's local server (core/phone_server.py `ensure_local()`, loopback
only; with phone access off, nothing from outside gets in) serves
`web/`; this app opens it in a built-in browser (QtWebEngine) already
signed in as whoever is at the desktop (a local session token), with
their text size and contrast. When someone else signs in, it reloads as
them. If this computer's PySide6 has no QtWebEngine, it offers to open
the page in the normal browser instead.

Since 2026-11-07 (Zac: "the only way I am able to view most of MIA is
through the Home Preview app") the desktop window opens on this, full size
(gui/main_window.py's web mode): the web front end is MIA on the desktop,
and the Qt screens are the classic view (Ctrl+Shift+C). A page asking for
an app that lives only in the PC app (a `/desktop-open/<id>` link, the
Apps page's "Open on this PC") is caught here and opened in the window.
"""

from __future__ import annotations

from typing import Optional
from urllib.parse import urlencode

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from core.logger import get_logger
from modules.module_base import ModuleBase

log = get_logger(__name__)


def web_home_url(base: str, token: str, scale: float = 1.0, high_contrast: bool = False) -> str:
    """Pure logic. The page address: that it's in the desktop window and the
    look settings in the query, the sign-in token in the fragment (never sent
    to the server or logged)."""
    query = {"desktop": "1"}
    if scale and scale != 1.0:
        query["scale"] = f"{scale:g}"
    if high_contrast:
        query["contrast"] = "high"
    return f"{base}/web/" + (f"?{urlencode(query)}" if query else "") + f"#token={token}"


class WebHomeModule(ModuleBase):
    """Home on the desktop: MIA's web front end (web/) shown in the built-in browser, signed in as whoever is signed in here, in their text size and contrast; since DEC-0124 the window opens on it, and its PC-only app links open in the window."""
    module_id = "web_home"
    display_name = "Home"
    description = "MIA herself: her presence, today's one thing, and a chat with her."
    icon = "\U0001F52E"  # crystal ball: MIA's presence

    def __init__(self, context) -> None:
        """Nothing shown yet: the browser view (or the message when there's none) is made in get_widget()."""
        super().__init__(context)
        self._view = None
        self._message: Optional[QLabel] = None
        self._url = ""

    def on_load(self) -> None:
        """Reloads the page when someone else signs in or the display settings change."""
        super().on_load()
        self.context.events.subscribe("profile.switched", lambda **_: self.reload())
        self.context.events.subscribe("display.changed", lambda **_: self.reload())

    def _address(self) -> Optional[str]:
        """The page's address: the local server (started if needed) with a session for the signed-in person and their text scale and contrast; None when there's no server, no one signed in, or no session."""
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
        return web_home_url(server.local_url, token, scale, contrast)

    def _open_on_pc(self, module_id: str) -> None:
        """A page asked for an app that lives only in the PC app: the window opens it (its classic screen)."""
        self.context.events.publish("assistant.open_module_requested", module_id=module_id)

    def reload(self) -> None:
        """Loads the page again for the current person (or updates the message saying why it can't); nothing before the page was first opened."""
        if self._view is None and self._message is None:
            return  # not opened yet
        self._url = self._address() or ""
        if self._view is not None and self._url:
            self._view.setUrl(QUrl(self._url))
        elif self._message is not None:
            self._message.setText(self._explain())

    def _explain(self) -> str:
        """Why Home can't show: the local server's last problem, or that someone needs to sign in."""
        server = getattr(self.context, "phone_server", None)
        problem = getattr(server, "last_error", "") if server is not None else "MIA's local server isn't available."
        return problem or "Sign in to see your Home."

    def get_widget(self) -> QWidget:
        """The page: the web front end in QtWebEngine (its page catching /desktop-open/ links), or, without QtWebEngine or an address, a message saying why with a way to open it in the system browser."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        self._url = self._address() or ""
        try:
            from PySide6.QtWebEngineWidgets import QWebEngineView
        except ImportError:
            QWebEngineView = None
            log.warning("QtWebEngine isn't available; Home (preview) offers the normal browser.")
        if QWebEngineView is not None and self._url:
            self._view = QWebEngineView(widget)
            page = _desktop_page(self._view, self._open_on_pc)
            if page is not None:
                self._view.setPage(page)
            self._view.setUrl(QUrl(self._url))
            layout.addWidget(self._view)
            return widget
        self._message = QLabel(self._explain() if not self._url else
                               "This computer can't show the new Home inside MIA (no QtWebEngine). "
                               "Open it in your browser instead:")
        self._message.setWordWrap(True)
        layout.addWidget(self._message)
        if self._url:
            button = QPushButton("Open in browser")
            button.setObjectName("ModuleButton")
            button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(self._url)))
            layout.addWidget(button)
        layout.addStretch(1)
        return widget


def _desktop_page(view, open_on_pc):
    """The web view's page, catching `/desktop-open/<module id>` links (an app only in the PC app) and handing the
    id to open_on_pc instead of navigating; None without QtWebEngine."""
    try:
        from PySide6.QtWebEngineCore import QWebEnginePage
    except ImportError:
        return None

    class DesktopPage(QWebEnginePage):
        """A page that hands "open this PC-only app" links to the desktop window."""

        def acceptNavigationRequest(self, url, nav_type, is_main_frame):  # noqa: N802 (Qt's name)
            """Navigates as usual, except a /desktop-open/ link, which opens the app it names in the window."""
            if url.path().startswith("/desktop-open/"):
                module_id = url.path().rsplit("/", 1)[-1]
                if module_id:
                    open_on_pc(module_id)
                return False
            return super().acceptNavigationRequest(url, nav_type, is_main_frame)

    return DesktopPage(view)
