"""The development history on this PC (DEC-0077, core/dev_store.py): kept
whole, kept small, found without loading it."""

import gzip
import json

from core.dev_store import DevIndex, DevStore, _fts_query


def test_full_segments_are_compressed_and_nothing_is_lost(tmp_path):
    store = DevStore(tmp_path / "council", segment_bytes=2_000)
    for n in range(200):
        store.append({"at": f"2026-11-04T10:{n // 60:02d}:{n % 60:02d}+00:00", "who": "claude", "text": f"message {n} " + "x" * 40})
    closed = sorted(p.name for p in (tmp_path / "council").glob("*.gz"))
    assert len(closed) >= 3 and len(list((tmp_path / "council").glob("*.jsonl"))) == 1  # one open, the rest packed
    with gzip.open(tmp_path / "council" / closed[0], "rt", encoding="utf-8") as f:
        assert json.loads(f.readline())["text"].startswith("message 0 ")
    assert [r["text"].split()[1] for r in store.records()] == [str(n) for n in range(200)]  # whole, in order
    assert [r["text"].split()[1] for r in store.tail(3)] == ["197", "198", "199"]
    assert len(store.tail(150)) == 150 and store.tail(150)[0]["text"].startswith("message 50 ")  # across segments
    plain = sum(len(json.dumps(r)) + 1 for r in store.records())
    assert store.size() < plain / 2  # smaller on disk than the text it keeps


def test_a_new_month_starts_a_new_segment(tmp_path):
    store = DevStore(tmp_path / "usage")
    store.append({"at": "2026-11-30T23:00:00+00:00", "provider": "codex"})
    _, where = store.append({"at": "2026-12-01T00:10:00+00:00", "provider": "codex"})
    assert (tmp_path / "usage" / "0001.jsonl.gz").exists() and where == "seg:usage/0002:0"


def test_a_stop_between_packing_and_removing_loses_nothing(tmp_path):
    store = DevStore(tmp_path / "c", segment_bytes=10**9)
    store.append({"text": "kept"})
    store._close("0001")
    (tmp_path / "c" / "0001.jsonl").write_text('{"text": "kept"}\n', encoding="utf-8")  # as if the delete never ran
    store.append({"text": "next"})
    assert [r["text"] for r in store.records()] == ["kept", "next"]


def test_one_search_over_the_pc_and_the_repo_without_a_second_copy(tmp_path):
    store = DevStore(tmp_path / "council", segment_bytes=1_500)
    for n in range(60):
        store.append({"who": "codex", "text": f"note {n} about the relay" if n == 7 else f"note {n} on other things " + "y" * 30})
    activity = tmp_path / "activity.jsonl"
    activity.write_text(json.dumps({"at": "2026-11-03T15:00:00+00:00", "who": "QA Engineer (ollama-coder)",
                                    "action": "review", "task": "T-0019", "detail": "changes: _WINDOWS_DEFAULT unused"}) + "\n",
                        encoding="utf-8")
    index = DevIndex(tmp_path / "index.sqlite", stores={"council": store}, files={"activity": activity})
    try:
        hits = index.search("what about the relay?")
        assert [h["text"] for h in hits] == ["note 7 about the relay"] and hits[0]["source"] == "council"
        assert index.search("WINDOWS_DEFAULT")[0]["task"] == "T-0019"  # the repo's own record, read where it is
        store.append({"who": "zac", "text": "and the relay again"})
        with open(activity, "a", encoding="utf-8") as f:
            f.write(json.dumps({"who": "claude", "action": "note", "task": "T-0020", "detail": "relay checked"}) + "\n")
        assert len(index.search("relay")) == 3  # only what's new is read
        assert index.search('" ) ( * ^ :') == [] and index.search("") == []  # words, never query syntax
        assert all("1" in h["text"].split() for h in index.search('" OR 1=1')) # "1" searched as a word
        assert b"note 7 about the relay" not in index.path.read_bytes()  # positions, not a second copy of the text
    finally:
        index.close()
    again = DevIndex(tmp_path / "index.sqlite", stores={"council": store}, files={"activity": activity})
    try:
        assert len(again.search("relay")) == 3  # nothing indexed twice on reopening
    finally:
        again.close()


def test_the_query_is_only_quoted_words():
    assert _fts_query('relay "AND" NEAR(x) -y* relay') == '"relay" OR "near" OR "x" OR "-y"'
    assert _fts_query("what is the") == ""
