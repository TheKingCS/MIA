"""
tests.test_picture_of_you
===========================

The picture of him (core/picture_of_you.py, DEC-0290): his memories grouped with how each is known and where from,
his skills by level, what he's learning, how he likes answers; said in a few sentences for "what do you know about
me?", and the page wired in; his learning read from his own path book, never the device's.
"""

from pathlib import Path
from types import SimpleNamespace

from core import picture_of_you as py

ROOT = Path(__file__).resolve().parent.parent


def _memory(mid, text, category, how="said", source="conversation:c1", confirmed=""):
    return SimpleNamespace(memory_id=mid, text=text, category=category, how=how, source=source,
                           source_conversation_id=None, confirmed_at=confirmed, created_at="2026-11-01T09:00:00")


def test_memories_are_grouped_with_how_each_is_known():
    ctx = SimpleNamespace(user_memories=SimpleNamespace(all_memories=lambda: [
        _memory("a", "Building a coop", "Projects", confirmed="2026-11-02"),
        _memory("b", "Trains in the mornings", "Fitness", how="inferred", source="")]))
    groups = py._memories(ctx)
    assert [g["category"] for g in groups] == ["Fitness", "Projects"]
    fitness = groups[0]["items"][0]
    assert fitness["how"] == "my guess from what you said" and fitness["source"] == "before I kept sources"
    assert groups[1]["items"][0]["confirmed"] and groups[1]["items"][0]["source"] == "a conversation"


def test_say_gives_the_picture_and_where_to_fix_it(monkeypatch):
    monkeypatch.setattr(py, "picture", lambda context: {
        "memories": [{"category": "Projects", "items": [{}, {}]}], "count": 2,
        "skills": [{"name": "Woodworking", "level": 4, "xp": 1250}],
        "learning": [{"name": "Guitar", "stage": 2, "of": 5}],
        "answers": [{"name": "How long", "lean": "Short", "word": "Settled"}]})
    said = py.say(None)
    assert "I remember 2 things about you: projects (2)" in said and "Woodworking (level 4)" in said
    assert "Guitar (stage 2 of 5)" in said and "short how long" in said and "You page" in said


def test_an_empty_picture_says_so_and_a_broken_section_never_empties_it(monkeypatch):
    monkeypatch.setattr(py, "_skills", lambda context: 1 / 0)
    got = py.picture(SimpleNamespace(user_memories=SimpleNamespace(all_memories=lambda: [_memory("a", "x", "Work")])))
    assert got["count"] == 1 and got["skills"] == []
    monkeypatch.setattr(py, "picture", lambda context: {"memories": [], "count": 0, "skills": [], "learning": [],
                                                        "answers": []})
    assert "don't hold much" in py.say(None)


def test_the_page_is_wired_in():
    assert "/api/picture" in (ROOT / "server" / "app.py").read_text(encoding="utf-8")
    assert 'picture: () => read("/api/picture"' in (ROOT / "web" / "mia.js").read_text(encoding="utf-8")
    page = (ROOT / "web" / "you.js").read_text(encoding="utf-8")
    assert '"memory.fix"' in page and '"memory.forget"' in page
    assert 'href: "you.html"' in (ROOT / "web" / "about.js").read_text(encoding="utf-8")


def test_learning_comes_from_the_persons_own_path_book(tmp_path):
    from core import paths

    book = paths.PathBook(None, data_dir=tmp_path)
    paths._builtins()
    book.start(paths.PROGRAMS["woodworking"])
    got = py._learning(SimpleNamespace(paths=book))
    assert got == [{"id": "woodworking", "name": "Woodworking at the bench", "stage": 1, "of": 3}]
    assert py._learning(SimpleNamespace(paths=None)) == []  # no book of his: nothing, never the device's
