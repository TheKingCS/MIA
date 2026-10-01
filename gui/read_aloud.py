"""
gui.read_aloud
================

"Read this screen aloud" (2026-10-01, core/accessibility.py): MIA reads
the visible text of the open screen in her own voice, top to bottom.
Ctrl+Shift+R, or the profile menu; again to stop. Passwords are never
read.
"""

from __future__ import annotations

import re
import tempfile
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QLabel, QLineEdit, QListWidget, QPlainTextEdit, QTabBar, QTextEdit, QWidget

from core.accessibility import screen_text

_TAGS = re.compile(r"<[^>]+>")


def visible_lines(root: QWidget) -> list[str]:
    """The text a person sees on `root`, in reading order (top to bottom,
    left to right)."""
    found: list[tuple[int, int, str]] = []

    def add(widget: QWidget, text: str) -> None:
        if text and text.strip():
            where = widget.mapTo(root, QPoint(0, 0))
            found.append((where.y(), where.x(), text))

    for widget in root.findChildren(QWidget):
        if not widget.isVisibleTo(root) or not widget.isVisible() and root.isVisible():
            continue
        if isinstance(widget, QLabel):
            add(widget, _TAGS.sub(" ", widget.text()).replace("&nbsp;", " "))
        elif isinstance(widget, QLineEdit):
            if widget.echoMode() == QLineEdit.EchoMode.Normal:
                add(widget, widget.text())
        elif isinstance(widget, (QTextEdit, QPlainTextEdit)):
            add(widget, widget.toPlainText())
        elif isinstance(widget, QListWidget):
            items = [widget.item(i).text() for i in range(min(widget.count(), 15))]
            add(widget, "\n".join(items))
        elif isinstance(widget, QTabBar) and widget.currentIndex() >= 0:
            add(widget, f"{widget.tabText(widget.currentIndex()).replace('&&', 'and').replace('&', '')} tab")
    lines = []
    for _y, _x, text in sorted(found, key=lambda f: (f[0], f[1])):
        lines.extend(text.splitlines())
    return lines


class ReadAloud:
    """Speaks a screen; calling it again while speaking stops."""

    def __init__(self, context) -> None:
        self.context = context
        self._worker = None

    @property
    def speaking(self) -> bool:
        return self._worker is not None

    def toggle(self, root: Optional[QWidget]) -> str:
        """Start or stop. Returns what to show in the status bar."""
        voice = getattr(self.context, "voice", None)
        if self.speaking:
            if voice is not None:
                voice.stop_playback()
            return "Stopped reading."
        if voice is None or not voice.is_tts_available():
            return "MIA's voice isn't set up yet (Settings, Check My Setup)."
        text = screen_text(visible_lines(root)) if root is not None else ""
        if not text:
            return "There's nothing to read on this screen."
        from core.tts_worker import TTSWorker

        self._worker = TTSWorker(voice, text, Path(tempfile.gettempdir()) / "mia_read_aloud.wav")
        self._worker.finished.connect(self._on_finished)
        self._worker.start()
        return "Reading this screen aloud (Ctrl+Shift+R again to stop)."

    def _on_finished(self) -> None:
        if self._worker is not None:
            self._worker.deleteLater()
        self._worker = None
