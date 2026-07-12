"""
tests.test_zim_url
=====================

Unit tests for modules.knowledge.zim_url's pure QUrl <-> (pack_id,
entry_path) conversion. QUrl needs no QApplication/event loop to
construct or parse, so — unlike modules.knowledge.zim_text_browser's
QTextBrowser subclass — this is safe to cover with plain pytest rather
than deferring to tests/run_module.py's manual harness.
"""

from __future__ import annotations

from PySide6.QtCore import QUrl

from modules.knowledge.zim_url import entry_to_url, url_to_entry


def test_entry_to_url_round_trips_through_url_to_entry():
    url = entry_to_url("wikipedia_medicine", "A/First_Aid")
    assert url_to_entry(url) == ("wikipedia_medicine", "A/First_Aid")


def test_entry_to_url_uses_the_zim_scheme():
    url = entry_to_url("demo", "home")
    assert url.toString() == "zim://demo/home"


def test_url_to_entry_strips_leading_slash_from_path():
    pack_id, entry_path = url_to_entry(entry_to_url("demo", "nested/page"))
    assert pack_id == "demo"
    assert entry_path == "nested/page"


def test_url_to_entry_returns_none_for_non_zim_schemes():
    assert url_to_entry(QUrl("https://example.com/some/page")) is None
    assert url_to_entry(QUrl("about:blank")) is None


def test_relative_link_resolves_against_a_zim_url_like_a_normal_web_page():
    """
    This is the exact mechanism QTextBrowser.setSource() relies on
    internally when the user clicks a relative link — see
    zim_text_browser.py's docstring. Verifying it here pins down the
    behavior the whole in-page-navigation feature depends on, without
    needing a QTextBrowser/QApplication to prove it.
    """
    base = entry_to_url("demo", "A/Some_Page")
    resolved = base.resolved(QUrl("../I/photo.png"))
    assert url_to_entry(resolved) == ("demo", "I/photo.png")
