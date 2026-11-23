"""Every personal store sealed (WP-04, DEC-0126): each record, log or derived file in the retention registry is sealed
whole (SEALED), sealed a line at a time (LINE_SEALED), not anyone's (PUBLIC, with why), or listed as not sealed yet
with why (NOT_SEALED_YET), a list that may only shrink, or kept as no file at all (NO_FILE). A sealed store reads through open_text; a line-sealed log is
appended through seal_line; sync's
last-synced copy of a sealed file is sealed too."""
import re
from pathlib import Path

from core import at_rest, retention

ROOT = Path(__file__).resolve().parent.parent
NOT_SEALED_YET_MOST = 7  # 2026-11-20: lower it as stores are sealed; it may never rise


def test_every_personal_store_is_sealed_or_said_why_not():
    """A new personal file can't slip in unsealed: it's sealed, public with why, waiting with why, or a name no
    store keeps as a file."""
    accounted = set(at_rest.SEALED) | set(at_rest.LINE_SEALED) | set(at_rest.PUBLIC) | set(at_rest.NOT_SEALED_YET) | \
        set(at_rest.NO_FILE)
    personal = {n for n, r in retention.REGISTRY.items() if r.cls in ("record", "log", "derived")}
    assert sorted(personal - accounted) == []
    assert all(why.strip() for why in list(at_rest.NOT_SEALED_YET.values()) + list(at_rest.PUBLIC.values()))
    assert not set(at_rest.NOT_SEALED_YET) & (set(at_rest.SEALED) | set(at_rest.PUBLIC))


def test_the_not_sealed_list_only_shrinks():
    """Sealing a store takes its name off; nothing is added to the list."""
    assert len(at_rest.NOT_SEALED_YET) <= NOT_SEALED_YET_MOST


def test_each_sealed_store_reads_through_open_text():
    """A module that names a SEALED file reads files through open_text (or open_bytes, open_lines): a store that read
    it plainly would see the sealed envelope, not its records. The registries that name every file (at_rest itself,
    retention...) don't count as its reader (Fable's review, 2026-11-22: at_rest alone made every name pass)."""
    sources = {p: p.read_text(encoding="utf-8") for p in list((ROOT / "core").glob("*.py"))}
    registries = {"at_rest.py", "retention.py", "your_data.py", "personal_data.py", "app_ecosystem.py"}
    for name in at_rest.SEALED:
        mods = [p.name for p, text in sources.items() if f'"{name}"' in text and p.name not in registries]
        readers = [m for m in mods if re.search(r"open_text\(|open_bytes\(|open_lines\(",
                                                 sources[ROOT / "core" / m])]
        assert readers, f"{name}: no module that names it reads through open_text"


def test_each_line_sealed_log_is_written_through_seal_line():
    """A module that appends to a LINE_SEALED log seals each line (seal_line): one that wrote plain lines would leave
    the log readable on disk."""
    sources = {p: p.read_text(encoding="utf-8") for p in list((ROOT / "core").glob("*.py"))}
    for name in at_rest.LINE_SEALED - {"life_events.jsonl"}:
        writers = [p.name for p, text in sources.items() if name in text and p.name not in ("at_rest.py", "retention.py",
                                                                                             "your_data.py")]
        assert writers and all("seal_line(" in sources[ROOT / "core" / w] for w in writers), name


def test_an_appended_log_is_sealed_line_by_line_and_older_plain_lines_still_read(tmp_path, monkeypatch):
    """The security log's new lines are sealed on disk, its older plain lines still read, and a trim keeps them all
    sealed."""
    from core import security_log

    monkeypatch.setattr(security_log, "KEEP", 3)
    path = tmp_path / "security_log.jsonl"
    path.write_text('{"at": "2026-01-01T00:00:00", "kind": "sign_in", "profile_id": "p1"}\n', encoding="utf-8")
    book = security_log.SecurityLog(tmp_path)
    book.record("sign_in", "p1", device="phone")
    lines = [x for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert not at_rest.is_sealed(lines[0]) and at_rest.is_sealed(lines[1]) and "phone" not in lines[1]
    assert [e["profile_id"] for e in book.entries()] == ["p1", "p1"]
    for _ in range(2 * security_log.KEEP):
        book.record("sign_in", "p1")
    kept = [x for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(kept) <= 2 * security_log.KEEP and all(at_rest.is_sealed(x) for x in kept)


def test_a_name_with_no_file_is_written_by_no_store():
    """NO_FILE holds only names nothing writes: a store that began writing one would need it sealed or said why."""
    for path in (ROOT / "core").glob("*.py"):
        text = path.read_text(encoding="utf-8")
        for name in at_rest.NO_FILE:
            for line in text.splitlines():
                if f'"{name}"' in line:
                    assert not re.search(r"atomic_write_text\(|write_text\(|write_bytes\(", line), (path.name, name)


def test_sync_keeps_a_sealed_file_s_last_synced_copy_sealed(tmp_path):
    """The copy sync keeps of each file as it was last synced holds the same records, so it's sealed like the file."""
    from core.sync import SyncState

    state = SyncState(tmp_path)
    state.set_base("home", "missions.json", b'[{"name": "Fix fence"}]')
    state.set_base("home", "readings.json", b'[{"v": 1}]')
    assert at_rest.is_sealed((tmp_path / "home" / "missions.json").read_text(encoding="utf-8"))
    assert state.base("home", "missions.json") == b'[{"name": "Fix fence"}]'
    assert (tmp_path / "home" / "readings.json").read_bytes() == b'[{"v": 1}]'
    state.set_game({"total_xp": 40})
    assert at_rest.is_sealed((tmp_path / "game.json").read_text(encoding="utf-8")) and state.game() == {"total_xp": 40}
