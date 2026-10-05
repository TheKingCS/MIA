"""
modules.web_home
==================

"Home (preview)" (2026-10-05, Phase 2, DEC-0012/DEC-0013): MIA's new web
front end (`web/`, Muse's) shown inside the desktop window, so the first
vertical slice (engine → /api/state → web Home → an action → live update)
runs on the real desktop and the Pi 5 before anything else moves over.

How: MIA's local server (core/phone_server.py `ensure_local()`, loopback
only; with phone access off, nothing from outside gets in) serves
`web/`; this app opens it in a built-in browser (QtWebEngine) already
signed in as whoever is at the desktop (a local session token), with
their text size and contrast. When someone else signs in, it reloads as
them. If this computer's PySide6 has no QtWebEngine, it offers to open
the page in the normal browser instead.

A preview next to the current Home, not a replacement: the Qt Home stays
until the web one is proven on the Pi (DEC-0013).
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
    """Pure logic. The page address: look settings in the query, the
    sign-in token in the fragment (never sent to the server or logged)."""
    query = {}
    if scale and scale != 1.0:
        query["scale"] = f"{scale:g}"
    if high_contrast:
        query["contrast"] = "high"
    return f"{base}/web/" + (f"?{urlencode(query)}" if query else "") + f"#token={token}"


class WebHomeModule(ModuleBase):
    module_id = "web_home"
    display_name = "Home (preview)"
    description = "MIA's new Home, built on the web front end (Phase 2 preview)."
    icon = "\U0001F52E"  # crystal ball: MIA's presence

    def __init__(self, context) -> None:
        super().__init__(context)
        self._view = None
        self._message: Optional[QLabel] = None
        self._url = ""

    def on_load(self) -> None:
        super().on_load()
        self.context.events.subscribe("profile.switched", lambda **_: self.reload())
        self.context.events.subscribe("display.changed", lambda **_: self.reload())

    def _address(self) -> Optional[str]:
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

    def reload(self) -> None:
        if self._view is None and self._message is None:
            return  # not opened yet
        self._url = self._address() or ""
        if self._view is not None and self._url:
            self._view.setUrl(QUrl(self._url))
        elif self._message is not None:
            self._message.setText(self._explain())

    def _explain(self) -> str:
        server = getattr(self.context, "phone_server", None)
        problem = getattr(server, "last_error", "") if server is not None else "MIA's local server isn't available."
        return problem or "Sign in to see your Home."

    def get_widget(self) -> QWidget:
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
