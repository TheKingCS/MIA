"""
tests.test_trade_session
==========================

Walking someone through a job or a diagnosis (core/trade_session.py, core/trade_actions.py, DEC-0149): started by
their words, one step at a time, never past a hold point until it's checked, why and what to watch for on any step,
a stop rule's words ending it at once with what to do instead, a job planned as a mission that the steps count toward,
and a diagnosis worked by yes and no to its cause. And a question about the job in progress ("what tools do I need
for this job?") answered by the "the job" question plan from code: its step, its tools against the inventory, its
stop rules.
"""

import pytest

from core import trade_session as ts
from core import trades
from core.actions import ActionCenter
from core.trade_actions import reply
from tests.engine_world import build_world

trades._loaded()  # the content, before the diagnoses are listed for parametrize


@pytest.fixture
def world(tmp_path, monkeypatch):
    """The shared test world with an action center and the person's trade session store."""
    context = build_world(tmp_path, monkeypatch)
    context.actions = ActionCenter()
    context.trade_session = ts.TradeStore(context, data_dir=context.my_dir)
    return context


def test_a_job_is_started_by_their_words_and_never_passes_a_hold_point_unchecked(world):
    """"Walk me through building the coop" starts it (drafted, its permit and PPE said); a step with a hold refuses
    "next" until "checked"; why and what to watch for answer from the step itself."""
    said = reply(world, "walk me through building the coop")
    assert said.startswith("Chicken coop and run (drafted") and "Permit:" in said and "step 1 of" in said
    coop = trades.JOBS["chicken_coop"]
    first_hold = next(n for n, (_p, _i, s) in enumerate(coop.steps()) if s.hold)
    for _ in range(first_hold):
        assert "step" in reply(world, "next")
    assert reply(world, "next").startswith("Not yet:")
    assert reply(world, "why?") == coop.steps()[first_hold][2].why
    assert reply(world, "what should I watch for") == " ".join(coop.steps()[first_hold][2].watch)
    assert reply(world, "checked").startswith("Checked.")
    assert f"step {first_hold + 2} of" in reply(world, "next")
    assert f"step {first_hold + 1} of" in reply(world, "back")
    assert reply(world, "where am i") == ts.say(world.trade_session.live())


def test_a_stop_rule_s_words_end_the_job_at_once_with_what_to_do_instead(world):
    """Whatever else is said, "I cut myself, it's bleeding" stops the session with the injury rule's instead."""
    reply(world, "walk me through building the workshop")
    said = reply(world, "ugh I cut myself and it's bleeding, next")
    assert said == trades.STOP_RULES["injury"].instead and world.trade_session.live() is None
    assert reply(world, "next") is None  # nothing in progress any more, and "next" alone starts nothing


def test_a_job_is_a_mission_from_the_start_counted_step_by_step(world):
    """Starting a job makes its mission (one objective a phase), said in the reply; "make it a mission" then says
    it already is one; each step done counts toward its phase."""
    assert "It's in your Missions as “Build: Hoop-house greenhouse (high tunnel)”" in reply(
        world, "walk me through building the greenhouse")
    assert "is already one of your missions" in reply(world, "make it a mission")
    mission = next(m for m in world.missions.all_missions() if m.name.startswith("Build: Hoop-house"))
    assert [o.description for o in mission.objectives] == [p.name for p in trades.JOBS["hoop_house"].phases]
    reply(world, "next")
    assert world.missions.get_mission(mission.mission_id).objectives[0].progress == 1


def test_a_diagnosis_goes_by_yes_and_no_to_its_cause(world):
    """The running toilet: dye shows in the bowl, the flapper is worn: that's the cause."""
    said = reply(world, "my toilet keeps running, help me figure it out")
    assert "Safety first" in said and "food coloring" in said
    assert "flapper" in reply(world, "yes")
    assert reply(world, "yes").startswith("Found it: the flapper (or its seat) is worn")
    assert world.trade_session.live() is None


def test_words_that_aren_t_for_a_job_are_left_alone(world):
    """No job in progress and nothing that asks for one: reply() says nothing, so the turn goes on as usual."""
    assert reply(world, "what's the weather tomorrow") is None
    assert reply(world, "walk me through baking sourdough") is None  # no such job written yet


def test_finishing_or_stopping_is_kept_and_the_loops_read_it(world):
    """A diagnosis finished and a job stopped are lines in the person's history, once each (saving again records
    nothing more); trades.finished reads the share, and trades.depth says how much of the wanted list is written and
    what's next."""
    from core import life_events
    from core.loops import _trades_depth, _trades_finished

    reply(world, "my toilet keeps running, help me figure it out")
    reply(world, "yes")
    reply(world, "yes")
    reply(world, "walk me through building the coop")
    reply(world, "stop the job")
    world.trade_session.save()
    kinds = [e.type for e in life_events.events_for(world, types=("trade_finished", "trade_stopped"))]
    assert sorted(kinds) == ["trade_finished", "trade_stopped"]
    assert _trades_finished(world).value == 0.5
    depth = _trades_depth(world)
    upcoming = trades.depth()["next"]
    assert depth.n == len(trades.WANTED) and f"next: {upcoming}" in depth.detail


def test_the_model_is_given_the_job_and_step_it_s_asked_about(world):
    """Mid-job, the system message carries the job, the step with why, its hold and the stop rules, and the rule never
    to skip either; with no job going, a question about building one carries its outline, and a passing mention of
    the place doesn't."""
    from core.assistant_chat import build_system_message
    from core.trade_session import context_block

    assert context_block(world, "I'm out in the workshop") == ""
    asked = context_block(world, "what's involved in building a chicken coop?")
    assert asked.startswith("A job the person may be asking about: Chicken coop and run") and "stop rules" in asked
    reply(world, "walk me through building the workshop")
    block = context_block(world, "can I use a smaller header?")
    step = trades.JOBS["workshop"].steps()[0][2]
    assert f"step 1 of {len(trades.JOBS['workshop'].steps())}: {step.do}" in block and f"Why: {step.why}" in block
    assert "Never suggest skipping a hold point or working past a stop rule." in block
    assert block in build_system_message(world, False, prompt="can I use a smaller header?")


@pytest.mark.parametrize("diag_id", sorted(trades.DIAGNOSES))
def test_every_path_through_every_diagnosis_ends_in_a_cause_or_a_professional(diag_id):
    """Every run of yes and no answers, through the session itself, ends in "Found it" or a professional to call,
    never a dead end or a loop."""
    from datetime import datetime

    d = trades.DIAGNOSES[diag_id]
    paths = [[]]
    endings = 0
    while paths:
        answers = paths.pop()
        s = ts.start(d, datetime(2026, 11, 8))
        said = ""
        for yes in answers:
            said = ts.answer(s, yes)
        if s.status == ts.FINISHED:
            assert said.startswith(("Found it: ", "This one's for ")), (diag_id, answers, said)
            endings += 1
            continue
        assert len(answers) < len(d.checks) + 1, (diag_id, answers)  # no loops
        paths += [answers + [True], answers + [False]]
    assert endings >= len(d.checks)


def test_a_symptom_said_starts_its_diagnosis_with_safety_first(world):
    """"My breaker keeps tripping, help me figure it out" starts the breaker diagnosis, safety said before the first
    check."""
    said = reply(world, "my breaker keeps tripping, help me figure it out")
    assert said.startswith("A breaker that keeps tripping") and "Never take the panel cover off" in said
    assert "Unplug or switch off everything on that circuit" in said


def test_a_question_about_this_job_gets_its_step_tools_and_stop_rules_from_code(world):
    """With a job in progress, the "the job" plan's sheet has the job, the step in focus, the tools (any in the
    inventory marked as had), and its stop rules; with none in progress, "this job" asks to name one, other words step
    aside, and a job the words name is outlined."""
    from core import question_plans as qp

    from core.inventory_manager import InventoryManager

    plan = qp.PLAN_BY_NAME["the job"]
    world.inventory = InventoryManager(world, data_dir=world.my_dir)
    world.inventory.add_item("Drill/driver", quantity=1, category="tools")
    reply(world, "walk me through building the coop")
    sheet = qp.gather(world, plan, "What tools do I need for this job?")
    text = sheet.as_text()
    assert "Chicken coop and run" in text and "Where you are:" in text and "Stop and get help if" in text
    assert "seem to have already" in text and "drill/driver" in text.lower()
    reply(world, "stop the job")
    assert "No job or repair is in progress" in qp.gather(world, plan, "What step am I on in this job?").as_text()
    assert qp.gather(world, plan, "troubleshoot my wifi").facts == []
    assert "circuit to the workshop" in qp.gather(world, plan, "what tools do I need for the workshop circuit").as_text()


def test_the_job_in_progress_is_in_missions_not_on_today(world):
    """Zac, 2026-11-09: a job walked through belongs in Missions, not Today; neither a job nor a repair being worked
    out puts anything on Today's list."""
    from core.today import today_items

    reply(world, "walk me through building the coop")
    assert any(m.name == "Build: Chicken coop and run" for m in world.missions.all_missions())
    assert not any(i.title.startswith("Chicken coop") for i in today_items(world))
    reply(world, "stop the job")
    reply(world, "help me figure out why my toilet keeps running")
    assert not any("working it out" in i.title for i in today_items(world))
