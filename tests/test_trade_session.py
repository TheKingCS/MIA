"""
tests.test_trade_session
==========================

Walking someone through a job or a diagnosis (core/trade_session.py, core/trade_actions.py, DEC-0149): started by
their words, one step at a time, never past a hold point until it's checked, why and what to watch for on any step,
a stop rule's words ending it at once with what to do instead, a job planned as a mission that the steps count toward,
and a diagnosis worked by yes and no to its cause.
"""

import pytest

from core import trade_session as ts
from core import trades
from core.actions import ActionCenter
from core.trade_actions import reply
from tests.engine_world import build_world


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


def test_a_job_planned_as_a_mission_is_counted_step_by_step(world):
    """"Make it a mission": one objective a phase; each step done counts toward its phase."""
    reply(world, "walk me through building the greenhouse")
    assert "Added the mission “Build: Hoop-house greenhouse (high tunnel)”" in reply(world, "make it a mission")
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
    """A diagnosis finished and a job stopped are lines in the person's history; trades.finished reads the share, and
    trades.depth says how much of the wanted list is written and what's next."""
    from core import life_events
    from core.loops import _trades_depth, _trades_finished

    reply(world, "my toilet keeps running, help me figure it out")
    reply(world, "yes")
    reply(world, "yes")
    reply(world, "walk me through building the coop")
    reply(world, "stop the job")
    kinds = [e.type for e in life_events.events_for(world, types=("trade_finished", "trade_stopped"))]
    assert sorted(kinds) == ["trade_finished", "trade_stopped"]
    assert _trades_finished(world).value == 0.5
    depth = _trades_depth(world)
    assert depth.n == len(trades.WANTED) and "next: workshop_circuit" in depth.detail
