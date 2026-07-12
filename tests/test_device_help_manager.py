"""
tests.test_device_help_manager
================================

Unit tests for core.device_help_manager: the pure chunking/scoring
logic (no filesystem), retrieval ranking (with pre-set chunks,
bypassing the filesystem), and one test of the actual doc-loading path
against a tmp_path fixture directory (monkeypatching `_DOCS_DIR`, same
approach as test_voice_manager.py monkeypatching `_sd`).
"""

from __future__ import annotations

from pathlib import Path

from core.app_context import AppContext
from core.device_help_manager import DeviceHelpManager, HelpChunk, score_chunk, split_into_chunks


class _FakeConfig:
    def get(self, key: str, default=None):
        return default


class _FakeModule:
    def __init__(self, display_name: str, description: str) -> None:
        self.display_name = display_name
        self.description = description


def _make_manager() -> DeviceHelpManager:
    context = AppContext(config=_FakeConfig(), events=None)
    return DeviceHelpManager(context)


# ----------------------------------------------------------------------
# split_into_chunks
# ----------------------------------------------------------------------

def test_split_into_chunks_splits_on_h2_headings():
    text = "Intro text\n\n## First Section\nbody one\n\n## Second Section\nbody two\n"
    chunks = split_into_chunks(text, source="docs/example.md")
    assert [c.heading for c in chunks] == ["Introduction", "First Section", "Second Section"]
    assert "body one" in chunks[1].text
    assert "body two" in chunks[2].text


def test_split_into_chunks_splits_on_h3_headings_too():
    text = "## Section\n### Subsection\nbody\n"
    chunks = split_into_chunks(text, source="docs/example.md")
    assert [c.heading for c in chunks] == ["Section", "Subsection"]


def test_split_into_chunks_drops_empty_leading_chunk():
    text = "## Only Section\nbody\n"
    chunks = split_into_chunks(text, source="docs/example.md")
    assert len(chunks) == 1
    assert chunks[0].heading == "Only Section"


# ----------------------------------------------------------------------
# score_chunk
# ----------------------------------------------------------------------

def test_score_chunk_scores_heading_match_higher_than_body_match():
    heading_chunk = HelpChunk(source="s", heading="Kiosk Mode", text="## Kiosk Mode\nsomething else entirely")
    body_chunk = HelpChunk(source="s", heading="Other", text="## Other\nthis mentions kiosk somewhere")
    words = {"kiosk"}
    assert score_chunk(words, heading_chunk) > score_chunk(words, body_chunk)


def test_score_chunk_zero_when_no_words_match():
    chunk = HelpChunk(source="s", heading="Something", text="## Something\nunrelated content")
    assert score_chunk({"zzz"}, chunk) == 0


# ----------------------------------------------------------------------
# retrieve (chunks pre-set, no filesystem)
# ----------------------------------------------------------------------

def test_retrieve_ranks_by_score_and_respects_limit():
    manager = _make_manager()
    manager._doc_chunks = [
        HelpChunk(source="a", heading="Kiosk Mode", text="## Kiosk Mode\nfullscreen behavior"),
        HelpChunk(source="b", heading="Unrelated", text="## Unrelated\nsomething about kiosk in passing"),
        HelpChunk(source="c", heading="Totally Different", text="## Totally Different\nno overlap here"),
    ]
    results = manager.retrieve("kiosk mode", limit=2)
    assert len(results) == 2
    assert results[0].heading == "Kiosk Mode"


def test_retrieve_empty_query_returns_nothing():
    manager = _make_manager()
    manager._doc_chunks = [HelpChunk(source="a", heading="X", text="## X\nkiosk")]
    assert manager.retrieve("   ") == []


def test_retrieve_includes_module_metadata():
    manager = _make_manager()
    manager._doc_chunks = []
    manager.register_module_lister(lambda: [_FakeModule("Notes", "Dated, searchable, taggable journal entries.")])
    results = manager.retrieve("notes journal")
    assert len(results) == 1
    assert results[0].source == "Module: Notes"


def test_retrieve_boosts_module_named_in_query_over_generic_docs_mentioning_module():
    """
    Regression test: docs/ADDING_MODULES.md-style chunks (headings full
    of the generic word "module") must not outrank a module's own
    description when the module is actually named in the query — see
    core.device_help_manager.retrieve's _MODULE_NAME_MATCH_BONUS
    comment for the real bug this caught.
    """
    manager = _make_manager()
    manager._doc_chunks = [
        HelpChunk(source="docs/ADDING_MODULES.md", heading="1. Create a module folder", text="## 1. Create a module folder\nmodule module module"),
        HelpChunk(source="docs/ADDING_MODULES.md", heading="2. Write module.py", text="## 2. Write module.py\nmodule module module"),
    ]
    manager.register_module_lister(lambda: [_FakeModule("Notes", "Dated, searchable, taggable journal entries.")])

    results = manager.retrieve("what does the notes module do", limit=5)
    assert results[0].source == "Module: Notes"


def test_retrieve_module_lister_error_does_not_crash():
    manager = _make_manager()
    manager._doc_chunks = []

    def _broken_lister():
        raise RuntimeError("boom")

    manager.register_module_lister(_broken_lister)
    assert manager.retrieve("anything") == []


# ----------------------------------------------------------------------
# build_grounded_prompt
# ----------------------------------------------------------------------

def test_build_grounded_prompt_includes_retrieved_material():
    manager = _make_manager()
    manager._doc_chunks = [HelpChunk(source="docs/HARDWARE.md", heading="Storage", text="## Storage\nUSB SSD setup")]
    prompt = manager.build_grounded_prompt("storage")
    assert "docs/HARDWARE.md" in prompt
    assert "USB SSD setup" in prompt
    assert "Question: storage" in prompt


def test_build_grounded_prompt_falls_back_when_nothing_matches():
    manager = _make_manager()
    manager._doc_chunks = [HelpChunk(source="a", heading="X", text="## X\nunrelated")]
    prompt = manager.build_grounded_prompt("zzz_no_match_zzz")
    assert "No reference material matched" in prompt


# ----------------------------------------------------------------------
# _ensure_docs_loaded (real filesystem, via tmp_path fixture)
# ----------------------------------------------------------------------

def test_ensure_docs_loaded_reads_markdown_files_from_docs_dir(tmp_path, monkeypatch):
    import core.device_help_manager as device_help_module

    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "example.md").write_text("## Test Heading\nsome content about widgets\n", encoding="utf-8")

    monkeypatch.setattr(device_help_module, "_DOCS_DIR", docs_dir)

    manager = _make_manager()
    results = manager.retrieve("widgets")
    assert len(results) == 1
    assert results[0].source == "docs/example.md"
    assert results[0].heading == "Test Heading"
