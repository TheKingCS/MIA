"""Taught skills, phase 1 (DEC-0123): steps read and written as lines, teaching by telling and by watching, a run
that stops for the person, practising until two clean runs, the steps that ask every time whatever was learned, and
each run kept in the run book through its waits to its end (UI-1)."""

import pytest

from core import taught_skills as ts
from core.assistant_actions import AssistantAction, AssistantActionRegistry
from core.assistant_taught_skill_actions import register_taught_skill_actions
from core.taught_skills import LEARNED, PRACTISING, SkillBook, SkillError
from tests.test_crafting import do, shop  # noqa: F401  (the fixture)

RESET = "tell: Friday reset.\nask: What's the one thing for next week? -> thing\naction: mission.add name={thing}\n" \
        "you: put the bins out"


@pytest.fixture
def world(shop):  # noqa: F811
    """The shop world with a skill book, the skill tools, a tool that adds a mission and one that deletes them."""
    from core.actions import run_as_tool

    w = shop
    w.taught_skills = SkillBook(w, data_dir=w.my_dir)
    reg = AssistantActionRegistry()
    register_taught_skill_actions(reg)
    none = {"type": "object", "properties": {}, "required": []}
    reg.register(AssistantAction(name="add_a_mission", domain="missions", description="Adds a mission.",
                                 parameters=none, trigger_phrases=("add a mission",),
                                 handler=lambda c, a: run_as_tool(c, "mission.add", {"name": a.get("name")})))
    reg.register(AssistantAction(name="tidy_up_missions", domain="missions", description="Tidies the missions.",
                                 parameters=none, trigger_phrases=("tidy missions",),
                                 handler=lambda c, a: run_as_tool(
                                     c, "mission.delete", {"mission_id": c.missions.all_missions()[0].mission_id})))
    reg.register(AssistantAction(name="get_mission_count", domain="missions", description="Counts missions.",
                                 parameters=none, trigger_phrases=("how many missions",),
                                 handler=lambda c, a: f"{len(c.missions.all_missions())} missions."))
    reg.register(AssistantAction(name="break_something", domain="missions", description="Breaks.",
                                 parameters=none, trigger_phrases=("break it",), handler=lambda c, a: 1 / 0))
    w.assistant_actions = reg
    return w


def names(w):
    """The names of the world's missions."""
    return [m.name for m in w.missions.all_missions()]


def run_reset(w, thing):
    """Runs the Friday reset to its end, answering everything; the last result."""
    skill = w.taught_skills.find("friday reset")
    got = ts.start(w, skill.skill_id)
    while got["status"] == "waiting":
        got = ts.answer(w, thing if got["waiting"]["kind"] == "ask" else "yes")
    return got


def test_steps_are_read_from_lines_and_written_back_the_same():
    steps = ts.parse_steps("1. tell: Hello there\n- ask: Which day? -> Day One\n\nyou: lock the shed\n"
                           "tool: add_a_mission name=Water the beds, hours=2, urgent=true\n"
                           "action: mission.add name={day_one}, summary=a, b")
    assert steps[1] == {"kind": "ask", "question": "Which day?", "as": "day_one"}
    assert steps[3]["arguments"] == {"name": "Water the beds", "hours": 2, "urgent": True}
    assert steps[4]["params"] == {"name": "{day_one}", "summary": "a, b"}
    assert ts.parse_steps(ts.format_steps(steps)) == steps
    odd = [{"kind": "tool", "tool": "x", "arguments": {"n": "5", "tags": ["a", "b"]}}]
    assert ts.parse_steps(ts.format_steps(odd)) == odd  # what key=value would change is written as JSON
    with pytest.raises(SkillError, match="can't read this step"):
        ts.parse_steps("tell: fine\nfly to the moon")
    with pytest.raises(SkillError, match="isn't key=value"):
        ts.parse_steps("tool: add_a_mission just words")


def test_a_skill_is_only_made_of_things_mia_can_already_do(world):
    wrong = " ".join(ts.step_problems(world, ts.parse_steps(
        "tool: launch_rocket\naction: rocket.launch\ntool: run_taught_skill skill=x\naction: taught_skill.delete")))
    assert 'tool called "launch_rocket"' in wrong and 'action called "rocket.launch"' in wrong
    assert wrong.count("can't teach or run skills") == 2
    assert ts.step_problems(world, []) == ["A skill needs at least one step."]
    with pytest.raises(SkillError, match="launch_rocket"):
        world.taught_skills.add("Launch", ts.parse_steps("tool: launch_rocket"))
    world.taught_skills.add("Count", ts.parse_steps("tool: get_mission_count"))
    with pytest.raises(SkillError, match="already a skill called count"):
        world.taught_skills.add("count", ts.parse_steps("tell: again"))


def test_a_practising_skill_asks_before_each_change_and_is_learned_after_two_clean_runs(world):
    do(world, "taught_skill.add", name="Friday reset", steps=RESET)
    skill = world.taught_skills.find("the friday reset skill")
    assert skill.state == PRACTISING and skill.source == "told in steps"

    got = ts.start(world, skill.skill_id)
    assert got["status"] == "waiting" and got["waiting"]["kind"] == "ask" and "Friday reset." in got["said"]
    got = ts.answer(world, "Order the seed trays")
    assert got["waiting"]["kind"] == "confirm" and "Order the seed trays" in got["waiting"]["text"]
    assert "Order the seed trays" not in names(world)  # nothing changes before the yes
    with pytest.raises(SkillError, match="yes or a no"):
        ts.answer(world, "hmm")
    got = ts.answer(world, "yes")
    assert "Order the seed trays" in names(world) and got["waiting"]["kind"] == "you"
    got = ts.answer(world, "done")
    assert got["status"] == "done" and "1 more clean run" in got["said"][-1]
    assert world.taught_skills.active is None and skill.clean_runs == 1 and skill.state == PRACTISING

    got = run_reset(world, "Fix the gate")
    assert skill.state == LEARNED and "I've learned" in got["said"][-1]
    # Learned: it still stops for the question and the person's own task, but not for the change it has proven.
    got = ts.start(world, skill.skill_id)
    got = ts.answer(world, "Sharpen the tools")
    assert got["waiting"]["kind"] == "you" and "Sharpen the tools" in names(world)
    assert ts.answer(world, "done")["status"] == "done" and skill.runs == 3


def test_paying_sending_and_deleting_ask_every_time_even_when_learned(world):
    for kind in ("bill.pay", "order.pay", "shop.buy", "quote.send", "quote.email", "creation.publish",
                 "map.tak_share", "profile.edit", "mission.delete", "freedom.fund_account", "browser.commit"):
        assert ts.always_asks(kind), kind
    assert not ts.always_asks("mission.add") and not ts.always_asks("closet.wore")
    world.missions.add_mission("Old one")
    gone = world.missions.all_missions()[0].mission_id
    skill = world.taught_skills.add("Clear out", [{"kind": "action", "action": "mission.delete",
                                                  "params": {"mission_id": gone}}])
    skill.state = LEARNED
    got = ts.start(world, skill.skill_id)
    assert got["status"] == "waiting" and got["waiting"]["kind"] == "confirm" and "Old one" in names(world)
    assert ts.answer(world, "no")["status"] == "stopped" and "Old one" in names(world)
    assert skill.state == LEARNED and skill.last_result == "stopped by you"  # a no is not a failure
    ts.start(world, skill.skill_id)
    assert ts.answer(world, "go ahead")["status"] == "done" and "Old one" not in names(world)


def test_a_tool_cannot_pay_send_or_delete_inside_a_skill_on_the_strength_of_its_name(world):
    world.missions.add_mission("Keep me")
    skill = world.taught_skills.add("Tidy", ts.parse_steps("tool: tidy_up_missions\ntell: Tidied."))
    skill.state = LEARNED  # its name says nothing about deleting, and a learned skill doesn't ask for tools
    got = ts.start(world, skill.skill_id)
    assert got["status"] == "waiting" and got["waiting"]["kind"] == "confirm" and "Keep me" in names(world)
    got = ts.answer(world, "yes")
    assert got["status"] == "done" and "Keep me" not in names(world) and "Tidied." in got["said"]
    # The same holds for a tool that proposes and approves the action itself.
    def sweep(c, a):
        """A tool that approves its own delete."""
        p = c.actions.propose(c, "mission.delete", {"mission_id": c.missions.all_missions()[0].mission_id})
        return c.actions.approve(c, p.proposal_id).result

    world.assistant_actions.register(AssistantAction(
        name="sweep_missions", domain="missions", description="Sweeps.", handler=sweep, trigger_phrases=("sweep",),
        parameters={"type": "object", "properties": {}, "required": []}))
    world.missions.add_mission("Keep me too")
    sweeping = world.taught_skills.add("Sweep", ts.parse_steps("tool: sweep_missions"))
    sweeping.state = LEARNED
    got = ts.start(world, sweeping.skill_id)
    assert got["status"] == "waiting" and "Keep me too" in names(world)
    assert ts.answer(world, "yes")["status"] == "done" and "Keep me too" not in names(world)
    assert ts._TOOL_ALWAYS.search("record_debt_payment") and ts._TOOL_ALWAYS.search("undo_last_change")
    assert not ts._TOOL_ALWAYS.search("add_a_mission") and not ts._TOOL_ALWAYS.search("get_weather")
    # Outside a skill the same tool is what the person just asked for, and runs.
    world.missions.add_mission("Another")
    world.assistant_actions.execute(world, "tidy_up_missions", {})
    assert "Another" not in names(world)


def test_a_run_that_fails_sends_a_learned_skill_back_to_practising(world):
    skill = world.taught_skills.add("Shaky", ts.parse_steps("tell: Starting.\ntool: break_something\ntell: Never said."))
    skill.state, skill.clean_runs = LEARNED, 2
    got = ts.start(world, skill.skill_id)
    assert got["status"] == "stopped" and "Never said." not in got["said"] and "Step 2 didn't work" in " ".join(got["said"])
    assert skill.state == PRACTISING and skill.clean_runs == 0 and "back to practising" in got["said"][-1]
    gone = world.taught_skills.add("Missing", [{"kind": "action", "action": "mission.delete",
                                               "params": {"mission_id": "nope"}}])
    assert ts.start(world, gone.skill_id)["status"] == "stopped"  # the action's own check refused it


def test_changing_a_skills_steps_starts_its_practice_over(world):
    do(world, "taught_skill.add", name="Friday reset", steps=RESET)
    skill = world.taught_skills.find("friday reset")
    run_reset(world, "a"), run_reset(world, "b")
    assert skill.state == LEARNED
    p = world.actions.propose(world, "taught_skill.steps", {"skill_id": skill.skill_id, "steps": "tell: Just this."})
    assert "goes back to practising" in p.summary
    world.actions.approve(world, p.proposal_id)
    assert skill.state == PRACTISING and skill.clean_runs == 0 and len(skill.steps) == 1
    do(world, "taught_skill.delete", skill_id=skill.skill_id)
    assert world.taught_skills.skills == []


def test_watch_me_notes_what_is_done_and_keeps_it_as_a_skill(world):
    reg = world.assistant_actions
    reg.execute(world, "add_a_mission", {"name": "Before watching"})  # not watching yet: nothing noted
    assert ts.take_turn(world, "", "Watch me: the evening close").startswith("Watching.")
    assert "already watching" in ts.take_turn(world, "", "watch me: something else")
    reg.execute(world, "get_mission_count", {})
    reg.execute(world, "add_a_mission", {"name": "Lock the shed"})
    reg.execute(world, "list_taught_skills", {})  # her own skill tools are never steps
    reg.execute(world, "break_something", {})  # nor is a tool that failed
    do(world, "mission.add", name="Feed the fish")  # a change approved on a screen
    shown = world.taught_skills.recording["steps"]
    assert [s.get("tool") or s.get("action") for s in shown] == ["get_mission_count", "add_a_mission", "mission.add"]
    assert shown[1]["arguments"] == {"name": "Lock the shed"} and shown[2]["params"]["name"] == "Feed the fish"
    said = ts.take_turn(world, "", "that's it")
    assert said.startswith('Kept "the evening close"') and world.taught_skills.recording is None
    skill = world.taught_skills.find("evening close")
    assert skill.state == PRACTISING and len(skill.steps) == 3 and skill.source == "shown by doing it"
    # Kept across a restart, with nothing still being shown.
    again = SkillBook(world, data_dir=world.my_dir)
    assert again.find("evening close").steps == skill.steps and again.recording is None


def test_watching_with_nothing_shown_keeps_nothing_and_never_mind_drops_it(world):
    assert ts.take_turn(world, "", "that's it") is None  # not watching: an ordinary thing to say
    ts.take_turn(world, "", "watch me: nothing much")
    assert "haven't seen you do anything" in ts.take_turn(world, "", "that's it")
    assert ts.take_turn(world, "", "never mind") == 'Dropped "nothing much". Nothing was kept.'
    assert world.taught_skills.recording is None and world.taught_skills.skills == []


def test_a_run_is_followed_in_conversation_and_only_takes_the_answer_to_its_own_question(world):
    do(world, "taught_skill.add", name="Friday reset", steps=RESET)
    assert ts.take_turn(world, "", "what's the weather") is None
    said = ts.take_turn(world, "", "Run the Friday reset")
    assert said.endswith("What's the one thing for next week?")
    # The person moved on: her last message isn't the question, so this isn't taken as its answer.
    assert ts.take_turn(world, "It's sunny.", "add milk to the list") is None
    said = ts.take_turn(world, said, "Mend the fence")
    assert said.endswith("OK?") and "Mend the fence" in said
    assert ts.take_turn(world, said, "what does that mean") is None  # neither yes nor no: an ordinary message
    said = ts.take_turn(world, said, "yes")
    assert "Mend the fence" in names(world) and "Over to you: put the bins out" in said
    assert "1 more clean run" in ts.take_turn(world, said, "done")
    assert "still running" not in (ts.take_turn(world, "", "run friday reset") or "")


def test_only_one_skill_runs_at_a_time_and_a_stopped_run_counts_for_nothing(world):
    do(world, "taught_skill.add", name="Friday reset", steps=RESET)
    skill = world.taught_skills.find("friday reset")
    ts.start(world, skill.skill_id)
    with pytest.raises(SkillError, match="still running"):
        ts.start(world, skill.skill_id)
    with pytest.raises(SkillError, match="only runs with you there"):
        world.taught_skills.active = None
        ts.start(world, skill.skill_id, watched=False)
    ts.start(world, skill.skill_id)
    assert ts.stop(world) and not ts.stop(world)
    assert skill.clean_runs == 0 and skill.state == PRACTISING and skill.last_result == "stopped by you"
    with pytest.raises(SkillError, match="No skill is waiting"):
        ts.answer(world, "yes")


def test_undo_takes_back_the_step_she_did_and_not_the_fact_that_the_skill_ran(world):
    do(world, "taught_skill.add", name="Friday reset", steps=RESET)
    skill = world.taught_skills.find("friday reset")
    run_reset(world, "Paint the door")
    assert "Paint the door" in names(world) and skill.runs == 1
    change = world.undo.pop(world.me.profile_id)
    assert change is not None and not any(p.name == "taught_skills.json" for p in change.files)


def test_the_voice_tools_are_the_same_doors(world):
    reg = world.assistant_actions
    assert reg.execute(world, "list_taught_skills", {}).startswith("You haven't taught me a skill yet.")
    said = reg.execute(world, "teach_skill_in_steps", {"name": "Friday reset", "steps": RESET})
    assert said.startswith("Got it.") and world.taught_skills.find("friday reset") is not None
    assert "Friday reset (practising, 0 of 2 clean runs)" in reg.execute(world, "list_taught_skills", {})
    said = reg.execute(world, "run_taught_skill", {"skill": "friday reset"})
    assert said.endswith("What's the one thing for next week?")
    assert reg.execute(world, "answer_taught_skill", {"answer": "Stack the wood"}).endswith("OK?")
    assert reg.execute(world, "stop_taught_skill", {}) == "Stopped."
    assert reg.execute(world, "run_taught_skill", {"skill": "nothing like it"}).startswith("I don't have a skill")
    assert reg.execute(world, "forget_taught_skill", {"skill": "friday reset"}) == 'Forgot "Friday reset".'
    reg.execute(world, "watch_me_teach", {"name": "Close up"})
    reg.execute(world, "add_a_mission", {"name": "Lock the gate"})
    assert reg.execute(world, "keep_taught_skill", {}).startswith('Kept "Close up"')
    assert len(world.taught_skills.find("close up").steps) == 1


def test_the_screen_shows_each_step_in_words_and_marks_the_ones_that_will_ask(world):
    from core.web_taught_skills import skills_page

    world.missions.add_mission("Old one")
    gone = world.missions.all_missions()[0].mission_id
    world.taught_skills.add("Mixed", [{"kind": "tell", "text": "Hi"},
                                      {"kind": "action", "action": "mission.add", "params": {"name": "New"}},
                                      {"kind": "action", "action": "mission.delete", "params": {"mission_id": gone}}])
    page = skills_page(world)
    row = page["skills"][0]
    assert [s["asks"] for s in row["steps"]] == [False, True, True]
    assert [s["always_asks"] for s in row["steps"]] == [False, False, True]
    assert row["steps"][0]["text"] == 'Say: "Hi"' and "Old one" in row["steps"][2]["text"]
    assert ts.parse_steps(row["steps_text"]) == world.taught_skills.skills[0].steps
    ts.take_turn(world, "", "watch me: later")
    assert skills_page(world)["watching"] == {"name": "later", "steps": []}
    assert skills_page(type("Bare", (), {})())["available"] is False


def test_each_skill_run_is_kept_in_the_run_book_through_its_waits_to_its_end(world):
    """UI-1 (core/runs.py): a skill run appears as waiting at each question, confirm and task of the person's, and
    ends done; one stopped by the person ends stopped, saying so. How the skill runs doesn't change."""
    from core.runs import RunBook

    world.runs = RunBook(world, data_dir=world.my_dir)
    do(world, "taught_skill.add", name="Friday reset", steps=RESET)
    skill = world.taught_skills.find("friday reset")
    got = ts.start(world, skill.skill_id)
    [run] = world.runs.open_runs()
    assert run.source == "taught_skills" and run.ref == f"skill:{skill.skill_id}" and run.title == "Friday reset"
    assert run.status == "waiting" and run.waiting["kind"] == "ask" and "one thing" in run.waiting["text"]
    got = ts.answer(world, "Order the seed trays")
    assert run.waiting["kind"] == "confirm"
    ts.answer(world, "yes")
    assert run.waiting["kind"] == "you"
    assert ts.answer(world, "done")["status"] == "done" and run.status == "done" and run.steps
    ts.start(world, skill.skill_id)
    [second] = world.runs.open_runs()
    assert ts.stop(world)
    assert second.status == "stopped" and "by you" in second.why
    from core import runs

    runs._RECOVERED.clear()
    later = RunBook(world, data_dir=world.my_dir)  # a restart: nothing left looking alive
    assert not later.open_runs()
