"""
modules.knowledge.zim_url
============================

Pure QUrl <-> (pack_id, entry_path) conversion, isolated from
ZimTextBrowser's resource-loading logic so it's testable without a
QApplication/event loop (QUrl itself needs neither, unlike QTextBrowser)
— same "pure logic split out of the widget" pattern as
modules/files_mod/file_operations.py and modules/notes/module.py's
format_entry_row.

Custom "zim" URL scheme: host is the pack_id, path is the ZIM-internal
entry path. This piggybacks on QUrl's own RFC 3986 relative-URL
resolution (QUrl.resolved(), used internally by QTextBrowser.setSource()
when the user clicks a link) for correctly interpreting the relative
hrefs/srcs a real scraped ZIM page contains (including "../"-style
parent references) — exactly how those paths are authored to be
resolved when normally served over HTTP by kiwix-serve. Hand-parsing
that resolution ourselves would be reinventing a well-specified wheel.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QUrl

ZIM_SCHEME = "zim"


def entry_to_url(pack_id: str, entry_path: str) -> QUrl:
    url = QUrl()
    url.setScheme(ZIM_SCHEME)
    url.setHost(pack_id)
    url.setPath("/" + entry_path)
    return url


def url_to_entry(url: QUrl) -> Optional[tuple[str, str]]:
    """Returns (pack_id, entry_path), or None if `url` isn't a zim:// URL (e.g. an external http(s) link in the content)."""
    if url.scheme() != ZIM_SCHEME:
        return None
    return url.host(), url.path().lstrip("/")
