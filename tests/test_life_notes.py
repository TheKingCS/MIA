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
    """An everyday conversation (not off the record, not the journal, not private), with any field overridden."""
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
    """A note is kept once, marked done, and forgotten; an unknown kind is refused."""
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


def test_what_she_was_told_about_someone(tmp_path):
    from core.question_plans import PLAN_BY_NAME, Sheet

    sam = SimpleNamespace(name="Sam Rivera", relationship="Brother", person_id="p1")
    looked = []
    registry = SimpleNamespace(_actions={"get_person": 1},
                               execute=lambda context, tool, arguments: looked.append(arguments) or "Sam Rivera, your brother.")
    memories = [SimpleNamespace(text="Sam is allergic to peanuts", category="Family"),
                SimpleNamespace(text="Samantha from work likes tea", category="Work")]
    notes = LifeNotes(data_dir=tmp_path)
    notes.add("commitment", "fix his gate", who="Sam", by="Saturday")
    context = SimpleNamespace(relationships=SimpleNamespace(all_people=lambda: [sam]), assistant_actions=registry,
                              user_memories=SimpleNamespace(all_memories=lambda: memories), life_notes=notes)
    for asked in ("What have I told you about Sam?", "What do you know about my brother?"):
        sheet = Sheet("person", "")
        PLAN_BY_NAME["person"].gather(context, sheet, asked, None)
        texts = [f.text for f in sheet.facts]
        assert texts[1:] == ["You told MIA: Sam is allergic to peanuts", "a promise to Sam: fix his gate (by Saturday)"]
    assert looked[-1] == {"name": "Sam Rivera"}
    sheet = Sheet("person", "")
    PLAN_BY_NAME["person"].gather(context, sheet, "What important information have I told you about this person?", None)
    assert [f.kind for f in sheet.facts] == ["missing"]  # who isn't said: she asks


def test_what_they_keep_running_into(tmp_path):
    from core.question_plans import PLAN_BY_NAME, Sheet

    memories = [SimpleNamespace(text="Mornings are hard after night shifts", category="Struggles & Patterns"),
                SimpleNamespace(text="Likes fishing", category="Fishing")]
    insights = [SimpleNamespace(source_type="patterns", title="Workouts slip on Mondays", message="3 of 4 skipped",
                                status="open"),
                SimpleNamespace(source_type="maintenance", title="Oil change", message="due", status="open")]
    context = SimpleNamespace(user_memories=SimpleNamespace(all_memories=lambda: memories),
                              insights=SimpleNamespace(all_insights=lambda: insights), life_notes=None)
    sheet = Sheet("patterns", "")
    PLAN_BY_NAME["patterns"].gather(context, sheet, "What have I repeatedly struggled with?", None)
    assert [f.text for f in sheet.facts] == ["You told MIA: Mornings are hard after night shifts",
                                             "Workouts slip on Mondays: 3 of 4 skipped"]


@pytest.mark.parametrize("by, due", [
    ("tomorrow", "2026-11-07"), ("tonight", "2026-11-06"), ("Saturday", "2026-11-07"), ("friday", "2026-11-13"),
    ("next Monday", "2026-11-09"), ("the weekend", "2026-11-07"), ("the 15th", "2026-11-15"), ("the 3rd", "2026-12-03"),
    ("next week", "2026-11-13"), ("whenever", None),
])
def test_the_day_a_promise_means(by, due):
    from datetime import date

    found = life_notes.due_date(by, date(2026, 11, 6))  # a Friday
    assert (found.isoformat() if found else None) == due


def test_a_promise_with_a_day_is_mentioned_the_day_before_and_on_it(tmp_path):
    from datetime import date, timedelta

    store = LifeNotes(data_dir=tmp_path)
    note = store.add("commitment", "fix his gate", who="Sam", by="tomorrow")
    store.add("commitment", "call the bank")  # no day: never mentioned
    context = SimpleNamespace(life_notes=store)
    today = date.today()
    [first] = life_notes.reminders(context, today)
    assert (first.topic, first.message) == ("promise_due", "Your promise to Sam: fix his gate, tomorrow.")
    assert life_notes.reminders(context, today) == []  # once
    [second] = life_notes.reminders(context, today + timedelta(days=1))
    assert second.title == "A promise for today"
    store.mark_done(note["id"])
    assert life_notes.reminders(context, today + timedelta(days=1)) == []
    assert LifeNotes(data_dir=tmp_path).get(note["id"])["reminded"] == ["tomorrow", "today"]


def test_kept_or_forgotten_by_voice(tmp_path, monkeypatch):
    from core import actions
    from core.actions import ActionCenter

    monkeypatch.setattr(actions, "_who", lambda context: "p1")
    store = LifeNotes(data_dir=tmp_path)
    store.add("commitment", "fix his gate", who="Sam", by="tomorrow")
    store.add("commitment", "call the bank")
    store.add("idea", "sell honey at the market")
    person = SimpleNamespace(life_notes=store, actions=ActionCenter(), config=None, undo=None, events=None)
    said = life_notes.reply(person, "I kept my promise to Sam")
    assert said.startswith("Done: a promise to Sam: fix his gate (by tomorrow). Nicely kept.")
    assert life_notes.reply(person, "forget the idea about honey").startswith("Forgotten: an idea: sell honey")
    assert life_notes.reply(person, "I kept my promise to Alex") == "I don't have a promise about Alex kept."
    assert [n["what"] for n in store.of_kind("commitment", open_only=True)] == ["call the bank"]
    assert life_notes.reply(person, "I kept my word") is None


def test_the_kept_screen(tmp_path):
    """Kept lists promises open first, each with who it's to and when."""
    store = LifeNotes(data_dir=tmp_path)
    old = store.add("commitment", "call the bank")
    store.mark_done(old["id"])
    store.add("commitment", "fix his gate", who="Sam", by="tomorrow")
    store.notes[-1]["at"] = "2099-01-01T00:00:00"
    data = life_notes.screen(SimpleNamespace(life_notes=store))
    promises = data["kinds"][0]
    assert promises["title"] == "Promises" and [n["status"] for n in promises["notes"]] == ["open", "done"]
    assert promises["notes"][0]["line"] == "a promise to Sam: fix his gate (by tomorrow)" and promises["notes"][0]["due"]


def test_what_they_said_about_it_before(tmp_path):
    from core.conversation_manager import Conversation, ConversationMessage
    from core.question_plans import PLAN_BY_NAME, Sheet

    said = lambda text, at: ConversationMessage(role="user", content=text, timestamp=at)  # noqa: E731
    talks = [Conversation("c1", title="The roof", messages=[said("The roof leaks over the porch again", "2026-10-02T09:00")]),
             Conversation("c2", title="Private", journal=True, messages=[said("the roof makes me anxious", "2026-10-03")]),
             Conversation("c3", title="Shopping", messages=[said("buy milk", "2026-10-04")])]
    notes = LifeNotes(data_dir=tmp_path)
    notes.add("decision", "a metal roof", why="it lasts")
    context = SimpleNamespace(conversations=SimpleNamespace(all_conversations=lambda: talks), user_memories=None,
                              life_notes=notes)
    sheet = Sheet("discussed", "")
    PLAN_BY_NAME["discussed"].gather(context, sheet, "What did we discuss about the roof last time?", None)
    assert [f.text for f in sheet.facts] == [
        "On 2026-10-02, in “The roof”, they said: “The roof leaks over the porch again”",
        "a decision: a metal roof, because it lasts"]  # never the journal's
    sheet = Sheet("discussed", "")
    PLAN_BY_NAME["discussed"].gather(context, sheet, "Have I mentioned this problem before?", None)
    assert [f.kind for f in sheet.facts] == ["missing"] and "Name it" in sheet.facts[0].text


def test_what_their_assets_earn():
    from core.question_plans import PLAN_BY_NAME, Sheet

    looked = []
    registry = SimpleNamespace(_actions={"list_properties": 1, "get_property_summary": 1, "list_products": 1,
                                         "list_goods_on_hand": 1, "get_ledger_summary": 1},
                               execute=lambda context, tool, arguments: looked.append(tool) or f"{tool} says so.")
    estate = SimpleNamespace(all_properties=lambda: [SimpleNamespace(name="Duplex")])
    sheet = Sheet("returns", "")
    PLAN_BY_NAME["returns"].gather(SimpleNamespace(assistant_actions=registry, real_estate=estate), sheet,
                                   "Which of my assets are generating the best returns?", None)
    assert looked == ["list_properties", "get_property_summary", "list_products", "list_goods_on_hand",
                      "get_ledger_summary"]
    assert sheet.facts[-1].kind == "estimate" and "outside MIA" in sheet.facts[-1].text


def test_where_their_time_goes(monkeypatch):
    from datetime import date

    import core.calendar_view as cv
    from core.question_plans import PLAN_BY_NAME, Sheet

    monkeypatch.setattr(cv, "calendar_items", lambda context, start, end, today=None: [
        {"kind": "event"}, {"kind": "shift"}, {"kind": "shift"}, {"kind": "shift"}])
    looked = []
    registry = SimpleNamespace(_actions={"get_dungeon_loot": 1, "get_workout_summary": 1},
                               execute=lambda context, tool, arguments: looked.append(tool) or f"{tool} says so.")
    sheet = Sheet("time", "")
    PLAN_BY_NAME["time"].gather(SimpleNamespace(assistant_actions=registry), sheet,
                                "What am I spending too much time on?", date(2026, 11, 6))
    assert looked == ["get_dungeon_loot", "get_workout_summary"]
    assert "This week's calendar has 4 things: 3 shift, 1 event." in [f.text for f in sheet.facts]
    assert sheet.facts[-1].kind == "estimate"


def test_what_might_be_holding_them_back(tmp_path):
    from core.question_plans import PLAN_BY_NAME, Sheet

    notes = LifeNotes(data_dir=tmp_path)
    notes.add("dropped_goal", "the half marathon", why="my knee hurts")
    notes.add("commitment", "fix his gate", who="Sam")
    memories = [SimpleNamespace(text="Mornings are hard after night shifts", category="Struggles & Patterns")]
    context = SimpleNamespace(user_memories=SimpleNamespace(all_memories=lambda: memories), insights=None,
                              life_notes=notes)
    sheet = Sheet("held back", "")
    PLAN_BY_NAME["held back"].gather(context, sheet, "What is holding me back?", None)
    texts = [f.text for f in sheet.facts]
    assert "You told MIA: Mornings are hard after night shifts" in texts
    assert "a goal set aside: the half marathon, because my knee hurts" in texts
    assert any(t.startswith("a promise to Sam: fix his gate") for t in texts)  # still open



def test_what_the_workshop_costs_to_run():
    from core.question_plans import PLAN_BY_NAME, Sheet

    looked = []
    registry = SimpleNamespace(_actions={"get_ledger_summary": 1, "get_business_use": 1, "get_build_costs": 1,
                                         "list_maintenance_assets": 1},
                               execute=lambda context, tool, arguments: looked.append(tool) or f"{tool} says so.")
    sheet = Sheet("running costs", "")
    PLAN_BY_NAME["running costs"].gather(SimpleNamespace(assistant_actions=registry), sheet,
                                         "How much does it cost to operate my workshop?", None)
    assert looked == ["get_ledger_summary", "get_business_use", "get_build_costs", "list_maintenance_assets"]
    assert sheet.facts[-1].kind == "estimate"



def test_only_keep_it_keeps_and_one_question_at_a_time(tmp_path):
    context = SimpleNamespace(life_notes=LifeNotes(data_dir=tmp_path))
    chat = _chat()
    life_notes.offer_after(context, chat, "I should try selling honey")
    assert life_notes.answer_offer(context, chat, "yes") is None  # a bare yes may be for something else
    life_notes.offer_after(context, chat, "I should try selling honey")
    assert life_notes.answer_offer(context, chat, "Yes, keep it.").startswith("Kept: an idea: selling honey")
    chat.pending_offer = SimpleNamespace(shown=True)  # she already asked to log something this turn
    assert life_notes.offer_after(context, chat, "I promised Sam I'd fix his gate") is None
