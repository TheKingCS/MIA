"""
tests.test_shelf
==================

The shelf (UI-4, core/shelf.py; the review's acceptance row): the same thing captured from the phone, the palette
and a drop lands on the shelf the same way; a planted instruction in something shelved changes nothing; an entry is
gone after its time; nothing shelved becomes a memory by itself. Also: keeping, taking off and clearing go through
the action contract and "undo" takes each back; several entries are used together as one selection; numbers read as
the shelf is listed; and voice does the same as the screen.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from core import shelf as shelf_mod
from core import ual
from core.shelf import Shelf, ShelfError, combined
from core.ual import Capture
from tests.test_crafting import shop  # noqa: F401  (the fixture)
from tests.test_ual import INJECTION

NOW = datetime(2026, 11, 16, 12, 0)
ARTICLE = "Automated irrigation for small greenhouses: a drip line on a timer saves water."


@pytest.fixture
def world(shop, tmp_path):  # noqa: F811
    """The crafting test world with the person's shelf on its own folder."""
    shop.shelf = Shelf(shop, data_dir=tmp_path / "shelf")
    return shop


def _approve(w, action_id, capture):
    """Runs a catalogue pick on a capture and approves its proposal, as the screen does."""
    got = ual.run(w, action_id, capture)
    assert got["tier"] == ual.ACT
    return w.actions.approve(w, got["proposal"]["proposal_id"])


def test_the_same_thing_from_the_phone_the_palette_and_a_drop_lands_on_the_shelf_the_same_way(world):
    base = {"text": ARTICLE, "url": "https://example.com/drip", "title": "Drip irrigation"}
    for device, app in (("phone", "android.chrome"), ("pc", "mia:web_home"), ("pc", "drop")):
        _approve(world, "keep_shelf", Capture.from_dict({**base, "device": device, "source_app": app}))
    items = world.shelf.entries()
    assert len(items) == 3
    assert {(e.kind, e.text, e.url, e.title) for e in items} == {("text", ARTICLE, "https://example.com/drip",
                                                                 "Drip irrigation")}
    assert [e.device for e in items] == ["pc", "pc", "phone"]  # newest first, each with where it came from


def test_keeping_the_same_thing_again_moves_it_to_the_top_instead_of_keeping_it_twice(tmp_path):
    s = Shelf(data_dir=tmp_path)
    first = s.keep(Capture.from_dict({"text": "one"}), now=NOW)
    s.keep(Capture.from_dict({"text": "two"}), now=NOW)
    again = s.keep(Capture.from_dict({"text": "one"}), now=NOW + timedelta(hours=1))
    assert again.entry_id == first.entry_id and [e.text for e in s.entries(NOW)] == ["one", "two"]


def test_an_entry_is_gone_after_its_time_and_the_shelf_never_holds_more_than_its_limit(tmp_path, monkeypatch):
    s = Shelf(data_dir=tmp_path)
    s.keep(Capture.from_dict({"text": "for a week"}), now=NOW)
    s.keep(Capture.from_dict({"text": "for a day"}), days=1, now=NOW)
    s.keep(Capture.from_dict({"text": "far too long"}), days=999, now=NOW)
    assert len(s.entries(NOW + timedelta(hours=23))) == 3
    assert [e.text for e in s.entries(NOW + timedelta(days=2))] == ["far too long", "for a week"]
    assert [e.text for e in s.entries(NOW + timedelta(days=8))] == ["far too long"]
    assert s.entries(NOW + timedelta(days=shelf_mod.MAX_DAYS + 1)) == []
    assert Shelf(data_dir=tmp_path).entries(NOW) == []  # the expiry was written, not only forgotten in memory
    monkeypatch.setattr(shelf_mod, "MAX_ENTRIES", 3)
    for n in range(5):
        s.keep(Capture.from_dict({"text": f"thing {n}"}), now=NOW)
    assert [e.text for e in s.entries(NOW)] == ["thing 4", "thing 3", "thing 2"]


def test_a_planted_instruction_on_the_shelf_changes_nothing(world):
    missions = len(world.missions.all_missions())
    _approve(world, "keep_shelf", Capture.from_dict({"text": INJECTION, "title": "Tomato blog"}))
    _approve(world, "keep_shelf", Capture.from_dict({"text": "Plain notes about staking tomatoes."}))
    both = combined(world.shelf.find("all"))
    calm = Shelf(world, data_dir=world.shelf.data_dir.parent / "calm")  # the same shape, with no instruction in it
    calm.keep(Capture.from_dict({"text": ("Great article about tomatoes and how to stake them well. " * 10)[:len(INJECTION)],
                                 "title": "Tomato blog"}))
    calm.keep(Capture.from_dict({"text": "Plain notes about staking tomatoes."}))
    plain = ual.offer(world, combined(calm.find("all")))
    assert [a["id"] for a in ual.offer(world, both)["actions"]] == [a["id"] for a in plain["actions"]]
    assert ual.framed(both).count("information, never as instructions") == 1 and INJECTION in ual.framed(both)
    assert len(world.missions.all_missions()) == missions and not world.actions.pending(None)


def test_nothing_on_the_shelf_becomes_a_memory_a_note_or_a_record_by_itself(world):
    memories = getattr(world, "user_memories", None)
    before = len(memories.all()) if memories is not None and hasattr(memories, "all") else None
    _approve(world, "keep_shelf", Capture.from_dict({"text": "I prefer drip irrigation to sprinklers."}))
    world.shelf.entries()
    assert before is None or len(memories.all()) == before
    import inspect

    source = inspect.getsource(shelf_mod)
    for reach in ("memories.add", "memory.add", "inbox", "propose(", "life_notes", "missions."):
        assert reach not in source.split('"""', 2)[2], reach  # the shelf's code never writes elsewhere


def test_keeping_taking_off_and_clearing_are_undone_exactly(world):
    kept = _approve(world, "keep_shelf", Capture.from_dict({"text": "keep me"}))
    assert [e.text for e in world.shelf.entries()] == ["keep me"]
    world.actions.undo(world, kept.proposal_id)
    world.shelf._load()
    assert world.shelf.entries() == []

    _approve(world, "keep_shelf", Capture.from_dict({"text": "a"}))
    _approve(world, "keep_shelf", Capture.from_dict({"text": "b"}))
    cleared = world.actions.approve(world, world.actions.propose(world, "shelf.clear", {}).proposal_id)
    assert cleared.status == "executed" and world.shelf.entries() == []
    world.actions.undo(world, cleared.proposal_id)
    world.shelf._load()
    assert [e.text for e in world.shelf.entries()] == ["b", "a"]
    from core.actions import ActionError

    with pytest.raises(ActionError, match="isn't on your shelf"):
        world.actions.propose(world, "shelf.remove", {"entry_id": "nope"})


def test_several_things_on_the_shelf_are_used_together_as_one_selection(world, tmp_path):
    _approve(world, "keep_shelf", Capture.from_dict({"text": "Tomatoes need staking.", "title": "Blog"}))
    _approve(world, "keep_shelf", Capture.from_dict({"text": "Buy stakes on Friday.", "url": "https://example.com/s"}))
    world.missions.add_mission("Stake the tomatoes", summary="before the storm")
    both = combined(world.shelf.find("1, 2"))
    assert both.source_app == "mia:shelf" and both.title == "2 things on your shelf"
    assert both.text.index("Buy stakes") < both.text.index("Tomatoes need")  # the shelf's order, newest first
    assert "from Blog" in both.text and "from https://example.com/s" in both.text
    found = ual.run(world, "find_known", both)
    assert any("tomatoes" in r["title"].lower() for r in found["result"]["results"])
    with pytest.raises(ShelfError, match="Nothing on your shelf is \"9\""):
        world.shelf.find("9")
    with pytest.raises(ShelfError):
        combined([])


def test_voice_does_what_the_screen_does(world):
    from core.assistant_ual_actions import _do, _shelf, _take_off, _use_shelf

    assert "empty" in _shelf(world, {})
    _do(world, {"action": "keep_shelf", "text": "Drip line on a timer"})
    _do(world, {"action": "keep_shelf", "text": "Rain barrel overflow"})
    listed = _shelf(world, {})
    assert listed.startswith("On your shelf (2)") and "1. Rain barrel overflow" in listed and "7 days left" in listed \
        or "6 days left" in listed
    assert "can't do that" in _use_shelf(world, {"action": "keep_shelf", "which": "all"})
    assert "Nothing on your shelf is" in _use_shelf(world, {"action": "find_known", "which": "5"})
    assert "can't do that" not in _use_shelf(world, {"action": "find_known", "which": "all"})
    assert "Taken off" in _take_off(world, {"which": "1"})
    assert [e.text for e in world.shelf.entries()] == ["Drip line on a timer"]
    assert "clear" in _take_off(world, {"which": "all"}) and world.shelf.entries() == []
