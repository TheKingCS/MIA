"""
tests.test_did_it
===================

"I did X" (core/did_it.py, DEC-0148): what the person says they did is kept in their history, counted toward a
routine it names (undoable), and offered once toward a task, a mission objective, or as a new routine when they keep
doing it; never a negative, a vague or self-critical "I did", or a private conversation.
"""

from datetime import date, datetime, timedelta
from types import SimpleNamespace

import pytest

from core import did_it, life_events
from core.actions import ActionCenter
from core.household_routines import add_routine
from tests.engine_world import build_world


@pytest.fixture
def world(tmp_path, monkeypatch):
    """The shared test world with an action center and a Laundry routine."""
    context = build_world(tmp_path, monkeypatch)
    context.actions = ActionCenter()
    context.laundry = add_routine(context, "Laundry", 1, "day")
    return context


def _talk():
    """A plain everyday conversation."""
    return SimpleNamespace(mode="normal", journal=False, off_record=False, private_turn=False, pending_track=None,
                           pending_note=None, did_handled=None, conversation_id="c1")


def _did(world):
    """The "did" lines in the person's own history, oldest first."""
    return [e.summary for e in reversed(life_events.events_for(world, types=[did_it.EVENT]))]


def test_the_activities_in_what_someone_says_they_did():
    """Several in one breath, either phrasing of the same thing as one key, a habit, and never a negative, a question
    alone, or "I did something stupid"."""
    found, whole = did_it.activities("I just put away the dishes and started a load of laundry")
    assert found == ["put away the dishes", "started a load of laundry"] and whole
    assert did_it.key("put the dishes away") == did_it.key("put away the dishes") == "put dish"
    assert did_it.activities("I did the dishes, what should I cook tonight?") == (["did the dishes"], False)
    assert did_it.activities("I've been running every morning") == (["been running every morning"], True)
    for nothing in ("I did something stupid", "I didn't do the dishes", "made a mistake", "what did you do today",
                    "I think it went well"):
        assert did_it.activities(nothing) == ([], False), nothing


def test_a_routine_it_names_is_counted_and_everything_said_is_kept(world):
    """"Started a load of laundry" counts toward Laundry through routine.log (undoable); the dishes are noted; both
    are lines in their history."""
    conversation = _talk()
    said = did_it.reply(world, conversation, "I just put away the dishes and started a load of laundry")
    assert "Laundry: 1 of 1" in said and "Noted: put away the dishes" in said and "undo that" in said
    assert _did(world) == ["Did: put away the dishes", "Did: started a load of laundry"]
    assert [p.kind for p in world.actions._proposals.values()] == ["routine.log"]


def test_a_task_or_an_objective_it_matches_is_offered_and_a_yes_does_it(world):
    """An open task with that name is offered to be marked done; a mission's tally objective, to be counted; a yes
    does it as the person, anything else lets it go."""
    project = world.projects.add_project("Garden")
    task = world.tasks.add_task(project.project_id, "Fix the gate")
    conversation = _talk()
    said = did_it.reply(world, conversation, "I fixed the gate")
    assert "your task “Fix the gate”" in said and conversation.pending_track["kind"] == "task.done"
    assert "done" in did_it.answer_offer(world, conversation, "yes please")
    assert world.tasks.get_task(task.task_id).done
    mission = world.missions.add_mission("Get fit")
    world.missions.add_objective(mission.mission_id, "Walk the dog 10 times", "tally", 10)
    said = did_it.reply(world, conversation, "I walked the dog")
    assert "Walk the dog 10 times" in said
    assert did_it.answer_offer(world, conversation, "not now") is None and conversation.pending_track is None
    assert world.missions.get_mission(mission.mission_id).objectives[0].progress == 0


def _said_yesterday(world, what):
    """A "did" line in the person's history from yesterday, as record() would have written it then."""
    import json

    from core.at_rest import seal_line

    at = (datetime.now() - timedelta(days=1)).isoformat(timespec="seconds")
    line = json.dumps({"event_id": "y1", "at": at, "type": did_it.EVENT, "summary": f"Did: {what}", "refs": [],
                       "payload": {"key": did_it.key(what)}, "source": "said", "profile_id": None})
    with open(world.personal_life_events.path, "a", encoding="utf-8") as out:
        out.write(seal_line(world.personal_life_events.path, line) + "\n")


def test_something_done_again_with_nothing_tracking_it_is_offered_as_a_routine(world):
    """Said on another day lately, it's offered as a routine; "I've been ..." is offered at once; a yes adds it."""
    conversation = _talk()
    assert "routine" not in did_it.reply(world, conversation, "I set out my work clothes")  # the first time: noted
    _said_yesterday(world, "made tomorrow's coffee")
    said = did_it.reply(world, conversation, "I made tomorrow's coffee")
    assert "You did that on 2 days lately. Want me to make made tomorrow's coffee a routine" in said
    assert conversation.pending_track["kind"] == "routine.add"
    assert "Added" in did_it.answer_offer(world, conversation, "yes")
    assert any(t.name == "Made tomorrow's coffee" for t in world.recurring_missions.all_templates())
    said = did_it.reply(world, conversation, "I've been running every morning")
    assert "Want me to track running every morning as a routine" in said


def test_a_question_goes_to_the_model_and_what_it_said_is_kept_after(world):
    """With a question in it, reply() leaves it for the model; afterwards the activity is kept, a routine's is never
    counted there (the model may have), and nothing private is ever taken."""
    conversation = _talk()
    assert did_it.reply(world, conversation, "I started the laundry, what should I cook tonight?") is None
    assert did_it.offer_after(world, conversation, "I started the laundry, what should I cook tonight?") is None
    assert _did(world) == ["Did: started the laundry"] and not world.actions._proposals
    private = _talk()
    private.journal = True
    assert did_it.reply(world, private, "I put away the dishes") is None
    assert did_it.offer_after(world, private, "I put away the dishes") is None and len(_did(world)) == 1


def test_the_whole_turn_counts_the_routine_without_the_model_and_a_yes_next_turn_tracks_the_rest(world):
    """Through run_assistant_turn, as the phone and voice go: a message that's only what they did never reaches the
    model; the routine is counted; the next turn's yes adds what they keep doing as a routine. A question still goes
    to the model, and a workout said is still the workout command's."""
    from core.assistant_turn import run_assistant_turn
    from core.conversation_manager import ConversationManager
    from core.llm_manager import ChatReply

    world.conversations = ConversationManager(world, data_dir=world.my_dir)
    asked = []
    world.llm = SimpleNamespace(chat_with_tools=lambda m, t: asked.append(1) or ChatReply(content="Sounds good."))
    conversation = world.conversations.create_conversation()
    _said_yesterday(world, "put away the dishes")
    [said] = run_assistant_turn(world, conversation, "I just put away the dishes and started a load of laundry").replies
    assert "Laundry: 1 of 1" in said and "make put away dishes a routine" in said and not asked
    [done] = run_assistant_turn(world, conversation, "yes").replies
    assert done.startswith("Added Put away dishes") and not asked
    replies = run_assistant_turn(world, conversation, "I picked up the kitchen, is it going to rain?").replies
    assert replies[0] == "Sounds good." and asked
