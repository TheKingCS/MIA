"""
tests.test_reference_library_manager
=======================================

Unit tests for core.reference_library_manager. Isolates the library
root into a tmp_path scratch area (same monkeypatch pattern as
test_journal_manager.py's isolated_paths), and builds tiny real .zim
fixtures on the fly with libzim.writer rather than bundling a binary
fixture in the repo or depending on network access to fetch one —
both would sit oddly in an offline-first project's own test suite.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest
from libzim.writer import Creator, Hint, StringProvider
from libzim.writer import Item as ZimWriterItem

import core.reference_library_manager as reference_library_manager_module
from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.reference_library_manager import ReferenceLibraryManager, _html_to_snippet


class _FakeConfig:
    """Minimal stand-in for ConfigManager, just enough for `.get(key, default)`."""

    def __init__(self, overrides: dict) -> None:
        self._overrides = overrides

    def get(self, key: str, default=None):
        return self._overrides.get(key, default)


class _TextItem(ZimWriterItem):
    def __init__(self, path: str, title: str, content: str, mimetype: str = "text/html"):
        super().__init__()
        self._path = path
        self._title = title
        self._content = content
        self._mimetype = mimetype

    def get_path(self) -> str:
        return self._path

    def get_title(self) -> str:
        return self._title

    def get_mimetype(self) -> str:
        return self._mimetype

    def get_contentprovider(self):
        return StringProvider(self._content)

    def get_hints(self) -> dict:
        return {Hint.FRONT_ARTICLE: 1}


def _build_zim(
    path: Path,
    *,
    title: str = "Test Pack",
    description: str = "A tiny test pack",
    language: str = "eng",
    pages: dict | None = None,
) -> Path:
    pages = pages or {
        "home": ("Home Page", "<html><body><h1>Home</h1><p>Hello world reference test</p></body></html>")
    }
    with Creator(str(path)).config_indexing(True, language) as creator:
        for entry_path, (entry_title, content) in pages.items():
            creator.add_item(_TextItem(entry_path, entry_title, content))
        creator.set_mainpath(next(iter(pages)))
        creator.add_metadata("Title", title)
        creator.add_metadata("Description", description)
        creator.add_metadata("Language", language)
    return path


@pytest.fixture
def isolated_root(tmp_path, monkeypatch):
    root = tmp_path / "reference_library"
    monkeypatch.setattr(reference_library_manager_module, "_DEFAULT_ROOT", root)
    return root


@pytest.fixture(autouse=True)
def _no_quiet_period(monkeypatch):
    """
    Most tests build a .zim fixture and expect it discoverable
    immediately; only the dedicated quiet-period test below needs the
    real still-copying guard, so it re-overrides this per-test.
    """
    monkeypatch.setattr(reference_library_manager_module, "_MIN_QUIET_SECONDS", 0)


def _make_manager() -> ReferenceLibraryManager:
    context = AppContext(config=ConfigManager(), events=EventBus())
    return ReferenceLibraryManager(context)


def test_empty_library_has_no_packs(isolated_root):
    manager = _make_manager()
    assert manager.list_packs() == []


def test_root_folder_is_created_on_construction(isolated_root):
    assert not isolated_root.exists()
    _make_manager()
    assert isolated_root.exists()


def test_discovers_a_valid_pack(isolated_root):
    isolated_root.mkdir(parents=True)
    _build_zim(isolated_root / "demo.zim", title="Demo Pack", description="A demo.", language="eng")

    manager = _make_manager()
    packs = manager.list_packs()

    assert len(packs) == 1
    assert packs[0].pack_id == "demo"
    assert packs[0].title == "Demo Pack"
    assert packs[0].description == "A demo."
    assert packs[0].language == "eng"
    assert packs[0].article_count == 1


def test_corrupt_zim_file_is_skipped_not_crashed(isolated_root):
    isolated_root.mkdir(parents=True)
    (isolated_root / "broken.zim").write_bytes(b"not a real zim file")

    manager = _make_manager()

    assert manager.list_packs() == []


def test_recently_written_zim_is_skipped_until_quiet(isolated_root, monkeypatch):
    # A pack still mid-copy keeps its mtime moving; opening it via
    # libzim while it's still being written is what caused the hang
    # this guard exists to prevent (see reference_library_manager's
    # module docstring).
    monkeypatch.setattr(reference_library_manager_module, "_MIN_QUIET_SECONDS", 60)
    isolated_root.mkdir(parents=True)
    path = isolated_root / "demo.zim"
    _build_zim(path, title="Demo Pack")

    manager = _make_manager()
    assert manager.list_packs() == []

    old = time.time() - 120
    os.utime(path, (old, old))
    packs = manager.list_packs()
    assert len(packs) == 1
    assert packs[0].title == "Demo Pack"


def test_broken_zim_recovers_once_replaced(isolated_root):
    # A pack that failed to open (e.g. caught mid-copy before this guard
    # existed, or genuinely corrupt) shouldn't be stuck failed forever —
    # once the file on disk actually changes, it should be retried.
    isolated_root.mkdir(parents=True)
    path = isolated_root / "pack.zim"
    path.write_bytes(b"not a real zim file")

    manager = _make_manager()
    assert manager.list_packs() == []

    _build_zim(path, title="Recovered Pack")
    packs = manager.list_packs()
    assert len(packs) == 1
    assert packs[0].title == "Recovered Pack"


def test_valid_and_corrupt_packs_coexist(isolated_root):
    isolated_root.mkdir(parents=True)
    _build_zim(isolated_root / "demo.zim")
    (isolated_root / "broken.zim").write_bytes(b"garbage")

    manager = _make_manager()
    packs = manager.list_packs()

    assert [p.pack_id for p in packs] == ["demo"]


def test_get_main_page_resolves_through_the_synthetic_redirect(isolated_root):
    isolated_root.mkdir(parents=True)
    _build_zim(isolated_root / "demo.zim")

    manager = _make_manager()
    main_path = manager.get_main_page("demo")

    # archive.main_entry.path is a synthetic "mainPage" alias that
    # isn't itself fetchable — get_main_page must resolve through it
    # to the real underlying entry path.
    assert main_path == "home"


def test_get_main_page_returns_none_for_unknown_pack(isolated_root):
    isolated_root.mkdir(parents=True)
    manager = _make_manager()
    assert manager.get_main_page("does_not_exist") is None


def test_get_entry_content_returns_bytes_and_mimetype(isolated_root):
    isolated_root.mkdir(parents=True)
    _build_zim(isolated_root / "demo.zim")

    manager = _make_manager()
    result = manager.get_entry_content("demo", "home")

    assert result is not None
    content, mimetype = result
    assert b"Hello world reference test" in content
    assert mimetype == "text/html"


def test_get_entry_content_returns_none_for_unknown_entry(isolated_root):
    isolated_root.mkdir(parents=True)
    _build_zim(isolated_root / "demo.zim")

    manager = _make_manager()
    assert manager.get_entry_content("demo", "does/not/exist") is None


def test_search_finds_a_matching_page(isolated_root):
    isolated_root.mkdir(parents=True)
    _build_zim(
        isolated_root / "demo.zim",
        pages={
            "home": ("Home Page", "<html><body>Nothing relevant here.</body></html>"),
            "other": ("Other Page", "<html><body>A page about bananas and tropical fruit.</body></html>"),
        },
    )

    manager = _make_manager()
    hits = manager.search("demo", "bananas")

    assert len(hits) == 1
    assert hits[0].path == "other"
    assert hits[0].title == "Other Page"


def test_search_with_blank_query_returns_nothing(isolated_root):
    isolated_root.mkdir(parents=True)
    _build_zim(isolated_root / "demo.zim")

    manager = _make_manager()
    assert manager.search("demo", "   ") == []


def test_search_on_unknown_pack_returns_nothing(isolated_root):
    isolated_root.mkdir(parents=True)
    manager = _make_manager()
    assert manager.search("does_not_exist", "anything") == []


def test_install_pack_from_file_copies_and_lists_immediately(isolated_root, tmp_path):
    source = tmp_path / "external_drive" / "incoming.zim"
    source.parent.mkdir(parents=True)
    _build_zim(source, title="Incoming Pack")

    manager = _make_manager()
    result = manager.install_pack_from_file(source)

    assert result.passed
    assert result.pack_id == "incoming"
    assert result.title == "Incoming Pack"
    assert (isolated_root / "incoming.zim").exists()

    # Should be listed right away, not stuck behind the mid-copy
    # quiet-period guard — we just wrote this file ourselves.
    packs = manager.list_packs()
    assert len(packs) == 1
    assert packs[0].title == "Incoming Pack"


def test_install_pack_from_file_rejects_missing_file(isolated_root, tmp_path):
    manager = _make_manager()
    result = manager.install_pack_from_file(tmp_path / "does_not_exist.zim")

    assert not result.passed
    assert "not a file" in result.errors[0].lower()


def test_install_pack_from_file_rejects_non_zim_extension(isolated_root, tmp_path):
    source = tmp_path / "notes.txt"
    source.write_text("hello")

    manager = _make_manager()
    result = manager.install_pack_from_file(source)

    assert not result.passed
    assert ".zim" in result.errors[0]


def test_install_pack_from_file_rejects_invalid_zim_content(isolated_root, tmp_path):
    source = tmp_path / "fake.zim"
    source.write_bytes(b"not a real zim file")

    manager = _make_manager()
    result = manager.install_pack_from_file(source)

    assert not result.passed
    assert not (isolated_root / "fake.zim").exists()


def test_install_pack_from_file_rejects_duplicate_pack(isolated_root, tmp_path):
    isolated_root.mkdir(parents=True)
    _build_zim(isolated_root / "demo.zim", title="Existing Pack")

    source = tmp_path / "demo.zim"
    _build_zim(source, title="Different Content, Same Filename")

    manager = _make_manager()
    result = manager.install_pack_from_file(source)

    assert not result.passed
    assert "already installed" in result.errors[0]


def test_root_path_config_override_is_used(tmp_path):
    custom_root = tmp_path / "external_ssd" / "reference_library"
    custom_root.mkdir(parents=True)
    _build_zim(custom_root / "demo.zim")

    context = AppContext(
        config=_FakeConfig({"reference_library.root_path": str(custom_root)}),
        events=EventBus(),
    )
    manager = ReferenceLibraryManager(context)

    assert [p.pack_id for p in manager.list_packs()] == ["demo"]


# ----------------------------------------------------------------------
# _html_to_snippet (pure function, no ZIM involved)
# ----------------------------------------------------------------------

def test_html_to_snippet_strips_tags_and_collapses_whitespace():
    html = b"<html><body><h1>Title</h1>\n\n<p>Some   text  here.</p></body></html>"
    assert _html_to_snippet(html) == "Title Some text here."


def test_html_to_snippet_skips_script_and_style_content():
    html = b"<html><head><style>.x{color:red}</style></head><body><script>alert('hi')</script><p>Real content.</p></body></html>"
    assert _html_to_snippet(html) == "Real content."


def test_html_to_snippet_truncates_long_text():
    long_text = "word " * 200
    html = f"<p>{long_text}</p>".encode("utf-8")
    snippet = _html_to_snippet(html, max_chars=50)
    assert len(snippet) == 51  # 50 chars + the "…" marker
    assert snippet.endswith("…")


def test_html_to_snippet_handles_malformed_html_gracefully():
    assert _html_to_snippet(b"<p>unclosed tag") == "unclosed tag"


# ----------------------------------------------------------------------
# search_all_packs
# ----------------------------------------------------------------------

def test_search_all_packs_returns_snippet_from_matching_pack(isolated_root):
    isolated_root.mkdir(parents=True)
    _build_zim(
        isolated_root / "demo.zim",
        title="Demo Pack",
        pages={
            "home": ("Home Page", "<html><body>Nothing relevant here.</body></html>"),
            "hypothermia": ("Hypothermia", "<html><body>Symptoms include shivering and confusion.</body></html>"),
        },
    )

    manager = _make_manager()
    snippets = manager.search_all_packs("hypothermia")

    assert len(snippets) == 1
    assert snippets[0].pack_id == "demo"
    assert snippets[0].pack_title == "Demo Pack"
    assert snippets[0].article_title == "Hypothermia"
    assert "shivering" in snippets[0].snippet


def test_search_all_packs_fans_out_across_multiple_packs(isolated_root):
    isolated_root.mkdir(parents=True)
    _build_zim(
        isolated_root / "medical.zim",
        title="Medical Pack",
        pages={"hypothermia": ("Hypothermia", "<html><body>Cold exposure symptoms.</body></html>")},
    )
    _build_zim(
        isolated_root / "survival.zim",
        title="Survival Pack",
        pages={"hypothermia_treatment": ("Treating Hypothermia", "<html><body>Warm the person slowly.</body></html>")},
    )

    manager = _make_manager()
    snippets = manager.search_all_packs("hypothermia", limit=10)

    pack_ids = {s.pack_id for s in snippets}
    assert pack_ids == {"medical", "survival"}


def test_search_all_packs_takes_only_one_hit_per_pack(isolated_root):
    # Regression test for the real crowding bug this method's docstring
    # describes: a single pack must never supply more than one hit,
    # even if it has several matches, so it can't crowd out a later
    # pack's more relevant single hit.
    isolated_root.mkdir(parents=True)
    _build_zim(
        isolated_root / "demo.zim",
        pages={
            "a": ("Article A", "<html><body>banana one</body></html>"),
            "b": ("Article B", "<html><body>banana two</body></html>"),
            "c": ("Article C", "<html><body>banana three</body></html>"),
        },
    )

    manager = _make_manager()
    snippets = manager.search_all_packs("banana", limit=10)
    assert len(snippets) == 1


def test_search_all_packs_respects_total_limit_across_packs(isolated_root):
    isolated_root.mkdir(parents=True)
    for name in ("pack_a", "pack_b", "pack_c"):
        _build_zim(
            isolated_root / f"{name}.zim",
            title=name,
            pages={"home": ("Home", "<html><body>banana content</body></html>")},
        )

    manager = _make_manager()
    snippets = manager.search_all_packs("banana", limit=2)
    assert len(snippets) == 2


def test_search_all_packs_blank_query_returns_nothing(isolated_root):
    isolated_root.mkdir(parents=True)
    _build_zim(isolated_root / "demo.zim")
    manager = _make_manager()
    assert manager.search_all_packs("   ") == []


def test_search_all_packs_no_packs_installed_returns_nothing(isolated_root):
    manager = _make_manager()
    assert manager.search_all_packs("anything") == []
