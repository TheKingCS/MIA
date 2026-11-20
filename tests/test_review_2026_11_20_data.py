"""Fable's review of Opus's work, 2026-11-20, batch B (data, sync, learning): an older phone's sync isn't ended by a
file that stays on one device now; the homestead's snapshots sync; a sync conflict's kept copy is sealed, never swept
into another undo, and its note quotes nothing; the daily budget is said once; a reset names one habit."""
from datetime import datetime, timedelta
from types import SimpleNamespace

from core import change_history, learned, retention, sync
from core.homeostasis import Homeostasis


def test_the_homesteads_snapshots_sync_and_device_files_dont():
    """A household store ingested only on the PC must reach the phone; pairing and usage stay where they are."""
    assert sync.syncable("homestead_snapshots.json") and retention.of("homestead_snapshots.json").cls == "record"
    assert not sync.syncable("phone_link.json") and not sync.syncable("module_usage.json")


def test_the_conflict_note_counts_and_quotes_no_field_or_value():
    """A path can hold his own words (a name used as a key), so the note says how many, never which."""
    note = sync.conflict_note("health.json", [("people", "Dr. Smith oncology", "phone"), ("people", "id=p2", "name")], True)
    assert note.startswith("health: 2 things changed on both devices; this device's was kept.")
    assert "Smith" not in note and "phone" not in note.split("kept.")[0] and "undo the sync conflict" in note


def test_a_list_without_ids_both_sides_changed_is_a_conflict_too():
    """Tags changed on both devices: one list loses whole, and that's noted."""
    with sync.conflicts() as lost:
        sync.merge_json({"tags": ["a"]}, {"tags": ["a", "b"]}, {"tags": ["c"]}, prefer_local=True)
    assert lost == [("tags",)]


def test_the_kept_copy_is_sealed_like_its_file_and_only_a_named_undo_finds_it(tmp_path, monkeypatch):
    """The losing copy is kept as the file is kept on disk, and "undo what you did" never sweeps it in."""
    monkeypatch.setattr(change_history, "folder_for", lambda pid: tmp_path / "history")
    sealed = []
    monkeypatch.setattr("core.at_rest.seal_text", lambda path, text: sealed.append(path.name) or f"SEALED({len(text)})")
    data = tmp_path / "user_memories.json"
    data.write_text("{}", encoding="utf-8")
    sync.keep_loser("p1", data, b'{"memories": []}', [("memories",)], local_won=True)
    assert sealed == ["user_memories.json"]
    start, end = datetime.now() - timedelta(hours=1), datetime.now() + timedelta(hours=1)
    assert change_history.find("p1", start, end) == []
    assert [e.label for e in change_history.find("p1", start, end, "the sync conflict")] == ["sync_conflict"]


def test_the_budgets_notice_is_said_once_a_day_in_its_own_words():
    """Twelve ticks over budget: one notice, about tomorrow, not about the computer being busy."""
    said = []
    clear = {"cpu": 10.0, "memory_free": 80.0, "battery": None, "online": True, "disk_free": 50.0}
    home = Homeostasis(SimpleNamespace(config=SimpleNamespace(get=lambda k, d=None: 1 if "budget" in k else d)),
                       read=lambda: clear)
    home._offer = lambda key, title, message: said.append((key, message))
    home.spend("night_school", 61)
    for _ in range(12):
        assert home.defer_reason("night_school") == "today's time for my own work is used up"
    assert len(said) == 1 and said[0][0] == "budget_spent" and "tomorrow" in said[0][1]


def test_words_that_fit_several_habits_reset_none(tmp_path):
    """"offer" fits every pace she learned; it must ask which, not reset the first."""
    import pytest

    from core.actions import ActionError

    two = [learned.Habit("pace:a", "I offer Good News up to 2 a day", "e", "r"),
           learned.Habit("pace:b", "I offer Tips up to 2 a day", "e", "r")]
    original = learned.habits
    learned.habits = lambda context: two
    try:
        with pytest.raises(ActionError):
            learned._find(None, {"habit": "offer"})
        assert learned._find(None, {"habit": "good news"}).habit_id == "pace:a"
        assert learned._find(None, {"habit_id": "pace:b"}).habit_id == "pace:b"
    finally:
        learned.habits = original
