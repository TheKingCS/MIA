"""DEC-0054 (T-0018): what someone says they'll do, decide, want to try and set aside, spotted in code, kept only on
their yes, and answered by the recall plan."""

from types import SimpleNamespace

import pytest

from core import life_notes
from core.life_notes import LifeNotes, noticed


@pytest.mark.parametrize("said, kind, what, extra", [
    ("I promised Sam I would fix his gate by Saturday.", "commitment", "fix his gate", {"who": "Sam", "by": "Saturday"}),
    ("I'll fix the fence for Mom by Sunday", "commitment", "fix the fence", {"who": "Mom", "by": "Sunday"}),
    ("We're going with the metal roof because it lasts longer", "decision", "the metal roof",
     {"why": "it lasts longer"}),
    ("I decided to sell the truck since it costs too much", "decision", "sell the truck", {"why": "it costs too much"}),
    ("I should try selling honey at the market", "idea", "selling honey at the market", {}),
    ("Maybe I could open an Etsy shop someday", "idea", "open an Etsy shop", {}),
    ("I'm giving up on the half marathon because my knee hurts", "dropped_goal", "the half marathon",
     {"why": "my knee hurts"}),
    ("I gave up on learning piano, no time", "dropped_goal", "learning piano", {}),
])
def test_what_her_code_spots(said, kind, what, extra):
    found = noticed(said)
    assert found["kind"] == kind and found["what"] == what
    assert all(found[k] == v for k, v in extra.items())


@pytest.mark.parametrize("said", ["Should I try selling honey?", "what did I promise?", "I'm done with the dishes",
                                  "I quit smoking", "I'm going with Sam to the game", "I should start dinner",
                                  "log lunch", ""])
def test_and_what_it_leaves_alone(said):
    assert noticed(said) is None


def _chat(**kw):
    return SimpleNamespace(conversation_id="c1", off_record=False, journal=False, private_turn=False, mode="companion",
                           pending_note=None, **kw)


def test_offered_once_and_kept_only_on_a_yes(tmp_path):
    context = SimpleNamespace(life_notes=LifeNotes(data_dir=tmp_path))
    chat = _chat()
    offer = life_notes.offer_after(context, chat, "I promised Sam I'd fix his gate by Saturday")
    assert offer == "(Want me to keep that as a promise to Sam? Say “keep it”.)"
    said = life_notes.answer_offer(context, chat, "keep it")
    assert said == "Kept: a promise to Sam: fix his gate (by Saturday). Ask “what did I promise?” any time."
    [note] = LifeNotes(data_dir=tmp_path).of_kind("commitment")  # on disk
    assert (note["who"], note["conversation_id"], note["status"]) == ("Sam", "c1", "open")
    assert life_notes.offer_after(context, chat, "I promised Sam I'd fix his gate by Saturday") is None  # kept already
    life_notes.offer_after(context, chat, "I should try selling honey")
    assert life_notes.answer_offer(context, chat, "what's on today?") is None  # anything else lets it go
    assert chat.pending_note is None and len(context.life_notes.notes) == 1
    assert [o["kept"] for o in context.life_notes.offers] == [True, False]
    assert "honey" not in str(context.life_notes.offers)  # the offers keep the kind only


def test_never_in_a_private_or_personal_conversation(tmp_path):
    context = SimpleNamespace(life_notes=LifeNotes(data_dir=tmp_path))
    for private in ({"journal": True}, {"off_record": True}, {"private_turn": True}):
        chat = _chat()
        chat.__dict__.update(private)
        assert life_notes.offer_after(context, chat, "I promised Sam I'd fix his gate") is None


def test_done_and_forgotten(tmp_path):
    store = LifeNotes(data_dir=tmp_path)
    note = store.add("idea", "sell honey")
    assert store.add("idea", "Sell honey") is note  # the same open note once
    store.mark_done(note["id"])
    assert store.of_kind("idea", open_only=True) == [] and store.get(note["id"])["status"] == "done"
    assert store.forget(note["id"]) and store.notes == []
    with pytest.raises(ValueError):
        store.add("wish", "a pony")


def test_the_recall_plan_answers_from_the_notes(tmp_path):
    from core.question_plans import PLAN_BY_NAME, Sheet

    store = LifeNotes(data_dir=tmp_path)
    store.add("commitment", "fix his gate", who="Sam", by="Saturday")
    store.add("dropped_goal", "the half marathon", why="my knee hurts")
    context = SimpleNamespace(life_notes=store)
    sheet = Sheet("recall", "")
    PLAN_BY_NAME["recall"].gather(context, sheet, "What did I promise someone?", None)
    facts = [f.text for f in sheet.facts if f.kind == "fact"]
    assert len(facts) == 1 and facts[0].startswith("a promise to Sam: fix his gate (by Saturday), noted ")
    sheet = Sheet("recall", "")
    PLAN_BY_NAME["recall"].gather(context, sheet, "What goals have I abandoned, and why?", None)
    assert any("because my knee hurts" in f.text for f in sheet.facts)
    sheet = Sheet("recall", "")
    PLAN_BY_NAME["recall"].gather(SimpleNamespace(life_notes=LifeNotes(data_dir=tmp_path / "x")), sheet,
                                  "What ideas haven't I tried?", None)
    assert [f.text for f in sheet.facts if f.kind == "missing"] == ["No ideas kept yet."]


def test_the_loop_counts_offers_turned_down(tmp_path):
    from core import loops

    store = LifeNotes(data_dir=tmp_path)
    for kept in (True, False, False, True):
        store.offered("idea" if not kept else "commitment", kept)
    reading = {l.id: l for l in loops.LOOPS}["notes.offers"].measure(SimpleNamespace(life_notes=store))
    assert (reading.value, reading.n, reading.detail) == (0.5, 4, "2 of 4 turned down (idea)")
