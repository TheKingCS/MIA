"""Buffs (DEC-0028): good effects earned from what you really did, each
lasting a while and lifting one attribute by +1. Never debuffs."""

from datetime import date, timedelta

from core.buffs import buffs, nth_latest
from core.character_stats import character_stats
from tests.engine_world import build_world

TODAY = date(2026, 10, 17)


def ago(n: int) -> str:
    return (TODAY - timedelta(days=n)).isoformat()


def test_nth_latest():
    days = [TODAY - timedelta(days=n) for n in (0, 2, 5, 9)]
    assert nth_latest(days, 3, TODAY, 7) == TODAY - timedelta(days=5)
    assert nth_latest(days, 4, TODAY, 7) is None  # the fourth is outside the week
    assert nth_latest([None, TODAY + timedelta(days=1)], 1, TODAY, 7) is None  # never the future


def test_buffs_come_from_real_things_and_run_out(tmp_path, monkeypatch):
    world = build_world(tmp_path, monkeypatch)
    assert buffs(world, TODAY) == []  # nothing done, nothing shown: never a debuff
    for n in (1, 3, 6):
        world.workout.add_session(date_str=ago(n), duration_minutes=30)
    world.fitness.log_food("lunch", "Chicken bowl", on=TODAY.isoformat())
    debt = world.budget.add_debt("Card", 900, 20, 50)
    world.budget.record_debt_payment(debt.debt_id, 100, date=ago(2))
    asset = world.maintenance.add_asset("Mower", category="Lawn & Garden")
    world.maintenance.add_task(asset.asset_id, "Sharpen blade", interval_days=60, last_completed=ago(5))
    got = {b["key"]: b for b in buffs(world, TODAY)}
    assert set(got) == {"momentum", "well_fed", "debt_slayer", "prepared"}
    assert got["momentum"]["ends"] == TODAY.isoformat()  # 7 days from the third workout
    assert got["momentum"]["lasts"] == "ends today" and got["well_fed"]["lasts"] == "ends today"
    assert got["debt_slayer"]["why"] == "You landed a hit on Card." and got["debt_slayer"]["lasts"] == "4 more days"
    assert got["prepared"]["lasts"] == "while it holds"
    assert all(b["bonus"] == 1 for b in got.values())

    # A buff lifts its attribute by one, and says so.
    stats = {s["key"]: s for s in character_stats(world, world.me.profile_id, TODAY)}
    assert stats["strength"]["buffs"] == ["🔥 Momentum +1"]
    plain = {s["key"]: s for s in character_stats(world, world.me.profile_id, TODAY, active=[])}
    assert stats["strength"]["value"] == plain["strength"]["value"] + 1

    # A week later the week's buffs have run out; nothing is taken away beyond that.
    later = {b["key"] for b in buffs(world, TODAY + timedelta(days=8))}
    assert later <= {"prepared"}


def test_home_and_glasses_show_buffs(tmp_path, monkeypatch):
    from datetime import datetime

    from core.glasses import _character_buffs
    from core.web_surfaces import dashboard

    world = build_world(tmp_path, monkeypatch)
    world.fitness.log_food("lunch", "Chicken bowl")
    assert [b["key"] for b in dashboard(world, datetime.now())["buffs"]] == ["well_fed"]
    panel = _character_buffs(world, date.today())
    assert panel["lines"][0]["text"] == "🍲 Well Fed" and "+1 Vitality" in panel["lines"][0]["detail"]
