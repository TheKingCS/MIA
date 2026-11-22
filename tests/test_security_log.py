"""
tests.test_security_log
=========================

The security log (core/security_log.py, docs/SECURITY.md step 3): devices said
in words, events kept per account newest first, never a password; a sign-in
from a new device and repeated wrong passwords alert the account's owner; and
"sign out everywhere" ends every other session; a password or email changed on this
computer is logged too, a changed email alerting the owner; and (WP-05) each line is chained
to the one before by its hash, so a changed, removed or added line breaks the chain, a log rewritten whole no
longer holds the head another device kept, the trim is a line of its own and never in the undo log, and a key
problem met while the log is held is recorded after.
"""

from core import security_log as sl


def test_devices_are_said_in_words_with_their_address():
    """The browser's description becomes a kind of device; the address follows."""
    assert sl.device_of("Mozilla/5.0 (Linux; Android 14) Chrome/120", "100.64.0.7") == "Android phone · 100.64.0.7"
    assert sl.device_of("Mozilla/5.0 (Windows NT 10.0) Edg/120", "127.0.0.1") == "Edge on Windows · 127.0.0.1"
    assert sl.device_of("", "") == "A device"


def test_events_are_kept_per_account_newest_first_and_known_devices_remembered(tmp_path):
    """Two accounts' events don't mix; a device counts as known after a sign-in from it."""
    book = sl.SecurityLog(tmp_path)
    book.record("sign_in", "p1", "Android phone · 1.2.3.4")
    book.record("sign_in_failed", "p2", "Edge on Windows · 5.6.7.8")
    book.record("password_changed", "p1", "Android phone · 1.2.3.4")
    mine = book.for_person("p1")
    assert [e["kind"] for e in mine] == ["password_changed", "sign_in"] and mine[0]["what"] == "Password changed"
    assert book.known_device("p1", "Android phone · 1.2.3.4") and not book.known_device("p2", "Android phone · 1.2.3.4")


def test_a_damaged_line_is_skipped_and_the_log_is_cut_back_when_long(tmp_path, monkeypatch):
    """A bad line doesn't stop reading; past twice KEEP lines, the log is cut back to the newest KEEP, the trim noted
    as a line of its own (WP-05), and what's kept still checks as a chain."""
    monkeypatch.setattr(sl, "KEEP", 3)
    book = sl.SecurityLog(tmp_path)
    book.path.write_text("not json\n", encoding="utf-8")
    for i in range(7):
        book.record("sign_in", "p1", f"device {i}")
    # Past 6 lines it was cut to the newest 3 (devices 3 to 5), the trim noted; device 6 came after.
    assert [e.get("device") or e["kind"] for e in book.entries()] == ["device 3", "device 4", "device 5", "log_trimmed",
                                                                      "device 6"]
    assert book.verify()["ok"] and book.verify()["chained"] == 5


def test_a_password_or_email_changed_on_this_computer_is_logged_and_a_new_email_alerts(tmp_path):
    """The listener writes a desktop change to the log as "this computer"; a changed sign-in email also tells the
    owner at once; a change its caller logs itself (the web, with the device) isn't written twice."""
    from types import SimpleNamespace

    sent = []
    notes = SimpleNamespace(notify=lambda title, message, **kw: sent.append(title))
    context = SimpleNamespace(security_log=sl.SecurityLog(tmp_path), notifications=notes)
    import core.personal_data as pd

    real = pd.view_for
    pd.view_for = lambda ctx, pid: ctx
    try:
        sl.on_account_change(context, "password_changed")(profile_id="p1")
        sl.on_account_change(context, "email_changed")(profile_id="p1")
        with sl.logged_by_caller():
            sl.on_account_change(context, "password_changed")(profile_id="p1")
    finally:
        pd.view_for = real
    kinds = [(e["kind"], e["device"]) for e in context.security_log.for_person("p1")]
    assert kinds == [("email_changed", "this computer"), ("password_changed", "this computer")]
    assert sent == ["Your MIA sign-in email changed"]


def test_each_line_is_chained_to_the_one_before_and_the_chain_checks(tmp_path):
    """WP-05: every line holds the previous line's hash and its own; an untouched log checks out, its head the newest."""
    book = sl.SecurityLog(tmp_path)
    first = book.record("sign_in", "p1", "phone")
    second = book.record("sign_out", "p1", "phone")
    assert first["prev"] == "" and second["prev"] == first["h"] and second["h"] == sl.digest(second)
    found = book.verify()
    assert found["ok"] and found["chained"] == 2 and found["head"]["h"] == second["h"] and book.holds(first["h"])


def _lines(book):
    """The log's lines, each sealed one opened."""
    from core.at_rest import open_text

    return [x for x in open_text(book.path).splitlines() if x.strip()]


def _write(book, lines):
    """Writes the log's lines back plain (as someone with the file would)."""
    book.path.write_text("".join(x + chr(10) for x in lines), encoding="utf-8")


def test_a_changed_removed_or_added_line_breaks_the_chain(tmp_path):
    """Changing what a line says, taking one out, or slipping one in each shows, at the line where it happened."""
    import json

    book = sl.SecurityLog(tmp_path)
    for device in ("phone", "laptop", "tablet"):
        book.record("sign_in", "p1", device)
    lines = _lines(book)
    changed = json.loads(lines[1])
    changed["device"] = "someone else's laptop"
    _write(book, [lines[0], json.dumps(changed), lines[2]])
    assert book.verify()["broken"]["why"] == "a line changed after it was written"
    _write(book, [lines[0], lines[2]])
    assert book.verify()["broken"] == {"line": 2, "at": json.loads(lines[2])["at"],
                                       "why": "a line removed or put in before this one"}
    forged = sl.link({"at": "2026-01-01T00:00:00", "kind": "sign_in", "profile_id": "p1"}, json.loads(lines[0])["h"])
    _write(book, [lines[0], json.dumps(forged), lines[1], lines[2]])
    assert not book.verify()["ok"]


def test_lines_from_before_the_chain_are_counted_and_the_chain_starts_after_them(tmp_path):
    """A log from before WP-05 keeps reading; its old lines come first and aren't checked, the new ones are."""
    book = sl.SecurityLog(tmp_path)
    book.path.write_text('{"at": "2026-11-01T00:00:00", "kind": "sign_in", "profile_id": "p1"}' + chr(10), encoding="utf-8")
    book.record("sign_in", "p1", "phone")
    found = book.verify()
    assert found["ok"] and (found["before_chain"], found["chained"]) == (1, 1)


def test_a_log_rewritten_whole_no_longer_holds_the_head_another_device_kept(tmp_path):
    """A chain rewritten from scratch checks out on its own, which is why another device keeps the head."""
    import json

    book = sl.SecurityLog(tmp_path)
    book.record("sign_in", "p1", "phone")
    kept = book.record("sign_in", "p1", "stranger's laptop")["h"]
    first = json.loads(_lines(book)[0])
    _write(book, [json.dumps(sl.link(first, ""))])
    assert book.verify()["ok"] and not book.holds(kept)


def test_a_key_problem_met_while_the_log_is_being_written_is_recorded_after(tmp_path, monkeypatch):
    """The key's lock and the log's are never waited on in the opposite order (WP-05): a key problem found while this
    thread holds the log's lock is noted, then recorded once it's let go, chained like any other line."""
    from core import at_rest

    monkeypatch.setattr(sl, "_DATA_DIR", tmp_path)
    book = sl.SecurityLog(tmp_path)
    with book._holding():
        at_rest._alert("data_key_unopened")
        assert sl.writing() and not book.path.exists()
    at_rest.flush_alerts()
    assert [e["kind"] for e in book.entries()] == ["data_key_unopened"] and book.verify()["ok"]


def test_the_trim_never_goes_through_the_undo_log(tmp_path, monkeypatch):
    """"Undo that" can't put back or take away security lines: the trim writes the file itself."""
    import core.atomic_write as aw

    monkeypatch.setattr(sl, "KEEP", 2)
    called = []
    monkeypatch.setattr(aw, "atomic_write_text", lambda *a, **k: called.append(a))
    book = sl.SecurityLog(tmp_path)
    for i in range(6):
        book.record("sign_in", "p1", f"device {i}")
    assert called == [] and "log_trimmed" in [e["kind"] for e in book.entries()]
    import inspect

    assert "atomic_write_text(" not in inspect.getsource(sl)
