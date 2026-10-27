"""The Dungeon (DEC-0046): work as a dungeon you loot every day. Runs and
their loot, overtime bosses, projected and banked loot, the hard-mode
record, and the Game Master's quests."""

from datetime import date, timedelta

import pytest

from tests.test_crafting import do, shop  # noqa: F401  (the fixture)


@pytest.fixture
def work(shop):  # noqa: F811
    from core.work_dungeon import DungeonBook

    shop.dungeon = DungeonBook(shop, data_dir=shop.my_dir)
    return shop


def _monday_weeks_ago(weeks: int) -> date:
    t = date.today()
    return t - timedelta(days=t.weekday() + 7 * weeks)


def test_overtime_is_what_the_week_holds_past_forty():
    from core.work_dungeon import Dungeon, Run, boss_bonus, loot, split_hours

    d = Dungeon("d1", "Work", hourly=20, overtime_after=40)
    monday = date(2026, 10, 19)
    runs = [Run(f"r{i}", "d1", (monday + timedelta(days=i)).isoformat(), 9) for i in range(5)]
    split = split_hours(d, runs)
    assert [split[f"r{i}"] for i in range(5)] == [(9, 0), (9, 0), (9, 0), (9, 0), (4, 5)]
    assert loot(d, 40, 5) == 950 and boss_bonus(d, 5) == 50
    # A Sunday pay week: Monday to Friday sits in one week either way, a Sunday run starts a new one.
    sunday = Run("r5", "d1", (monday + timedelta(days=6)).isoformat(), 8)
    assert split_hours(Dungeon("d1", "Work", hourly=20, week_starts="Sunday"), runs + [sunday])["r5"] == (8, 0)
    assert split_hours(d, runs + [sunday])["r5"] == (0, 8)
    # Planned runs only in a projection, and after the day's cleared ones.
    planned = Run("p", "d1", (monday + timedelta(days=5)).isoformat(), 8, status="planned")
    assert "p" not in split_hours(d, runs + [planned])
    assert split_hours(d, runs + [planned], include_planned=True)["p"] == (0, 8)


def test_the_game_master_hears_the_hard_mode_in_plain_words():
    from core.work_dungeon import detect_affixes, parse_affixes, run_xp, take_home_share, Dungeon

    assert detect_affixes("2nd shift left us unstocked again and they never do their job") == ["unstocked"]
    assert detect_affixes("we were short staffed and the line broke down") == ["short_staffed", "breakdown"]
    assert detect_affixes("good day") == []
    assert parse_affixes("Bare Shelves, short staffed, the forklift was hidden") == [
        "unstocked", "short_staffed", "the forklift was hidden"]
    assert run_xp(8, ["unstocked"], boss=True) == 10 + 8 + 6 + 15
    d = Dungeon("d", "Work")
    assert take_home_share(d, banked=780, earned=1000) == (0.78, "your deposits")
    assert take_home_share(d, banked=5000, earned=1000) == (None, "")  # not a paycheck's share: never guessed
    d.take_home_pct = 72
    assert take_home_share(d, 0, 0) == (0.72, "your number")


def test_a_hard_mode_week_end_to_end(work):
    from core.region import money
    from core.web_dungeon import dungeon_page

    w = work
    do(w, "dungeon.add", name="The warehouse", hourly=20, payer="ACME PAYROLL")
    monday = _monday_weeks_ago(1)
    p = do(w, "dungeon.run", date=monday.isoformat(), hours=9, hard_mode="unstocked")
    assert "hard mode (Bare Shelves)" in p.summary and money(180) in p.summary
    xp_before = w.profiles.get_active_profile().total_xp
    for i in range(1, 4):
        do(w, "dungeon.run", date=(monday + timedelta(days=i)).isoformat(), hours=9)
    boss = do(w, "dungeon.run", date=(monday + timedelta(days=4)).isoformat(), hours=9, hard_mode="short staffed")
    assert "5 h overtime: boss bonus " + money(50) in boss.summary
    assert w.profiles.get_active_profile().total_xp > xp_before

    w.budget.add_income(amount=700, category="Salary", description="ACME PAYROLL DIR DEP",
                        date=(monday + timedelta(days=11)).isoformat() if monday + timedelta(days=11) <= date.today()
                        else date.today().isoformat())
    w.budget.add_income(amount=40, category="Other", description="Marketplace sale", date=date.today().isoformat())

    page = dungeon_page(w, today=monday + timedelta(days=4))
    v = page["dungeons"][0]
    assert v["week"]["earned"] == 950 and v["week"]["overtime"] == 5
    assert v["week"]["bonus_text"] == money(50)
    assert v["overtime_now"]["in_overtime"] is True and v["overtime_now"]["hour_text"] == money(30)
    record = {x["id"]: x for x in v["hard_mode"]}
    assert record["unstocked"]["dates"] == [monday.isoformat()] and record["unstocked"]["name"] == "Bare Shelves"
    assert record["short_staffed"]["real"] == "short-staffed"
    assert v["runs"][0]["boss"] is True and v["runs"][0]["xp"] == 10 + 9 + 6 + 15

    later = dungeon_page(w, today=date.today())["dungeons"][0]
    assert later["banked"]["last_30"] == 700  # the marketplace sale isn't a paycheck
    assert later["pace"]["weekly"] == 950 and later["pace"]["yearly_text"] == money(950 * 52)


def test_planned_runs_are_projected_loot(work):
    from core.region import money
    from core.web_dungeon import dungeon_page

    w = work
    do(w, "dungeon.add", name="Work", hourly=25, overtime_after=40, shift_hours=10)
    soon = date.today() + timedelta(days=1)
    plan = do(w, "dungeon.plan", date=soon.isoformat(), overtime="yes")
    assert plan.summary.startswith("Plan an overtime boss at Work") and money(250) in plan.summary
    v = dungeon_page(w)["dungeons"][0]
    assert v["planned"][0]["date"] == soon.isoformat() and v["planned"][0]["boss"] is True
    if soon <= date.fromisoformat(v["week"]["end"]):
        assert v["week"]["projected"] == 250 + v["week"]["earned"]
    # Clearing that day picks up the planned run instead of adding another.
    do(w, "dungeon.run", date=soon.isoformat(), hours=11, hard_mode="Swarm")
    runs = w.dungeon.runs
    assert len(runs) == 1 and runs[0].status == "cleared" and runs[0].hours == 11 and runs[0].affixes == ["rush"]
    with pytest.raises(Exception, match="That day's gone"):
        do(w, "dungeon.plan", date=(date.today() - timedelta(days=1)).isoformat())


def test_the_game_master_turns_it_into_a_quest(work):
    w = work
    p = do(w, "dungeon.quest", challenge="2nd shift left us unstocked")
    assert p.summary.startswith("A new quest, “Hard Mode: Bare Shelves”")
    m = next(x for x in w.missions.all_missions() if x.name == "Hard Mode: Bare Shelves")
    assert m.difficulty == "HARD" and m.assigned_by == "mia" and m.objectives and m.reward_xp == 31
    do(w, "dungeon.quest", challenge="the printer jams every morning")
    assert any(x.name == "Side Quest: the printer jams every morning" for x in w.missions.all_missions())


def test_money_stays_with_grown_ups():
    from core.child_accounts import CHILD_APPS, CHILD_BLOCKED_DOMAINS
    from core.personal_data import PERSONAL_STORES

    assert "dungeon" in CHILD_BLOCKED_DOMAINS and "dungeon" not in CHILD_APPS
    assert "dungeon" in dict(PERSONAL_STORES)


def test_game_master_mode_is_asked_for_and_gets_its_facts_from_code(work):
    from core.assistant_chat import build_personal_system_message
    from core.conversation_modes import GAME_MASTER, detect_mode_change, looks_like_direct_command
    from core.region import money
    from core.support_choice import QUESTION, interpret_answer

    assert detect_mode_change("2nd shift left us unstocked again. GM this").mode == GAME_MASTER
    assert detect_mode_change("make it a game").mode == GAME_MASTER
    assert detect_mode_change("just listen").mode != GAME_MASTER
    assert looks_like_direct_command("yes, make it a quest") and looks_like_direct_command("I worked 9 hours today")
    assert "Game Master" in QUESTION and interpret_answer("the game one") == GAME_MASTER
    assert interpret_answer("the last one") == GAME_MASTER and interpret_answer("remind me why") != GAME_MASTER

    w = work
    system = build_personal_system_message(w, GAME_MASTER, prompt="2nd shift left us unstocked again")
    assert "Bare Shelves" in system and "never villains" in system and "isn't set up" in system
    do(w, "dungeon.add", name="The warehouse", hourly=20)
    do(w, "dungeon.run", hours=8, hard_mode="unstocked")
    system = build_personal_system_message(w, GAME_MASTER, prompt="they left us unstocked AGAIN")
    assert "this month so far: 1" in system and money(160) in system and "isn't set up" not in system


def test_the_dungeon_by_voice(work):
    from core.assistant_dungeon_actions import _get_loot, _log_shift, _plan_shift, _start_quest, _when

    w = work
    assert "Apps → The Dungeon" in _get_loot(w, {})
    do(w, "dungeon.add", name="Work", hourly=20)
    assert _log_shift(w, {"hours": 9, "hard_mode": "we were unstocked"}).startswith("Run cleared: +")
    assert "9 hours" in _get_loot(w, {})
    assert _start_quest(w, {}).startswith("Quest accepted: Hard Mode: Bare Shelves")
    assert _plan_shift(w, {"day": "tomorrow", "overtime": True}) == "On the schedule."
    assert _when("yesterday", False) == (date.today() - timedelta(days=1)).isoformat()
    assert date.fromisoformat(_when("saturday", True)).weekday() == 5
