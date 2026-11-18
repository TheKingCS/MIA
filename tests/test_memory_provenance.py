"""
tests.test_memory_provenance
==============================

LS-02 (DEC-0281, Prompt 21): his memories say how they're known (where they came from, how, when he confirmed them,
when they hold), older ones read as unknown rather than guessed, and the history and links declare the same contract;
and Q-112's one-time removal on the phone of the PC's own files that had synced there.
"""

from __future__ import annotations

from types import SimpleNamespace

from core.user_memory_manager import UserMemory, UserMemoryManager


def _store(tmp_path):
    """A memory store in a temp folder."""
    return UserMemoryManager(SimpleNamespace(config=None), data_dir=tmp_path)


def test_a_memory_kept_on_his_yes_says_where_it_came_from_and_when_he_confirmed_it(tmp_path):
    store = _store(tmp_path)
    kept = store.add_memory("The coop door is 32 inches wide", source="card", confirmed=True)
    assert kept.source == "card" and kept.how == "said" and kept.confirmed_at
    again = _store(tmp_path).get_memory(kept.memory_id)  # survives a reload
    assert again.source == "card" and again.confirmed_at == kept.confirmed_at


def test_a_memory_from_a_conversation_names_it_and_is_not_confirmed_until_he_says_so(tmp_path):
    kept = _store(tmp_path).add_memory("Prefers mornings for outside work", source_conversation_id="c42")
    assert kept.source == "conversation:c42" and kept.confirmed_at == "" and kept.how == "said"


def test_an_older_memory_reads_as_unknown_and_said_never_guessed():
    old = UserMemory.from_dict({"memory_id": "m1", "text": "Lives near the river", "created_at": "2026-01-01T09:00:00"})
    assert old.source == "" and old.how == "said" and old.confirmed_at == "" and old.holds_until == ""


def test_an_unknown_way_of_knowing_falls_back_to_said(tmp_path):
    assert _store(tmp_path).add_memory("Something else", how="guessed").how == "said"


def test_his_memories_the_history_and_links_declare_how_they_are_known():
    from core.life_events import LifeEventLog
    from core.links import LinkStore

    for store in (UserMemoryManager, LifeEventLog, LinkStore):
        assert {"record", "source", "at", "how"} <= set(store.EPISTEMIC)


def test_the_phone_removes_the_pcs_own_files_once_and_keeps_its_own(tmp_path):
    from core.atomic_write import prev_path
    from core.sync import PC_ONLY, remove_pc_only_copies

    folder = tmp_path / "p1"
    folder.mkdir()
    for name in PC_ONLY + ("runs.json", "user_memories.json"):
        (folder / name).write_text("{}", encoding="utf-8")
    prev_path(folder / "activity.json").write_text("{}", encoding="utf-8")
    gone = remove_pc_only_copies(tmp_path)
    assert sorted(p.name for p in gone) == sorted(list(PC_ONLY) + [".activity.json.prev"])
    assert (folder / "runs.json").exists() and (folder / "user_memories.json").exists()
    assert remove_pc_only_copies(tmp_path) == [] and remove_pc_only_copies(tmp_path / "missing") == []
