"""Every personal store sealed (WP-04, DEC-0126): each record, log or derived file in the retention registry is sealed
whole (SEALED), sealed a line at a time (LINE_SEALED), not anyone's (PUBLIC, with why), or listed as not sealed yet
with why (NOT_SEALED_YET), a list that may only shrink. A sealed store reads through open_text; a line-sealed log is
appended through seal_line."""
import re
from pathlib import Path

from core import at_rest, retention

ROOT = Path(__file__).resolve().parent.parent
NOT_SEALED_YET_MOST = 38  # 2026-11-20: lower it as stores are sealed; it may never rise


def test_every_personal_store_is_sealed_or_said_why_not():
    """A new personal file can't slip in unsealed: it's sealed, public with why, or waiting with why."""
    accounted = set(at_rest.SEALED) | set(at_rest.LINE_SEALED) | set(at_rest.PUBLIC) | set(at_rest.NOT_SEALED_YET)
    personal = {n for n, r in retention.REGISTRY.items() if r.cls in ("record", "log", "derived")}
    assert sorted(personal - accounted) == []
    assert all(why.strip() for why in list(at_rest.NOT_SEALED_YET.values()) + list(at_rest.PUBLIC.values()))
    assert not set(at_rest.NOT_SEALED_YET) & (set(at_rest.SEALED) | set(at_rest.PUBLIC))


def test_the_not_sealed_list_only_shrinks():
    """Sealing a store takes its name off; nothing is added to the list."""
    assert len(at_rest.NOT_SEALED_YET) <= NOT_SEALED_YET_MOST


def test_each_sealed_store_reads_through_open_text():
    """A module that names a SEALED file reads files through open_text (or open_bytes, open_lines): a store that read
    it plainly would see the sealed envelope, not its records."""
    sources = {p: p.read_text(encoding="utf-8") for p in list((ROOT / "core").glob("*.py"))}
    for name in at_rest.SEALED:
        mods = [p.name for p, text in sources.items() if f'"{name}"' in text]
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
