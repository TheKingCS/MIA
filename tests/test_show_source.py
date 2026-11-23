"""
tests.test_show_source
========================

"Show me where it says that" (core/show_source.py, brainstorm 3.2): the sources her library lookups named are kept for
the person, and asking to see one opens it on the Knowledge page; with nothing read, the words go on as usual.
"""

from pathlib import Path

from core import show_source as ss

ROOT = Path(__file__).resolve().parent.parent
RESULT = ('From USDA Complete Guide to Home Canning, "Snap and Italian beans"\nref: usda|guide1.pdf|41\nProcess in a '
          'pressure canner...\n\nFrom Wikipedia, "Home canning"\nref: wiki|A/Home_canning|0\nHome canning is...')


def test_the_sources_a_lookup_named_are_read_out():
    found = ss.sources_in(RESULT)
    assert [f["article"] for f in found] == ["Snap and Italian beans", "Home canning"]
    assert found[0]["ref"] == "usda|guide1.pdf|41" and found[0]["pack"] == "USDA Complete Guide to Home Canning"


def test_asking_opens_the_newest_source_with_its_page():
    ss.reset()
    ss.remember("p1", ss.sources_in(RESULT))
    said, page = ss.reply("p1", "show me where it says that")
    assert "Snap and Italian beans" in said and "page 42" in said
    assert page == "knowledge.html?ref=usda%7Cguide1.pdf%7C41"


def test_each_person_has_their_own_and_nothing_read_means_nothing_taken():
    ss.reset()
    ss.remember("p1", ss.sources_in(RESULT))
    assert ss.reply("p2", "show me the source") is None
    assert ss.reply("p1", "what's the weather") is None


def test_the_ways_he_might_ask():
    for words in ("show me where it says that", "open that article", "where does it say that?", "show me the source",
                  "pull up the guide", "where did you read that"):
        assert ss.wants_source(words), words
    for words in ("show me my budget", "open the garage", "where is my truck"):
        assert not ss.wants_source(words), words


def test_the_turn_and_the_knowledge_page_are_wired():
    turn = (ROOT / "core" / "assistant_turn.py").read_text(encoding="utf-8")
    assert "show_source.reply(" in turn
    loop = (ROOT / "core" / "tool_loop.py").read_text(encoding="utf-8")
    assert "show_source.remember(" in loop
    page = (ROOT / "web" / "knowledge.js").read_text(encoding="utf-8")
    assert 'get("ref")' in page
