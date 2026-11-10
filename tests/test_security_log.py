"""
tests.test_security_log
=========================

The security log (core/security_log.py, docs/SECURITY.md step 3): devices said
in words, events kept per account newest first, never a password; a sign-in
from a new device and repeated wrong passwords alert the account's owner; and
"sign out everywhere" ends every other session; a password or email changed on this
computer is logged too, a changed email alerting the owner.
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
    """A bad line doesn't stop reading; past twice KEEP lines, the log is cut back to the newest KEEP."""
    monkeypatch.setattr(sl, "KEEP", 3)
    book = sl.SecurityLog(tmp_path)
    book.path.write_text("not json\n", encoding="utf-8")
    for i in range(7):
        book.record("sign_in", "p1", f"device {i}")
    # Past 6 lines it was cut to the newest 3 (devices 3 to 5); device 6 came after.
    assert [e["device"] for e in book.entries()] == ["device 3", "device 4", "device 5", "device 6"]


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
