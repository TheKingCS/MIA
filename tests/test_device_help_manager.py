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
from core.reference_library_manager import ReferenceSnippet


class _FakeConfig:
    def get(self, key: str, default=None):
        return default


class _FakeModule:
    def __init__(self, display_name: str, description: str) -> None:
        self.display_name = display_name
        self.description = description


class _FakeReferenceLibrary:
    def __init__(self, snippets=None, error: bool = False, snippets_by_query: dict = None) -> None:
        self._snippets = snippets or []
        self._snippets_by_query = snippets_by_query or {}
        self._error = error
        self.last_query = None
        self.last_limit = None
        self.all_queries: list[str] = []

    def search_all_packs(self, query, limit=3):
        self.last_query = query
        self.last_limit = limit
        self.all_queries.append(query)
        if self._error:
            raise RuntimeError("boom")
        if self._snippets_by_query:
            return self._snippets_by_query.get(query, [])
        return self._snippets


class _FakeLLM:
    def __init__(self, reply: str = "hypothermia frostbite cold exposure") -> None:
        self._reply = reply
        self.last_prompt = None

    def generate(self, prompt):
        self.last_prompt = prompt
        return self._reply


def _make_manager(llm=None) -> DeviceHelpManager:
    context = AppContext(config=_FakeConfig(), events=None)
    context.llm = llm
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


# ----------------------------------------------------------------------
# Reference Library integration (5.6)
# ----------------------------------------------------------------------

def test_reference_library_chunks_empty_when_not_registered():
    manager = _make_manager()
    assert manager._reference_library_chunks("hypothermia") == []


def test_reference_library_chunks_converts_snippets_to_help_chunks():
    manager = _make_manager()
    fake_library = _FakeReferenceLibrary(snippets=[
        ReferenceSnippet(pack_id="medicine", pack_title="WikiMed", article_title="Hypothermia", snippet="Cold exposure symptoms."),
    ])
    manager.register_reference_library(fake_library)

    chunks = manager._reference_library_chunks("hypothermia symptoms")
    assert len(chunks) == 1
    assert chunks[0].source == "Reference Library: WikiMed"
    assert chunks[0].heading == "Hypothermia"
    assert chunks[0].text == "Cold exposure symptoms."
    # Order isn't guaranteed (_query_words returns a set), just that both
    # meaningful words made it through.
    assert set(fake_library.last_query.split()) == {"hypothermia", "symptoms"}


def test_reference_library_chunks_strips_stopwords_before_searching():
    """
    Regression test: verified against the real medicine pack that
    passing the raw natural-language question instead of stripped
    keywords ranks the wrong article first ("Pulseless electrical
    activity" instead of "Hypothermia" for "What are the symptoms of
    hypothermia?") — filler words dilute libzim's own relevance
    ranking. _reference_library_chunks() must pass keywords, not the
    raw question.
    """
    manager = _make_manager()
    fake_library = _FakeReferenceLibrary(snippets=[])
    manager.register_reference_library(fake_library)

    manager._reference_library_chunks("What are the symptoms of hypothermia?")
    query_words = set(fake_library.last_query.split())
    assert query_words == {"hypothermia", "symptoms"}
    assert "what" not in query_words
    assert "are" not in query_words
    assert "the" not in query_words
    assert "of" not in query_words


def test_reference_library_chunks_error_does_not_crash():
    manager = _make_manager()
    manager.register_reference_library(_FakeReferenceLibrary(error=True))
    assert manager._reference_library_chunks("anything") == []


# ----------------------------------------------------------------------
# LLM query reformulation (2026-07-14 vocabulary-mismatch fix)
# ----------------------------------------------------------------------

def test_reformulate_query_returns_none_without_an_llm():
    manager = _make_manager(llm=None)
    assert manager._reformulate_query_for_search("my hands are freezing") is None


def test_reformulate_query_returns_none_when_llm_returns_empty():
    manager = _make_manager(llm=_FakeLLM(reply=""))
    assert manager._reformulate_query_for_search("my hands are freezing") is None


def test_reformulate_query_returns_the_llm_reply():
    manager = _make_manager(llm=_FakeLLM(reply="hypothermia frostbite symptoms"))
    assert manager._reformulate_query_for_search("my hands are freezing") == "hypothermia frostbite symptoms"


def test_reformulate_query_includes_the_original_question_in_the_prompt():
    fake_llm = _FakeLLM()
    manager = _make_manager(llm=fake_llm)
    manager._reformulate_query_for_search("my hands are freezing")
    assert "my hands are freezing" in fake_llm.last_prompt


def test_reformulate_query_truncates_a_rambling_non_compliant_reply():
    long_reply = " ".join(f"word{i}" for i in range(30))
    manager = _make_manager(llm=_FakeLLM(reply=long_reply))
    reformulated = manager._reformulate_query_for_search("anything")
    assert len(reformulated.split()) == 4  # _MAX_REFORMULATED_QUERY_WORDS


def test_reference_library_chunks_searches_with_reformulated_query_first():
    """
    Reproduces the exact 2026-07-14 finding: the original keywords find
    an unrelated article, but the reformulated query finds the real one
    — and its result must come first. Uses a single-word original query
    ("numb") so _query_words()'s set-based tokenization can't reorder
    it — a multi-word original query's word order isn't guaranteed.
    """
    manager = _make_manager(llm=_FakeLLM(reply="hypothermia frostbite"))
    fake_library = _FakeReferenceLibrary(snippets_by_query={
        "hypothermia frostbite": [
            ReferenceSnippet(pack_id="medicine", pack_title="WikiMed", article_title="Hypothermia", snippet="Cold exposure."),
        ],
        "numb": [
            ReferenceSnippet(pack_id="ifixit", pack_title="iFixit", article_title="iPod Touch Logic Board", snippet="Unrelated."),
        ],
    })
    manager.register_reference_library(fake_library)

    chunks = manager._reference_library_chunks("numb")
    assert [c.heading for c in chunks] == ["Hypothermia", "iPod Touch Logic Board"]
    assert fake_library.all_queries == ["hypothermia frostbite", "numb"]


def test_reference_library_chunks_dedupes_across_both_queries():
    manager = _make_manager(llm=_FakeLLM(reply="hypothermia"))
    same_hit = ReferenceSnippet(pack_id="medicine", pack_title="WikiMed", article_title="Hypothermia", snippet="Cold exposure.")
    fake_library = _FakeReferenceLibrary(snippets=[same_hit])  # returns the same hit regardless of query
    manager.register_reference_library(fake_library)

    chunks = manager._reference_library_chunks("hypothermia symptoms")
    assert len(chunks) == 1


def test_reference_library_chunks_falls_back_to_original_when_reformulation_unavailable():
    """Single-word query — _query_words()'s set-based tokenization can't reorder a one-word result."""
    manager = _make_manager(llm=None)
    fake_library = _FakeReferenceLibrary(snippets=[
        ReferenceSnippet(pack_id="medicine", pack_title="WikiMed", article_title="Hypothermia", snippet="Cold exposure."),
    ])
    manager.register_reference_library(fake_library)

    chunks = manager._reference_library_chunks("hypothermia")
    assert len(chunks) == 1
    assert fake_library.all_queries == ["hypothermia"]  # only one search, no reformulation call


def test_build_grounded_prompt_skips_reference_library_when_module_name_matches():
    """
    Regression test: verified against the real installed packs that
    NOT gating this is actively harmful — "what does the notes module
    do" already has the exact right answer via the module-name-match
    bonus, but every installed pack had some weak stemmed match on
    "module"/"note" (e.g. "Loudspeaker Modules Replacement"), and
    piling all of those in overloaded the LLM into answering "I don't
    know" despite the right answer being right there.
    """
    manager = _make_manager()
    manager._doc_chunks = []
    manager.register_module_lister(lambda: [_FakeModule("Notes", "Dated, searchable, taggable journal entries.")])
    fake_library = _FakeReferenceLibrary(snippets=[
        ReferenceSnippet(pack_id="ifixit", pack_title="iFixit", article_title="Unrelated Modules Replacement", snippet="irrelevant"),
    ])
    manager.register_reference_library(fake_library)

    prompt = manager.build_grounded_prompt("what does the notes module do")
    assert "Module: Notes" in prompt
    assert "Reference Library" not in prompt


def test_build_grounded_prompt_includes_only_top_chunk_when_confident_match():
    """
    Regression test: verified against the real live model that a
    confident module-name match plus several extra lower-scored docs
    chunks (even when the confident match still ranks #1) made the LLM
    answer "I don't know" despite its own reasoning quoting the correct
    text verbatim — a small model finds "maybe related" extra context
    actively distracting, not just unhelpful padding.
    """
    manager = _make_manager()
    manager._doc_chunks = [
        HelpChunk(source="docs/ADDING_MODULES.md", heading="1. Create a module folder", text="## 1. Create a module folder\nmodule module module"),
        HelpChunk(source="docs/ADDING_MODULES.md", heading="2. Write module.py", text="## 2. Write module.py\nmodule module module"),
    ]
    manager.register_module_lister(lambda: [_FakeModule("Notes", "Dated, searchable, taggable journal entries.")])

    prompt = manager.build_grounded_prompt("what does the notes module do", limit=5)
    assert "Module: Notes" in prompt
    assert "docs/ADDING_MODULES.md" not in prompt


def test_build_grounded_prompt_includes_reference_library_when_no_strong_doc_match():
    manager = _make_manager()
    manager._doc_chunks = [HelpChunk(source="a", heading="Unrelated", text="## Unrelated\nsomething else entirely")]
    manager.register_reference_library(_FakeReferenceLibrary(snippets=[
        ReferenceSnippet(pack_id="medicine", pack_title="WikiMed", article_title="Hypothermia", snippet="Cold exposure symptoms."),
    ]))

    prompt = manager.build_grounded_prompt("what are the symptoms of hypothermia")
    assert "Reference Library: WikiMed" in prompt


def test_build_grounded_prompt_includes_reference_library_snippets():
    manager = _make_manager()
    manager._doc_chunks = []
    manager.register_reference_library(_FakeReferenceLibrary(snippets=[
        ReferenceSnippet(pack_id="medicine", pack_title="WikiMed", article_title="Hypothermia", snippet="Cold exposure symptoms include shivering."),
    ]))

    prompt = manager.build_grounded_prompt("what are the symptoms of hypothermia")
    assert "Reference Library: WikiMed" in prompt
    assert "shivering" in prompt


def test_build_grounded_prompt_combines_docs_and_reference_library():
    manager = _make_manager()
    manager._doc_chunks = [HelpChunk(source="docs/HARDWARE.md", heading="Storage", text="## Storage\nUSB SSD setup")]
    manager.register_reference_library(_FakeReferenceLibrary(snippets=[
        ReferenceSnippet(pack_id="medicine", pack_title="WikiMed", article_title="Hypothermia", snippet="Cold exposure symptoms."),
    ]))

    prompt = manager.build_grounded_prompt("storage")
    assert "docs/HARDWARE.md" in prompt
    assert "Reference Library: WikiMed" in prompt


def test_build_grounded_prompt_falls_back_when_neither_source_matches():
    manager = _make_manager()
    manager._doc_chunks = []
    manager.register_reference_library(_FakeReferenceLibrary(snippets=[]))

    prompt = manager.build_grounded_prompt("zzz_no_match_zzz")
    assert "No reference material matched" in prompt
