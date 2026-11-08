"""
tests.test_at_rest
====================

MIA's most private files sealed at rest (DEC-0126, core/at_rest.py): a sealed name is written as an AES-256-GCM
envelope and read back, any other file stays plain; a plain file still reads (each store moves at its next save); a
file that won't open is copied aside before the error, so a store starting empty can't lose it (and every sealed
store starts empty rather than stopping MIA; every file naming a sealed file reads it with open_text); a changed file is
refused; a recovery key brings a key back; sync and export carry the real content; and, on Windows, the key is
protected by DPAPI and only opens for this Windows user.
"""

import json
import sys
import zipfile

from unittest.mock import MagicMock

import pytest

from core import at_rest
from core.atomic_write import atomic_write_text
from core.conversation_manager import ConversationManager
from core.user_memory_manager import UserMemoryManager

KEY = bytes(range(32))


@pytest.fixture(autouse=True)
def test_key(tmp_path, monkeypatch):
    """Each test seals with the suite's test key and keeps its key file in its own folder."""
    monkeypatch.setattr(at_rest, "KEY_DIR", tmp_path / ".keys")
    at_rest.use_key(KEY)
    yield
    at_rest.use_key(KEY)


def test_a_sealed_name_is_written_sealed_and_reads_back_while_others_stay_plain(tmp_path):
    """conversations.json on disk is an envelope with no trace of its words; notes.json is untouched."""
    secret, plain = tmp_path / "conversations.json", tmp_path / "notes.json"
    atomic_write_text(secret, json.dumps({"said": "my bank is Lakeside"}))
    atomic_write_text(plain, json.dumps({"said": "buy milk"}))
    on_disk = secret.read_text(encoding="utf-8")
    assert on_disk.startswith(at_rest.PREFIX) and "Lakeside" not in on_disk
    assert json.loads(at_rest.open_text(secret)) == {"said": "my bank is Lakeside"}
    assert "buy milk" in plain.read_text(encoding="utf-8") and at_rest.open_text(plain) == plain.read_text("utf-8")


def test_the_stores_read_their_old_plain_files_and_seal_them_at_the_next_save(tmp_path):
    """A plain user_memories.json from before DEC-0126 loads; the store's next save seals it."""
    (tmp_path / "user_memories.json").write_text(json.dumps([]), encoding="utf-8")
    store = UserMemoryManager(MagicMock(), data_dir=tmp_path)
    assert store.all_memories() == []
    store.add_memory("Their sister is called Rowan")
    on_disk = (tmp_path / "user_memories.json").read_text(encoding="utf-8")
    assert at_rest.is_sealed(on_disk) and "Rowan" not in on_disk
    assert [m.text for m in UserMemoryManager(MagicMock(), data_dir=tmp_path).all_memories()] == [
        "Their sister is called Rowan"]


def test_a_conversation_store_round_trips_through_its_sealed_file(tmp_path):
    """Saved and loaded again by a fresh store, the same conversations."""
    store = ConversationManager(MagicMock(), data_dir=tmp_path)
    talk = store.create_conversation()
    store.add_message(talk.conversation_id, "user", "I owe Dana forty dollars")
    on_disk = (tmp_path / "conversations.json").read_text(encoding="utf-8")
    assert at_rest.is_sealed(on_disk) and "Dana" not in on_disk
    again = ConversationManager(MagicMock(), data_dir=tmp_path).get_conversation(talk.conversation_id)
    assert again.messages[-1].content == "I owe Dana forty dollars"


def test_a_file_whose_key_is_gone_is_copied_aside_before_the_error(tmp_path):
    """Sealed with one key, opened with another: UnreadableFile, and a byte-for-byte copy kept beside it."""
    path = tmp_path / "life_notes.json"
    atomic_write_text(path, '{"notes": []}')
    before = path.read_bytes()
    at_rest.use_key(bytes(32))
    with pytest.raises(at_rest.UnreadableFile) as caught:
        at_rest.open_text(path)
    assert caught.value.aside.read_bytes() == before and "isn't held" in str(caught.value)


def test_a_changed_sealed_file_is_refused_not_misread(tmp_path):
    """One character of the ciphertext changed: GCM refuses it."""
    path = tmp_path / "journal_entries.json"
    atomic_write_text(path, "[]")
    text = path.read_text(encoding="utf-8")
    flipped = text[:-6] + ("A" if text[-6] != "A" else "B") + text[-5:]
    path.write_text(flipped, encoding="utf-8")
    with pytest.raises(at_rest.UnreadableFile) as caught:
        at_rest.open_text(path)
    assert "changed or damaged" in str(caught.value)


def test_sealing_twice_doesn_t_wrap_an_envelope_in_another(tmp_path):
    """Undo writes a file's old bytes back; a sealed text given to seal comes back as it is."""
    once = at_rest.seal("hello")
    assert at_rest.seal(once) == once and at_rest.unseal(once) == "hello"


def test_the_recovery_key_brings_the_key_back_and_old_files_open(tmp_path):
    """Written out in groups of five and taken back (any case, any spaces): the same key id, the old file opens."""
    path = tmp_path / "conversations.json"
    atomic_write_text(path, "[1, 2]")
    code = at_rest.recovery_key()
    assert all(len(g) <= 5 for g in code.split("-"))
    at_rest.use_key(bytes(32))  # another key, as on a reinstalled Windows
    assert at_rest.restore(code.lower().replace("-", " ")) == at_rest._kid(KEY)
    assert at_rest.open_text(path) == "[1, 2]"
    with pytest.raises(ValueError):
        at_rest.restore("not a key")


def test_sync_and_export_carry_the_real_content(tmp_path):
    """open_bytes gives a sealed file's content (so both sides hash and merge the same thing); plain bytes pass."""
    path, other = tmp_path / "conversations.json", tmp_path / "kitchen.json"
    atomic_write_text(path, '{"a": 1}')
    other.write_bytes(b'{"b": 2}')
    assert at_rest.open_bytes(path) == b'{"a": 1}' and at_rest.open_bytes(other) == b'{"b": 2}'


def test_the_account_export_holds_readable_files(tmp_path):
    """The export's _add writes a sealed file's content into the zip, and copies any other file."""
    from core.account_data import _add

    sealed, plain = tmp_path / "conversations.json", tmp_path / "workouts.json"
    atomic_write_text(sealed, '{"talk": "hi"}')
    plain.write_text("[]", encoding="utf-8")
    out = tmp_path / "export.zip"
    with zipfile.ZipFile(out, "w") as archive:
        _add(archive, sealed, "personal/conversations.json")
        _add(archive, plain, "personal/workouts.json")
    with zipfile.ZipFile(out) as archive:
        assert archive.read("personal/conversations.json") == b'{"talk": "hi"}'
        assert archive.read("personal/workouts.json") == b"[]"


def test_seal_now_seals_the_plain_ones_and_leaves_the_rest(tmp_path):
    """Two plain sealed-kind files and one other: two sealed, the other untouched; again, none."""
    for name in ("conversations.json", "life_notes.json", "kitchen.json"):
        (tmp_path / name).write_text("{}", encoding="utf-8")
    assert at_rest.seal_now([tmp_path]) == 2
    assert (tmp_path / "kitchen.json").read_text(encoding="utf-8") == "{}"
    assert at_rest.seal_now([tmp_path]) == 0


@pytest.mark.skipif(sys.platform != "win32", reason="DPAPI is Windows'")
def test_on_windows_the_key_file_holds_only_a_dpapi_protected_key(tmp_path):
    """The real path: a key made, written protected (the raw key nowhere in the file), opened again after forget."""
    at_rest.use_key(None)
    path = tmp_path / "conversations.json"
    atomic_write_text(path, '"kept"')
    record = json.loads(at_rest.key_file().read_text(encoding="utf-8"))
    at_rest.forget()
    assert at_rest.open_text(path) == '"kept"'
    raw = at_rest._key_for(record["current"])
    assert raw is not None and raw.hex() not in at_rest.key_file().read_text(encoding="utf-8")
    assert at_rest.status()["protection"] == "dpapi"


@pytest.mark.skipif(sys.platform != "win32", reason="DPAPI is Windows'")
def test_a_key_file_that_won_t_open_is_never_replaced(tmp_path):
    """A key file this Windows user can't open: sealing stops, files are written plain, the key file stays."""
    at_rest.use_key(None)
    at_rest.KEY_DIR.mkdir(parents=True)
    at_rest.key_file().write_text(json.dumps({"v": 1, "current": "abcd1234", "keys": [
        {"id": "abcd1234", "blob": "bm90IGEgZHBhcGkgYmxvYg=="}]}), encoding="utf-8")
    before = at_rest.key_file().read_text(encoding="utf-8")
    path = tmp_path / "conversations.json"
    atomic_write_text(path, "[]")
    assert path.read_text(encoding="utf-8") == "[]" and not at_rest.status()["sealing"]
    assert at_rest.key_file().read_text(encoding="utf-8") == before


SEALED_STORES = [
    ("core.conversation_manager", "ConversationManager", "conversations.json"),
    ("core.journal_manager", "JournalManager", "journal_entries.json"),
    ("core.user_memory_manager", "UserMemoryManager", "user_memories.json"),
    ("core.life_notes", "LifeNotes", "life_notes.json"),
    ("core.relationships_manager", "RelationshipsManager", "relationships_people.json"),
    ("core.relationships_manager", "RelationshipsManager", "relationships_pets.json"),
    ("core.finance_manager", "FinanceManager", "financial_snapshots.json"),
    ("core.insurance", "InsuranceBook", "insurance.json"),
    ("core.gps_tracks", "GpsTracks", "gps_tracks.json"),
    ("core.operating_journal", "OperatingJournal", "operating_journal.json"),
    ("core.turn_trace", "TurnTraces", "turn_traces.jsonl"),
    ("core.health_manager", "HealthStore", "health.json"),
    ("core.id_wallet", "IdWallet", "id_wallet.json"),
    ("core.intent_manager", "IntentManager", "intents.json"),
    ("core.communication_gate", "CommunicationGate", "communication_log.json"),
    ("core.freedom", "FreedomLog", "freedom_log.json"),
    ("core.recreation", "RecreationLog", "recreation.json"),
    ("core.paths", "PathBook", "paths.json"),
    ("core.browser_routines", "BrowserRoutines", "browser_routines.json"),
    ("core.living_worlds", "LivingWorldsBook", "living_worlds.json"),
    ("core.response_style", "StyleBook", "response_styles.json"),
    ("core.direction", "DirectionBook", "directions.json"),
    ("core.connections", "ConnectionBook", "connections.json"),
]


def test_every_sealed_name_has_its_store_here():
    """SEALED and this list agree, so each sealed file's store is tested below."""
    assert {name for _, _, name in SEALED_STORES} == set(at_rest.SEALED)


@pytest.mark.parametrize("module, cls, name", SEALED_STORES)
def test_a_sealed_store_whose_file_won_t_open_starts_empty_and_keeps_a_copy(tmp_path, module, cls, name):
    """Sealed under a key that's gone: the store loads (MIA still starts), and the file's copy is set aside."""
    import importlib

    at_rest.use_key(bytes(32))
    atomic_write_text(tmp_path / name, "[]")
    before = (tmp_path / name).read_bytes()
    at_rest.use_key(KEY)
    store_class = getattr(importlib.import_module(module), cls)
    store_class(MagicMock(), data_dir=tmp_path)
    [aside] = tmp_path.glob(name + ".unreadable-*")
    assert aside.read_bytes() == before


def test_every_file_that_names_a_sealed_file_reads_it_with_open_text():
    """A core, server or tools file with a sealed name in it and a read_text or json.load must use open_text (or be one
    of the few that only list names), so no reader is left behind when a name joins SEALED."""
    from pathlib import Path

    root = Path(at_rest.__file__).resolve().parent.parent
    lists_only = {"core/at_rest.py", "core/personal_data.py", "core/sync.py", "core/account_data.py",
                  "core/conversation_modes.py", "core/talk_it_out.py"}
    missing = []
    for folder in ("core", "server", "tools", "modules", "gui"):
        for path in (root / folder).rglob("*.py"):
            rel = path.relative_to(root).as_posix()
            text = path.read_text(encoding="utf-8")
            if rel in lists_only or not any(f'"{n}"' in text for n in at_rest.SEALED):
                continue
            if ("read_text" in text or "json.load(" in text) and "open_text" not in text:
                missing.append(rel)
    assert not missing, missing
