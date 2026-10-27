"""The Loop (DEC-0047): what recurs gets a rhythm by itself, MIA learns
its days and times (yours always win), plans the week's runs, reminds you
at the time, and a missed day shows honestly as the share cleared."""

from datetime import date, datetime, timedelta

import pytest

from tests.test_crafting import do, shop  # noqa: F401  (the fixture)


@pytest.fixture
def life(shop):  # noqa: F811
    from core.notification_manager import NotificationManager
    from core.the_loop import LoopBook
    from core.work_dungeon import DungeonBook

    shop.dungeon = DungeonBook(shop, data_dir=shop.my_dir)
    shop.loop = LoopBook(shop, data_dir=shop.my_dir)
    shop.notifications = NotificationManager(shop, data_dir=shop.my_dir)
    return shop


def test_clocks_days_and_the_night_shift():
    from core.the_loop import (clock_text, days_text, parse_clock, parse_days, span_hours, typical_minute,
                               usual_days, work_day)

    assert parse_clock("9:30 pm") == "21:30" and parse_clock("6 AM") == "06:00" and parse_clock("2:30pm") == "14:30"
    assert parse_clock("noon") == "12:00" and clock_text("21:30") == "9:30 PM" and clock_text("00:05") == "12:05 AM"
    with pytest.raises(ValueError):
        parse_clock("13 pm")
    assert span_hours("21:30", "06:00") == 8.5 and span_hours("14:30", "16:00") == 1.5
    assert parse_days("sun-thu") == [0, 1, 2, 3, 6] and days_text([0, 1, 2, 3, 6]) == "Sun–Thu"
    assert parse_days("weekdays") == [0, 1, 2, 3, 4] and days_text([0, 1, 2, 3, 4]) == "Mon–Fri"
    assert parse_days("mon, wed and fri") == [0, 2, 4] and days_text([0, 2, 4]) == "Mon, Wed, Fri"
    # 11:55 PM and 12:05 AM are usually midnight, not noon.
    assert typical_minute([23 * 60 + 55, 5]) == 0
    monday = date(2026, 10, 26)
    weeks = [monday - timedelta(days=7 * k) for k in range(1, 5)]
    seen = [w + timedelta(days=i) for w in weeks for i in (0, 1, 2, 3)] + [weeks[0] + timedelta(days=5)]
    assert usual_days(seen, monday) == [0, 1, 2, 3]  # one odd Saturday isn't a habit
    # Clearing a 9:30 PM – 6 AM run at 6:10 AM counts for the night it started.
    assert work_day("21:30", "06:00", [6, 0, 1, 2, 3], datetime(2026, 10, 27, 6, 10)) == date(2026, 10, 26)
    assert work_day("21:30", "06:00", [6, 0, 1, 2, 3], datetime(2026, 10, 27, 14, 0)) == date(2026, 10, 27)
    assert work_day("09:00", "17:00", [0, 1, 2, 3, 4], datetime(2026, 10, 27, 3, 0)) == date(2026, 10, 27)


def test_work_gets_a_rhythm_by_itself_and_learns_from_cleared_runs(life):
    from core.the_loop import ensure_rhythms, learn

    w = life
    do(w, "dungeon.add", name="The plant", hourly=20)
    ensure_rhythms(w)
    r = w.loop.find("work", w.dungeon.dungeons[0].dungeon_id)
    assert r is not None and r.name == "The plant" and r.lead_minutes == 30
    d = w.dungeon.dungeons[0]
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    for k in range(1, 5):
        for i in (0, 1, 2, 3, 6):  # Sun–Thu nights
            day = monday - timedelta(days=7 * k) + timedelta(days=i)
            run = w.dungeon.add_run(d.dungeon_id, day.isoformat(), 8.5)
            run.created_at = datetime.combine(day + timedelta(days=1), datetime.min.time()).replace(hour=6, minute=5).isoformat()
    w.dungeon._save()
    learn(w, today)
    assert r.days == [0, 1, 2, 3, 6] and r.days_source == "learned"
    assert (r.start, r.end) == ("21:35", "06:05") and r.start_source == "learned"
    # What you say wins, and learning never overwrites it.
    do(w, "loop.set", name="work", start="9:30 pm", end="6 am")
    learn(w, today)
    assert (r.start, r.end, r.start_source) == ("21:30", "06:00", "yours")
    do(w, "loop.forget", name="work", what="times")
    learn(w, today)
    assert r.start_source == "learned"


def test_the_weeks_runs_are_planned_once_and_never_brought_back(life):
    from core.the_loop import plan_week, week

    w = life
    do(w, "dungeon.add", name="Work", hourly=20)
    do(w, "loop.set", name="work", days="every day", start="9:30 pm", end="6 am")
    d = w.dungeon.dungeons[0]
    planned = [r for r in w.dungeon.runs if r.status == "planned"]
    assert len(planned) == 8 and all(r.hours == 8.5 for r in planned)
    removed = planned[1]
    w.dungeon.delete_run(removed.run_id)
    assert plan_week(w) == 0 and not any(r.date == removed.date for r in w.dungeon.runs)
    row = week(w)["rows"][0]
    assert row["name"] == "Work" and row["scheduled"] >= 1
    assert d.dungeon_id == w.loop.rhythms[0].ref


def test_a_missed_day_shows_honestly(life):
    from core.region import money
    from core.the_loop import week

    w = life
    do(w, "dungeon.add", name="Work", hourly=20)
    do(w, "loop.set", name="work", days="every day", start="9:30 pm", end="6 am")
    r = w.loop.rhythms[0]
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    r.created_at = (monday - timedelta(days=7)).isoformat() + "T00:00:00"
    sunday = monday + timedelta(days=6)
    w.dungeon.add_run(w.dungeon.dungeons[0].dungeon_id, (monday if today != monday else sunday).isoformat(), 8.5)
    view = week(w, sunday)
    row = view["rows"][0]
    cleared = [c for c in row["cells"] if c["status"] == "cleared"]
    missed = [c for c in row["cells"] if c["status"] == "missed"]
    assert len(cleared) == 1 and cleared[0]["text"] == money(170)
    assert missed and all(c["text"] == money(0) for c in missed)
    # On Sunday the whole week is past: the score is cleared out of every scheduled day.
    assert row["to_go"] == 1 and row["so_far"] == row["scheduled"] - 1 and row["pct"] == round(100 / row["so_far"])


def test_reminders_go_out_at_the_time_once(life):
    from core.the_loop import tick

    w = life
    do(w, "dungeon.add", name="Work", hourly=20)
    do(w, "loop.set", name="work", days="every day", start="9:30 pm", end="6 am")
    today = date.today()
    early = datetime.combine(today, datetime.min.time()).replace(hour=20, minute=30)
    assert tick(w, early) == 0
    at = early.replace(hour=21, minute=5)  # 30 minutes' lead for work
    assert tick(w, at) == 1 and tick(w, at.replace(minute=20)) == 0
    note = next(n for n in w.notifications.list_all() if n.source == "loop")
    assert "opens at 9:30 PM until 6:00 AM: a 8.5-hour run, about" in note.message and "loot" in note.message


def test_chores_and_your_own_rhythms(life):
    from core.the_loop import ensure_rhythms, reminders

    w = life
    w.recurring_missions.add_template(name="Feed the animals", objective_description_template="Feed ({target:g}x)",
                                      base_target=1, target_increment_per_week=0, daily_reward_xp=5,
                                      weekly_bonus_reward_xp=10, start_date=date.today().isoformat(), category="Household")
    ensure_rhythms(w)
    chores = w.loop.find("routine", "Household")
    assert chores is not None and chores.days == list(range(7))
    do(w, "loop.set", name="chores", start="2:30 pm")
    for t in w.recurring_missions.all_templates():
        w.recurring_missions.ensure_current_missions(t, date.today())
    at = datetime.combine(date.today(), datetime.min.time()).replace(hour=14, minute=20)
    said = reminders(w, at)
    assert said and "1 to do today (Feed the animals)" in said[0][2]
    do(w, "loop.set", name="Evening walk", days="every day", start="7 pm", lead_minutes=0)
    assert w.loop.rhythms[-1].kind == "custom"
    with pytest.raises(Exception, match="comes back by itself"):
        do(w, "loop.delete", name="chores")
    do(w, "loop.delete", name="Evening walk")
    assert all(r.name != "Evening walk" for r in w.loop.rhythms)


def test_a_night_run_cleared_after_midnight_is_the_night_before(life, monkeypatch):
    import core.the_loop as the_loop

    w = life
    do(w, "dungeon.add", name="Work", hourly=20)
    do(w, "loop.set", name="work", days="every day", start="9:30 pm", end="6 am")
    yesterday = date.today() - timedelta(days=1)
    monkeypatch.setattr(the_loop, "work_day", lambda *a, **k: yesterday)
    do(w, "dungeon.run", hours=8.5)
    assert any(r.date == yesterday.isoformat() and r.status == "cleared" for r in w.dungeon.runs)


def test_the_loop_by_voice(life):
    from core.assistant_dungeon_actions import _get_loop, _set_schedule

    w = life
    assert "Nothing in your loop yet" in _get_loop(w, {})
    do(w, "dungeon.add", name="The plant", hourly=20)
    said = _set_schedule(w, {"name": "work", "days": "sun-thu", "start": "9:30 pm", "end": "6 am"})
    assert said == "Got it. MIA will remind you 30 min before."
    assert "The plant: Sun–Thu · 9:30 PM – 6:00 AM" in _get_loop(w, {})
    assert "isn't a time" in _set_schedule(w, {"name": "work", "start": "half past nine-ish"})
