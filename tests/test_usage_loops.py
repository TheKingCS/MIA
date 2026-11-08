"""Build plan step 3, the remaining usage loops (core/loops.py): numbers she didn't look up, memories
corrected soon after she kept them, the gate's daily limit and the kinds it put on a break, published
screens a later change broke, and data files found corrupt. Each record keeps kinds and counts, never words."""

from datetime import datetime, timedelta
from types import SimpleNamespace

from core import loops
from core.failure_log import FailureLog
from core.question_plans import Sheet, finish
from core.user_memory_manager import UserMemoryManager

BY_ID = {l.id: l for l in loops.LOOPS}


def ago(**kw) -> str:
    """The moment that long ago, as an ISO time to the second."""
    return (datetime.now() - timedelta(**kw)).isoformat(timespec="seconds")


def test_an_invented_number_is_noted_by_the_plan_only(tmp_path):
    book = FailureLog(None, data_dir=tmp_path)
    sheet = Sheet("money_left", "Money left")
    sheet.add("fact", "Left this month: 412")
    said = finish("You have about 900 left, and rent is 1,250.", sheet, "how much do I have left?",
                  SimpleNamespace(failures=book))
    assert "900" not in said
    events = book.events()
    assert [(e["kind"], e["tool"]) for e in events] == [("invented_number", "plan:money_left")]
    assert "900" not in str(events)
    turns = [{"at": ago(hours=1), "seconds": 2}] * 20
    person = SimpleNamespace(failures=book, traces=SimpleNamespace(recent=lambda n: turns))
    reading = BY_ID["answers.numbers"].measure(person)
    assert reading.value == 5.0 and loops.judge(BY_ID["answers.numbers"], reading, [])["state"] == "below"


def test_memories_corrected_soon_after_she_kept_them(tmp_path):
    store = UserMemoryManager(None, data_dir=tmp_path)
    kept = [store.add_memory(f"They like thing number {n}", category="Cooking") for n in range(5)]
    old = store.add_memory("They live near the coast", category="Other")
    old.created_at = ago(days=40)
    store.update_memory(kept[0].memory_id, "They like thing number zero")
    store.update_memory(kept[1].memory_id, kept[1].text)  # saved unchanged: not a correction
    store.delete_memory(kept[2].memory_id)
    store.delete_memory(old.memory_id)  # long kept: removing it judges nothing about her
    fixed = store.corrections()
    assert [c["how"] for c in fixed] == ["edited", "deleted"] and "thing" not in str(fixed)
    reading = BY_ID["memory.quality"].measure(SimpleNamespace(user_memories=store))
    assert (reading.value, reading.n) == (0.4, 5) and "Cooking 2" in reading.detail
    assert loops.judge(BY_ID["memory.quality"], reading, [])["state"] == "below"


def test_the_gate_hitting_its_limit_and_its_breaks():
    log = [{"at": ago(days=d), "action": "drop", "reason": "already said 5 things today (your limit is 5)"} for d in (1, 2, 3)]
    log += [{"at": ago(days=4), "action": "act", "reason": "passed"}]
    gate = SimpleNamespace(entries_since=lambda since: [e for e in log if e["at"] >= since],
                           paused=lambda: [{"topic": "insight_skill", "label": "x", "until": "2026-11-09"},
                                           {"topic": "finding_spend", "label": "y", "until": "2026-11-08"}])
    person = SimpleNamespace(communication=gate)
    full = BY_ID["gate.saturation"].measure(person)
    assert (full.value, full.n) == (3, 4) and loops.judge(BY_ID["gate.saturation"], full, [])["state"] == "below"
    assert BY_ID["gate.unwelcome"].measure(person).detail == "2 kinds on a break: finding_spend, insight_skill"


def test_a_published_screen_a_later_change_broke():
    good = {"kind": "screen", "title": "Plants", "icon": "greenhouse", "owner": "personal",
            "record_set": {"name": "Plants", "fields": [{"key": "name", "label": "Name", "type": "text"}]},
            "blocks": [{"type": "list", "set": "this", "show": ["name"]}]}
    broken = {"kind": "screen", "title": "Old", "colour": "red"}
    items = {"C-0001": good, "C-0002": broken}
    store = SimpleNamespace(published=lambda: [{"id": k} for k in items],
                            shown=lambda cid: {"spec": items[cid]})
    reading = BY_ID["creations.held"].measure(SimpleNamespace(creations=store))
    assert reading.n == 2 and reading.value >= 1  # the screen with a part that doesn't exist


def test_a_recovered_file_is_kept_by_name(tmp_path, monkeypatch):
    from core import data_recovery, dev_store

    monkeypatch.setattr(dev_store, "DEV_DATA", tmp_path)
    monkeypatch.setattr(loops, "DEV_DATA", tmp_path)
    monkeypatch.setattr(loops, "_has_repo", lambda: True)
    data_recovery.notify_data_corruption(SimpleNamespace(notifications=None), "user_memories.json")
    reading = BY_ID["data.recovered"].measure(None)
    assert reading.value == 1 and "user_memories.json" in reading.detail


def test_nothing_to_measure_is_none():
    nobody = SimpleNamespace()
    for loop_id in ("memory.quality", "gate.saturation", "gate.unwelcome", "creations.held"):
        assert BY_ID[loop_id].measure(nobody) is None
