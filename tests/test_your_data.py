"""
tests.test_your_data
======================

Your Data (core/your_data.py, docs/SECURITY.md step 8): every file in the person's folder listed with what it is,
how many records and whether it's sealed (DEC-0126), never the temporary or set-aside copies; records counted for
lists, objects of lists and JSON lines; her latest answers with the tools in words, newest first.
"""

from types import SimpleNamespace

from core import your_data
from core.atomic_write import atomic_write_text


def test_records_are_counted_for_lists_objects_of_lists_and_json_lines():
    """A list's length, an object's lists added up (or its keys), lines of .jsonl, None for what isn't JSON."""
    assert your_data.count_records("[1, 2, 3]", "a.json") == 3
    assert your_data.count_records('{"notes": [1, 2], "offers": [3]}', "b.json") == 3
    assert your_data.count_records('{"a": 1, "b": 2}', "c.json") == 2
    assert your_data.count_records('{"x": 1}\n\n{"y": 2}\n', "d.jsonl") == 2
    assert your_data.count_records("not json", "e.json") is None


def test_every_file_in_the_folder_shows_with_what_it_is_and_whether_it_s_sealed(tmp_path):
    """A sealed conversations file counts its records through the seal; a plain one shows plain; temporary and
    set-aside copies, and hidden files, are left out; an unknown file shows by its name made readable."""
    atomic_write_text(tmp_path / "conversations.json", "[1, 2]")
    (tmp_path / "boss_book.json").write_text('{"peaks": [1]}', encoding="utf-8")
    for junk in (".conversations.json.123.tmp", "conversations.json.unreadable-20261108", ".hidden.json"):
        (tmp_path / junk).write_text("x", encoding="utf-8")
    personal = SimpleNamespace(folder=lambda pid: tmp_path, household_stores=lambda hid: {})
    context = SimpleNamespace(personal_data=personal, households=None)
    shown = your_data.inventory(context, "p1")["mine"]
    assert [(f["file"], f["what"], f["records"], f["sealed"]) for f in shown] == [
        ("boss_book.json", "Boss book", 1, False), ("conversations.json", "Conversations with MIA", 2, True)]


def test_her_latest_answers_come_newest_first_with_the_tools_in_words():
    """From the traces: what was asked, the tools she used (underscores gone) and how many memories."""
    traces = SimpleNamespace(recent=lambda count: [
        {"at": "1", "asked": "first", "route": "model", "tools_called": [], "memories": 0},
        {"at": "2", "asked": "second", "route": "tools", "tools_called": ["get_calendar"], "memories": 2}])
    got = your_data.answers(SimpleNamespace(traces=traces))
    assert [a["asked"] for a in got] == ["second", "first"]
    assert got[0]["tools"] == ["get calendar"] and got[0]["memories"] == 2
    assert your_data.answers(SimpleNamespace()) == []
