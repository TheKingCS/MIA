"""User Sync, Meals (core/user_sync.py): what the code decides, with a
stand-in model. tools/user_sync_check.py runs the same steps on the real one."""

import json
from datetime import date
from pathlib import Path

from core import user_sync
from core.actions import ActionCenter
from core.relationships_manager import RelationshipsManager
from core.user_memory_manager import UserMemoryManager
from tests.engine_world import build_world
from tools.user_sync_check import missing_and_extra

QS = user_sync.TOPICS["meals"]["questions"]


class Model:
    def __init__(self, reply):
        self.reply = reply

    def generate(self, prompt):
        return self.reply if isinstance(self.reply, (str, type(None))) else json.dumps(self.reply)


def make(tmp_path, monkeypatch, reply=None, only="meals"):
    """In one topic, past the phone; `only=None` is the whole of it from the start."""
    world = build_world(tmp_path, monkeypatch)
    world.actions = ActionCenter()
    world.llm = Model(reply)
    if only:
        monkeypatch.setattr(user_sync, "TOPICS", {only: user_sync.TOPICS[only]})
    user_sync.start(world)
    if only:
        user_sync.choose(world, "skip")
    return world


def answer_all(world, *answers):
    now = None
    for said in answers:
        now = user_sync.reply(world, said)
    return now


BOARD = {"dishes": ["Chicken and rice", "tacos"], "prep_day": "Sunday", "avoid": []}


def test_nothing_is_saved_before_the_yes(tmp_path, monkeypatch):
    world = make(tmp_path, monkeypatch, BOARD)
    assert user_sync.state(world)["question"] == QS[0]
    assert user_sync.reply(world, "Chicken and rice, sometimes tacos")["question"] == QS[1]
    now = answer_all(world, "I meal prep on Sundays", "no")
    assert now["step"] == "review"
    assert [c["text"] for c in now["chips"]] == ["Chicken and rice", "Tacos", "Sunday meal prep"]
    assert world.kitchen.all_recipes() == []
    assert not [m for m in world.missions.all_missions() if m.name == "Sunday meal prep"]

    done = user_sync.reply(world, "looks right")
    assert done["done"] is True and done["say"].startswith("Saved 3.")
    assert sorted(r.name for r in world.kitchen.all_recipes()) == ["Chicken and rice", "Tacos"]
    assert [m for m in world.missions.all_missions() if m.name == "Sunday meal prep"]


def test_each_saved_chip_can_be_undone(tmp_path, monkeypatch):
    world = make(tmp_path, monkeypatch, {"dishes": ["tacos"], "prep_day": "", "avoid": []})
    answer_all(world, "tacos", "skip", "skip")
    user_sync.choose(world, "approve")
    assert len(world.kitchen.all_recipes()) == 1
    proposal = next(p for p in world.actions._proposals.values() if p.kind == "recipe.add")
    assert proposal.proposed_by == "mia" and proposal.status == "executed"
    world.actions.undo(world, proposal.proposal_id)
    assert world.kitchen.all_recipes() == []


def test_not_that_one_drops_a_chip(tmp_path, monkeypatch):
    world = make(tmp_path, monkeypatch, BOARD)
    now = answer_all(world, "Chicken and rice, sometimes tacos", "Sundays", "no")
    assert user_sync.reply(world, "not that one")["say"] == "Which one should I drop?"
    now = user_sync.reply(world, "not the tacos")
    assert [c["text"] for c in now["chips"]] == ["Chicken and rice", "Sunday meal prep"]
    now = user_sync.choose(world, "drop", 1)
    assert [c["text"] for c in now["chips"]] == ["Chicken and rice"]
    user_sync.choose(world, "approve")
    assert [r.name for r in world.kitchen.all_recipes()] == ["Chicken and rice"]


def test_what_they_never_said_is_thrown_away(tmp_path, monkeypatch):
    invented = {"dishes": ["Beef wellington", "tacos", "leftovers", 7], "prep_day": "Tuesday", "avoid": ["gluten"], "extra": 1}
    world = make(tmp_path, monkeypatch, invented)
    now = answer_all(world, "tacos and leftovers", "Sundays", "no")
    assert [c["text"] for c in now["chips"]] == ["Tacos"]


def test_a_recipe_they_already_have_is_not_proposed(tmp_path, monkeypatch):
    world = make(tmp_path, monkeypatch, {"dishes": ["tacos"], "prep_day": "", "avoid": []})
    world.kitchen.add_recipe("Tacos")
    assert answer_all(world, "tacos", "no", "no")["done"] is True
    assert len(world.kitchen.all_recipes()) == 1


def test_no_model_keeps_their_words_as_a_memory(tmp_path, monkeypatch):
    for reply in (None, "I can't help with that", '{"dishes": "tacos"'):
        world = make(tmp_path / str(hash(reply)), monkeypatch, reply)
        world.user_memories = UserMemoryManager(world, tmp_path / str(hash(reply)))
        now = answer_all(world, "mostly soup in winter", "no", "no")
        assert [c["app"] for c in now["chips"]] == ["Memory"]
        assert "mostly soup in winter" in now["chips"][0]["text"]
    assert user_sync.choose(world, "approve")["done"] is True
    assert [m.text for m in world.user_memories.all_memories()] == ["Meals: mostly soup in winter"]


def test_what_didnt_save_stays_on_screen(tmp_path, monkeypatch):
    world = make(tmp_path, monkeypatch, None)  # this world has no memory store
    world.user_memories = None
    answer_all(world, "mostly soup in winter", "no", "no")
    now = user_sync.reply(world, "looks right")
    assert now["step"] == "review" and "didn't save" in now["say"]
    assert now["chips"][0]["text"] == "mostly soup in winter"


def test_nothing_said_means_nothing_to_approve(tmp_path, monkeypatch):
    world = make(tmp_path, monkeypatch, BOARD)
    assert answer_all(world, "skip", "skip that one", "nothing")["done"] is True
    assert world.kitchen.all_recipes() == []


def test_finish_later_picks_up_at_the_same_question(tmp_path, monkeypatch):
    world = make(tmp_path, monkeypatch, BOARD)
    user_sync.reply(world, "tacos")
    now = user_sync.reply(world, "let's finish later")
    assert now["paused"] is True and now["active"] is False
    assert user_sync.hear(world, "what's on today") is None  # goes to Talk
    now = user_sync.hear(world, "let's keep going")
    assert now["active"] is True and now["question"] == QS[1]


def test_a_long_answer_with_later_in_it_is_an_answer(tmp_path, monkeypatch):
    world = make(tmp_path, monkeypatch, BOARD)
    now = user_sync.reply(world, "I eat later at night, usually tacos")
    assert now["paused"] is False and now["question"] == QS[1]


def test_answers_are_not_kept_once_approved(tmp_path, monkeypatch):
    world = make(tmp_path, monkeypatch, BOARD)
    answer_all(world, "Chicken and rice, sometimes tacos", "Sundays", "no", "yes")
    assert "tacos" not in json.dumps(user_sync._progress(world)).lower()


def test_each_person_has_their_own(tmp_path, monkeypatch):
    world = make(tmp_path, monkeypatch, BOARD)
    user_sync.reply(world, "tacos")
    world.profile_id = world.other.profile_id
    assert user_sync.state(world)["offer"] is True


def test_the_glasses_voice_reaches_it_and_says_so(tmp_path, monkeypatch):
    from core.glasses_voice import handle

    world = make(tmp_path, monkeypatch, BOARD)
    pid = world.me.profile_id
    talked = []
    out = handle(world, pid, "tacos", lambda w: talked.append(w), lambda w: user_sync.hear(world, w))
    assert out["sync"] is True and out["say"] == QS[1] and not talked
    out = handle(world, pid, "open kitchen", lambda w: talked.append(w), lambda w: user_sync.hear(world, w))
    assert "open" in out  # a command still works


def test_through_the_server(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    import server.app as server_app

    world = build_world(tmp_path, monkeypatch)
    world.profiles.set_password(world.me.profile_id, "pw")
    world.voice = world.push_subscriptions = None
    world.actions = ActionCenter()
    world.llm = Model(BOARD)
    client = TestClient(server_app.create_app(world))
    token = client.post("/api/login", json={"profile_id": world.me.profile_id, "password": "pw"}).json()["token"]
    client.headers.update({"Authorization": f"Bearer {token}"})

    assert client.get("/api/user-sync").json()["offer"] is True
    assert client.post("/api/user-sync", json={"choice": "start"}).json()["step"] == "phone"
    assert client.post("/api/user-sync", json={"permissions": {"microphone": True}}).json()["rows"][0]["status"] == "allowed"
    assert client.post("/api/user-sync", json={"choice": "skip"}).json()["say"].startswith("Let's talk about routines.")
    progress = user_sync._progress(world)
    progress["topics"] = {"routines": {"status": "skipped"}, "work": {"status": "skipped"}}
    user_sync._save(world, progress)
    for said in ("Chicken and rice, sometimes tacos", "Sundays", "no"):
        got = client.post("/api/glasses/voice", json={"text": said}).json()
    assert got["sync"] is True
    assert client.get("/api/user-sync").json()["step"] == "review"
    assert client.post("/api/user-sync", json={"choice": "approve"}).json()["step"] == "next"
    assert len(world.kitchen.all_recipes()) == 2


def chips_for(tmp_path, monkeypatch, topic, reply, *answers):
    world = make(tmp_path, monkeypatch, reply, only=topic)
    world.relationships = RelationshipsManager(world, tmp_path)
    now = answer_all(world, *answers)
    return world, now


def test_the_phone_step_shows_only_what_was_reported_and_never_blocks(tmp_path, monkeypatch):
    world = make(tmp_path, monkeypatch, None, only=None)
    now = user_sync.state(world)
    assert now["step"] == "phone" and {r["status"] for r in now["rows"]} == {"waiting"}
    now = user_sync.report(world, {"microphone": True, "location": False, "made_up": True})
    rows = {r["id"]: r["status"] for r in now["rows"]}
    assert rows["microphone"] == "allowed" and rows["location"] == "not yet" and rows["photos"] == "waiting" and "made_up" not in rows
    assert user_sync.reply(world, "skip")["say"].startswith("Let's talk about routines.")


def test_everything_allowed_moves_on_by_itself(tmp_path, monkeypatch):
    world = make(tmp_path, monkeypatch, None, only=None)
    now = user_sync.report(world, {key: True for key, _label in user_sync.PHONE_ASKS})
    assert now["step"] == "ask" and now["topic"] == "routines"


def test_she_offers_to_keep_going_after_each_topic(tmp_path, monkeypatch):
    world = make(tmp_path, monkeypatch, {"job": "nurse", "schedule": "", "upcoming": []}, only=None)
    user_sync.choose(world, "skip")
    user_sync.reply(world, "skip this topic")
    now = user_sync.state(world)
    assert now["step"] == "next" and now["topic"] == "work" and "finish later" in now["question"]
    assert user_sync.reply(world, "skip")["topic"] == "meals"  # skipping the one she offered
    assert user_sync.state(world)["step"] == "next"
    assert user_sync.reply(world, "keep going")["question"] == QS[0]


def test_a_child_is_never_asked_about_money(tmp_path, monkeypatch):
    world = make(tmp_path, monkeypatch, None, only=None)
    monkeypatch.setattr(user_sync, "is_child", lambda context: True)
    assert "money" not in user_sync._topics(world) and user_sync.state(world)["topics"] == len(user_sync.TOPICS) - 1


def test_a_weekly_thing_goes_on_the_calendar_only_after_the_yes(tmp_path, monkeypatch):
    reply = {"wake": "7:00", "bed": "4:00", "weekly": [{"what": "trash day", "day": "Tuesday", "time": ""},
                                                        {"what": "piano", "day": "Friday", "time": ""}], "morning": []}
    world, now = chips_for(tmp_path, monkeypatch, "routines", reply, "Up at seven, in bed by ten thirty", "Trash day is Tuesday", "no")
    assert [c["text"] for c in now["chips"]] == ["Up around 7:00", "Trash day, Tuesdays"]  # no 4:00, no piano
    before = len(world.calendar.all_events())
    user_sync.reply(world, "looks right")
    events = world.calendar.all_events()
    assert len(events) == before + 1 and events[-1].recurrence == "weekly"
    assert date.fromisoformat(events[-1].date).weekday() == 1


def test_a_named_split_becomes_the_plan_but_never_replaces_one(tmp_path, monkeypatch):
    reply = {"split": ["push", "pull", "legs"], "days": ["Monday", "Wednesday", "Friday"], "activities": [], "goal": "first pull-up"}
    world, now = chips_for(tmp_path, monkeypatch, "workouts", reply, "Push, pull, legs", "Monday, Wednesday and Friday", "My first pull-up")
    assert [c["text"] for c in now["chips"]] == ["Push, Pull, Legs, Mon, Wed, Fri", "First pull-up"]
    assert user_sync.reply(world, "looks right")["done"] is True
    assert [d["name"] for d in world.fitness.plan["training"]["rotation"]] == ["Push", "Pull", "Legs"]

    world, now = chips_for(tmp_path / "again", monkeypatch, "workouts", {**reply, "goal": ""}, "Push, pull, legs", "no", "no")
    world.fitness.update_plan({"training": {"rotation": [{"name": "Full body", "exercises": []}]}})
    assert user_sync._extract_workouts(world, [{"q": "", "a": "Push, pull, legs on Monday, Wednesday and Friday"}])[0]["text"] == "Mon, Wed, Fri"


def test_weekdays_can_be_a_span(tmp_path, monkeypatch):
    days = user_sync._days(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"], "Monday through Friday")
    assert len(days) == 5
    assert user_sync._days(["Monday", "Friday"], "just Fridays") == ["friday"]


def test_a_person_needs_a_year_for_a_real_birthday(tmp_path, monkeypatch):
    reply = {"people": [{"name": "Sarah", "who": "sister", "birthday": "March 4, 1990"},
                        {"name": "Mom", "who": "", "birthday": "June 2"}, {"name": "Elvis", "who": "friend", "birthday": ""}]}
    world, now = chips_for(tmp_path, monkeypatch, "people", reply, "My sister Sarah and my mom", "Sarah is March 4, 1990. Mom is June 2.")
    assert [c["text"] for c in now["chips"]] == ["Sarah, sister, March 4, 1990", "Mom, June 2"]
    user_sync.reply(world, "looks right")
    people = {p.name: p for p in world.relationships.all_people()}
    assert people["Sarah"].birthday == "1990-03-04" and not people["Mom"].birthday and "June 2" in people["Mom"].notes


def test_a_bill_needs_a_real_amount_and_day(tmp_path, monkeypatch):
    reply = {"saving_for": ["a van"], "bills": [{"name": "rent", "amount": "1200", "day": "1"}, {"name": "power", "amount": "90", "day": "9"}],
             "watch": ["takeout"]}
    world, now = chips_for(tmp_path, monkeypatch, "money", reply, "A van", "Rent is 1,200 on the 1st, and the power bill", "Takeout")
    assert [(c["app"], c["text"]) for c in now["chips"]] == [("Missions", "Save for a van"), ("Budget", "Rent"), ("Memory", "Power"), ("Memory", "Takeout")]
    user_sync.reply(world, "looks right")
    assert [b.name for b in world.budget.all_bills()] == ["Rent"]


def test_a_stray_brace_after_the_answer_doesnt_lose_it():
    assert user_sync._json_in('{"job": "nurse"}}') == {"job": "nurse"}
    assert user_sync._json_in('{"job": "nurse"') is None


def test_numbers_they_didnt_say_are_thrown_away():
    assert not user_sync._said("Monday to Friday, 9 to 5", "Monday to Friday, 8 to 5")
    assert user_sync._said("8 to 5", "usually 8 to 5")
    assert user_sync._time("7:00", "up at seven") and not user_sync._time("6:00", "up at seven")


def test_every_topic_has_sample_answers_and_a_fallback(tmp_path, monkeypatch):
    cases = json.loads((Path(__file__).parent.parent / "data" / "user_sync_cases.json").read_text(encoding="utf-8"))
    for topic in user_sync.TOPICS:
        assert len([c for c in cases if c["topic"] == topic]) >= 5
        assert user_sync.TOPICS[topic]["extract"](make(tmp_path / topic, monkeypatch, None, only=None), [{"q": "", "a": "x"}]) is None


def test_the_check_tool_marks_a_guess_as_wrong():
    chips = [{"kind": "recipe.add", "text": "Tacos"}, {"kind": "recipe.add", "text": "Soup"}]
    assert missing_and_extra(chips, {"recipes": ["taco"]}) == ([], ["Soup"])
    assert missing_and_extra([], {"memories": ["dairy"]}) == (["dairy"], [])


def test_the_sample_answers_are_well_formed():
    cases = json.loads((Path(__file__).parent.parent / "data" / "user_sync_cases.json").read_text(encoding="utf-8"))
    assert len(cases) >= 10
    assert all(len(c["answers"]) == len(user_sync.TOPICS[c["topic"]]["questions"]) for c in cases)
