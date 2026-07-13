"""
modules.knowledge.zim_text_browser
=====================================

ZimTextBrowser: a QTextBrowser that resolves "zim://<pack_id>/<entry_path>"
URLs against core.reference_library_manager.ReferenceLibraryManager
instead of the filesystem/network QTextBrowser normally expects.

Deliberately QTextBrowser, not QtWebEngine — see docs/ROADMAP.md's v0.4
breakdown for why (keeps requirements.txt light and stays inside the
Pi 5 resource budget). Renders basic HTML with no JavaScript, so
JS-heavy ZIM content (interactive Wikipedia templates) will render
imperfectly — an accepted tradeoff, not a bug to chase here.

Overriding loadResource() is QTextBrowser's documented extension point
for exactly this "resolve URLs against something other than the
filesystem" case (the same mechanism Qt's own Assistant help browser
uses). Relative links/images within a page resolve automatically via
QUrl's own resolution inside QTextBrowser.setSource() (see zim_url.py's
docstring), so a page's "../I/foo.png"-style relative paths work
without this class knowing anything about ZIM's namespace conventions.
Clicking a link therefore needs no code here beyond loadResource() —
QTextBrowser's default openLinks behavior already calls setSource()
for us, which is also what gives history/back/forward for free.

Deliberately forces its own plain white background (`setStyleSheet()`
on this widget itself) rather than inheriting whichever app-level theme
is active (gui/theme_manager.py, docs/ROADMAP.md milestone 13.2): ZIM
content is arbitrary third-party HTML authored assuming a normal light
document background, and any of the app's themes cascading onto it (the
same trap docs/KNOWN_ISSUES.md's closed "Header labels" bug hit) would
make most real content unreadable — this is the one deliberate exception
to "widgets don't set their own stylesheet" that milestone 13.2's
cleanup left in place, precisely because it needs to *not* inherit the
app-level theme.
"""

from __future__ import annotations

from PySide6.QtCore import QUrl
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QTextBrowser

from core.reference_library_manager import ReferenceLibraryManager
from modules.knowledge.zim_url import entry_to_url, url_to_entry


class ZimTextBrowser(QTextBrowser):
    def __init__(self, reference_library: ReferenceLibraryManager, parent=None) -> None:
        super().__init__(parent)
        self._reference_library = reference_library
        self.setOpenExternalLinks(False)  # never shell out to a system browser for e.g. citation links
        self.setStyleSheet("background-color: white; color: black;")

    def open_entry(self, pack_id: str, entry_path: str) -> None:
        self.setSource(entry_to_url(pack_id, entry_path))

    def loadResource(self, resource_type, url: QUrl):
        parsed = url_to_entry(url)
        if parsed is None:
            return None

        result = self._reference_library.get_entry_content(*parsed)
        if result is None:
            return None
        content, mimetype = result

        if mimetype.startswith("image/"):
            image = QImage()
            image.loadFromData(content)
            return None if image.isNull() else image

        return content.decode("utf-8", errors="replace")
