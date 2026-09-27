"""The encrypted private journal (core/private_journal.py)."""

import pytest

import core.private_journal as pj
from types import SimpleNamespace

from core.private_journal import (
    JournalExchange, JournalLockedError, PrivateJournalEntry, PrivateJournalManager,
)
from core.secrets_manager import SecretsError

PASS = "correct horse battery"


@pytest.fixture
def journal_files(tmp_path, monkeypatch):
    monkeypatch.setattr(pj, "_DATA_DIR", tmp_path)
    monkeypatch.setattr(pj, "_KEYS_FILE", tmp_path / "private_journal_keys.json")
    monkeypatch.setattr(pj, "_ENTRIES_FILE", tmp_path / "private_journal.json")
    monkeypatch.setattr(pj, "_RSA_KEY_SIZE", 2048)  # speed; production uses 3072
    return tmp_path


def _manager():
    return PrivateJournalManager(SimpleNamespace(notifications=None))


def _entry(entry_id="s1", text="Work dragged today and I kept thinking about the greenhouse."):
    return PrivateJournalEntry(
        entry_id=entry_id, title="Long shift", mood="drained", themes=["work", "greenhouse"],
        summary="You talked about a long shift.", exchanges=[JournalExchange("user", text, "2026-09-27T17:00:00")],
    )


def test_not_set_up(journal_files):
    journal = _manager()
    assert not journal.is_set_up() and not journal.is_unlocked()
    with pytest.raises(SecretsError):
        journal.save_entry(_entry())


def test_short_passphrase_refused(journal_files):
    with pytest.raises(SecretsError):
        _manager().setup("short")


def test_setup_unlocks_and_round_trips(journal_files):
    journal = _manager()
    journal.setup(PASS)
    journal.save_entry(_entry())
    [entry] = journal.all_entries()
    assert entry.title == "Long shift" and entry.themes == ["work", "greenhouse"] and "greenhouse" in entry.user_text


def test_nothing_readable_on_disk(journal_files):
    journal = _manager()
    journal.setup(PASS)
    journal.save_entry(_entry(text="my secret words about the factory"))
    raw = (journal_files / "private_journal.json").read_text() + (journal_files / "private_journal_keys.json").read_text()
    for word in ("secret words", "factory", "Long shift", "drained", PASS):
        assert word not in raw


def test_writes_while_locked_reads_only_after_unlock(journal_files):
    _manager().setup(PASS)
    journal = _manager()  # a fresh run: set up, locked
    assert journal.is_set_up() and not journal.is_unlocked()
    journal.save_entry(_entry("a"))
    journal.save_entry(_entry("b"))
    assert journal.entry_count() == 2
    with pytest.raises(JournalLockedError):
        journal.all_entries()
    with pytest.raises(SecretsError):
        journal.unlock("wrong passphrase")
    assert not journal.verify_passphrase("wrong passphrase") and journal.verify_passphrase(PASS)
    journal.unlock(PASS)
    assert {e.entry_id for e in journal.all_entries()} == {"a", "b"}
    journal.lock()
    assert not journal.is_unlocked()


def test_save_replaces_by_id_and_delete(journal_files):
    journal = _manager()
    journal.setup(PASS)
    journal.save_entry(_entry("a"))
    journal.save_entry(_entry("a", text="updated"))
    assert journal.entry_count() == 1 and journal.all_entries()[0].user_text == "updated"
    assert journal.delete_entry("a") and not journal.delete_entry("a")
    assert journal.entry_count() == 0


def test_search(journal_files):
    journal = _manager()
    journal.setup(PASS)
    journal.save_entry(_entry("a"))
    paid = _entry("b", text="Paid off the Chase card, felt amazing")
    paid.themes = ["debt"]
    journal.save_entry(paid)
    assert [e.entry_id for e in journal.search("chase card")] == ["b"]
    assert [e.entry_id for e in journal.search("greenhouses")] == ["a"]
    assert len(journal.search("")) == 2


def test_setup_twice_refused(journal_files):
    journal = _manager()
    journal.setup(PASS)
    with pytest.raises(SecretsError):
        journal.setup(PASS)
