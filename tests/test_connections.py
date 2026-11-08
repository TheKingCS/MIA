"""
tests.test_connections
========================

The magic is in the connections (core/connections.py, Zac 2026-11-08): a remark that ties into something started
weeks ago is noticed, held, raised once in a later conversation if it fits, then let go. These check the two ways a
tie is found (the link graph, shared words), the guards (a week old at least, never the thing named outright, never a
private turn), the store's life (held back, mentioned, expired, not raised twice, sealed), and the two loops.
"""

from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from core import connections as cx
from core import links
from core.at_rest import is_sealed
from core.connections import ConnectionBook

NOW = datetime(2026, 11, 8, 18, 0, 0)
WEEKS_AGO = (NOW - timedelta(days=21)).isoformat(timespec="seconds")
DAYS_AGO = (NOW - timedelta(days=3)).isoformat(timespec="seconds")


def _context(projects=(), materials=(), ideas=()):
    """A context with just the stores a connection reads."""
    return SimpleNamespace(
        projects=SimpleNamespace(all_projects=lambda: list(projects)),
        materials=SimpleNamespace(all_materials=lambda: list(materials)),
        life_notes=SimpleNamespace(of_kind=lambda kind, open_only=True: [n for n in ideas if n["kind"] == kind]),
    )


def _project(name, created=WEEKS_AGO, status="Planning", description="", pid="p1"):
    """A project record with the fields a connection reads (three weeks old unless told otherwise)."""
    return SimpleNamespace(project_id=pid, name=name, status=status, description=description, created_at=created)


def test_words_drop_common_words_and_fold_plurals():
    assert cx._words("I picked up some chicken boards today") == {"picked", "chicken", "board"}


def test_a_shared_word_ties_a_remark_to_an_idea_set_aside():
    idea = {"id": "n1", "kind": "idea", "what": "build a chicken tractor", "why": "", "at": WEEKS_AGO}
    found = cx.find(_context(ideas=[idea]), "grabbed chicken feed on the way home", NOW.date())
    assert [f["ref"] for f in found] == ["note:n1"] and found[0]["via"] == "words" and "chicken" in found[0]["shared"]


def test_the_link_graph_ties_a_named_thing_to_its_project(monkeypatch):
    cedar = SimpleNamespace(material_id="m1", name="Cedar")
    ctx = _context(projects=[_project("Bird feeder")], materials=[cedar])
    monkeypatch.setattr(links, "links_for", lambda context, ref: [
        links.Link(source="material:m1", relation="PART_OF", target="project:p1")] if ref == "material:m1" else [])
    found = cx.find(ctx, "Got a stack of cedar from the neighbour", NOW.date())
    assert found[0]["ref"] == "project:p1" and found[0]["via"] == "link" and found[0]["through"] == "Cedar"


def test_something_too_new_or_named_outright_is_not_a_connection():
    fresh = _context(projects=[_project("Chicken coop", created=DAYS_AGO, description="chicken coop for the hens")])
    assert cx.find(fresh, "the chicken feed is in", NOW.date()) == []  # three days old: still top of mind
    old = _context(projects=[_project("Chicken coop", description="chicken coop for the hens")])
    assert cx.find(old, "how's the chicken coop going", NOW.date()) == []  # named: it's the topic
    assert cx.find(old, "the chicken feed is in", NOW.date())  # mentioned in passing: a connection


def test_finished_things_are_never_brought_back():
    done = _context(projects=[_project("Chicken coop", status="Done", description="chicken coop")])
    assert cx.find(done, "the chicken feed is in", NOW.date()) == []


@pytest.fixture
def book(tmp_path):
    """An empty connection book in a temporary folder."""
    return ConnectionBook(data_dir=tmp_path)


def _found(name="Chicken coop", ref="project:p1"):
    """What `find` returns for one three-week-old project tied in by a shared word."""
    return [{"ref": ref, "kind": "project", "name": name, "status": "Planning",
             "since": (NOW - timedelta(days=21)).date(), "via": "words", "through": "", "through_kind": "",
             "shared": ["chicken"]}]


def test_a_connection_waits_then_comes_up_framed_to_fit_naturally(book):
    book.consider(_found(), "the chicken feed is in", NOW)
    assert book.context_block(NOW) == ""  # held back: not in the same conversation
    later = book.context_block(NOW + timedelta(hours=3))
    assert "Chicken coop" in later and "only if it fits" in later and "3 weeks" in later


def test_mentioning_it_settles_it_and_it_isnt_raised_again(book):
    book.consider(_found(), "the chicken feed is in", NOW)
    book.settle("By the way, how's the chicken coop coming along?", NOW + timedelta(hours=4))
    assert book.open_ones() == [] and book.items[0]["state"] == "mentioned"
    assert book.consider(_found(), "more chicken feed", NOW + timedelta(days=5)) is None  # inside the cooldown


def test_an_unmentioned_connection_expires(book):
    book.consider(_found(), "the chicken feed is in", NOW)
    book.settle("Sure, here's the weather.", NOW + timedelta(days=15))
    assert book.items[0]["state"] == "expired"


def test_connections_are_sealed_at_rest(tmp_path):
    ConnectionBook(data_dir=tmp_path).consider(_found(), "the chicken feed is in", NOW)
    on_disk = (tmp_path / "connections.json").read_text(encoding="utf-8")
    assert is_sealed(on_disk) and "chicken feed" not in on_disk
    assert ConnectionBook(data_dir=tmp_path).items[0]["said"] == "the chicken feed is in"


def test_a_private_conversation_is_never_noticed(book):
    ctx = _context(projects=[_project("Chicken coop", description="chicken coop")])
    ctx.connections = book
    private = SimpleNamespace(off_record=True, journal=False, private_turn=False, mode="companion", messages=[])
    assert cx.notice(ctx, private, "the chicken feed is in", NOW) is None and book.items == []
    open_talk = SimpleNamespace(off_record=False, journal=False, private_turn=False, mode="companion", messages=[])
    assert cx.notice(ctx, open_talk, "the chicken feed is in", NOW) is not None


def test_no_book_means_no_connection_line():
    assert cx.connections_for(SimpleNamespace()) == ""


def test_the_loops_read_landed_share_and_unlinked_kind_pairs(book, monkeypatch):
    from core import loops

    monkeypatch.setattr(loops, "_now", lambda: NOW + timedelta(days=20))
    unlinked = _found()
    unlinked[0].update(through="Cedar", through_kind="material")
    book.consider(unlinked, "got cedar for the chicken coop", NOW)
    book.consider(_found("Bird feeder", "project:p2"), "chicken feed", NOW)
    book.settle("How's the chicken coop?", NOW + timedelta(hours=4))  # one mentioned
    book.settle("", NOW + timedelta(days=15))  # the other expires
    ctx = SimpleNamespace(connections=book)
    landed = loops._connections_landed(ctx)
    assert landed.value == 0.5 and landed.n == 2
    gaps = loops._connections_unlinked(ctx)
    assert gaps.value == 1 and "material↔project" in gaps.detail and "Cedar" not in gaps.detail
