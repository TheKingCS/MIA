"""Remembering at the right moment (DEC-0029, ALICE pick 3): a birthday,
a plan or due upkeep brings back what you told MIA, only when there's
something remembered to add."""

from datetime import date, timedelta

from core.memory_callbacks import as_message, callbacks
from core.relationships_manager import RelationshipsManager
from core.user_memory_manager import UserMemoryManager
from tests.engine_world import build_world

TODAY = date(2026, 10, 17)


def test_callbacks_bring_back_what_you_said(tmp_path, monkeypatch):
    w = build_world(tmp_path, monkeypatch)
    w.relationships = RelationshipsManager(w, data_dir=tmp_path / "rel")
    w.user_memories = UserMemoryManager(w, data_dir=tmp_path / "mem")
    assert callbacks(w, TODAY) == []

    in_a_week = (TODAY + timedelta(days=7)).replace(year=1994).isoformat()
    w.relationships.add_person(name="Jordan", birthday=in_a_week, gift_ideas="New chalk bag")
    w.relationships.add_person(name="Alex", birthday=(TODAY + timedelta(days=7)).replace(year=1990).isoformat())
    w.user_memories.add_memory("The user's friend Sam is vegetarian.")
    w.calendar.add_event("Dinner with Sam", (TODAY + timedelta(days=1)).isoformat())
    w.calendar.add_event("Dentist", (TODAY + timedelta(days=1)).isoformat())
    mower = w.maintenance.add_asset("Mower", category="Power Equipment")
    w.maintenance.add_task(mower.asset_id, "Sharpen blades", interval_days=30,
                           last_completed=(TODAY - timedelta(days=29)).isoformat(), notes="Use the 7/8 socket")
    w.maintenance.add_task(mower.asset_id, "Check oil", interval_days=30, last_completed=(TODAY - timedelta(days=29)).isoformat())

    got = {c["title"]: c for c in callbacks(w, TODAY)}
    assert set(got) == {"Jordan's birthday is in 7 days (turning 32)", "Tomorrow: Dinner with Sam", "Sharpen blades: Mower is due tomorrow"}
    assert got["Tomorrow: Dinner with Sam"]["lines"] == ["You told me: your friend Sam is vegetarian."]
    assert as_message(got["Jordan's birthday is in 7 days (turning 32)"]) == \
        "Jordan's birthday is in 7 days (turning 32). Gift ideas you noted: New chalk bag."
    assert got["Sharpen blades: Mower is due tomorrow"]["lines"] == ["Your note: Use the 7/8 socket"]
    # Nothing on days in between: it's a reminder at the right moment, not a nag.
    assert not any("Jordan" in c["title"] for c in callbacks(w, TODAY + timedelta(days=2)))

    from datetime import datetime

    from core.web_surfaces import dashboard

    assert [r["icon"] for r in dashboard(w, datetime(2026, 10, 17, 9))["remember"]] == ["📅", "🔧", "🎂"]


def test_second_person():
    from core.memory_callbacks import second_person

    assert second_person("The user's sister Jordan loves climbing.") == "your sister Jordan loves climbing."
    assert second_person("The user is training for a half marathon.") == "you are training for a half marathon."
