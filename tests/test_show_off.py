"""Show-off mode (DEC-0031): a tour of MIA on the real profile that never
shows money, the journal, memories, health or other people."""

import json
from datetime import date, timedelta

from core.show_off import tour, wants_show_off
from tests.engine_world import build_world


def test_the_trigger():
    assert wants_show_off("MIA, show off for my friends")
    assert wants_show_off("can you do demo mode") and wants_show_off("Showoff!")
    assert not wants_show_off("what's on my calendar") and not wants_show_off("the show was great")


def test_the_tour_hides_private_things(tmp_path, monkeypatch):
    from core.journal_manager import JournalManager
    from core.relationships_manager import RelationshipsManager
    from core.user_memory_manager import UserMemoryManager

    w = build_world(tmp_path, monkeypatch)
    today = date.today()
    w.user_memories = UserMemoryManager(w, data_dir=tmp_path / "mem")
    w.user_memories.add_memory("The user's secret plan is ZEBRA-MEMORY.")
    w.journal = JournalManager(w, data_dir=tmp_path / "j")
    w.journal.add_entry("ZEBRA-JOURNAL feelings")
    w.relationships = RelationshipsManager(w, data_dir=tmp_path / "rel")
    w.relationships.add_person(name="ZebraFriend", birthday=(today + timedelta(days=1)).replace(year=1990).isoformat())
    debt = w.budget.add_debt("ZebraCard", 900, 20, 50)
    w.budget.record_debt_payment(debt.debt_id, 100)
    w.fitness.log_weight(181.5)
    w.fitness.log_food("lunch", "ZebraSandwich")
    for n in range(3):
        w.workout.add_session(date_str=(today - timedelta(days=n)).isoformat(), duration_minutes=30)
    mower = w.maintenance.add_asset("Mower", category="Power Equipment")
    w.maintenance.add_task(mower.asset_id, "Sharpen blades", interval_days=60, last_completed=today.isoformat())

    t = tour(w, today)
    keys = [s["key"] for s in t["steps"]]
    assert keys[0] == "hello" and keys[-1] == "finale" and "gear" in keys and "buffs" in keys
    dumped = json.dumps(t)
    for secret in ("ZEBRA", "Zebra", "181", "$"):
        assert secret not in dumped, secret
    buffs = next(s for s in t["steps"] if s["key"] == "buffs")["buffs"]
    assert {b["name"] for b in buffs} == {"Momentum", "Prepared"}  # never Debt Slayer or Well Fed


def test_saying_it_opens_the_tour(tmp_path, monkeypatch):
    from core.assistant_turn import run_assistant_turn
    from core.conversation_manager import Conversation

    w = build_world(tmp_path, monkeypatch)
    w.llm = None
    turn = run_assistant_turn(w, Conversation(conversation_id="c", title="t"), "MIA, show off for my friends")
    assert turn.open == "showoff.html" and turn.replies == ["Let's show them what I can do. Opening the tour."]
