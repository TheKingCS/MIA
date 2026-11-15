"""
tests.test_key_unlock
=======================

MIA's data key on Linux (DEC-0126's Linux step; core/key_unlock.py, core/at_rest.py): where there's no DPAPI the
data key is wrapped under an unlock secret that systemd keeps for this user on this machine. Checked here, with
stand-ins for systemd so it runs on any system: the key file holds only the wrapped key and opens again with the
secret; without the secret (or with another) it's locked and never replaced; a key file from Windows is kept as it
is while the recovery key adds this system's own entry beside it, and Windows still opens its own entry in a file
Linux has added to; a MIA with no window doesn't start over sealed files she can't open; the secret is read from
the service's credential folder or opened by systemd-creds, a cut-off one refused; making the secret never
replaces one that's there and removes one that doesn't read back; and the command-line tool's `protect` and
`restore`.
"""

import json
import subprocess
import sys

import pytest

from core import at_rest, key_unlock
from core.atomic_write import atomic_write_text
from tools import data_key

KEY = bytes(range(32))
SECRET = b"s" * 64


@pytest.fixture(autouse=True)
def own_key_file(tmp_path, monkeypatch):
    """Each test has its own key file, a quick scrypt, and goes back to the suite's test key after."""
    monkeypatch.setattr(at_rest, "KEY_DIR", tmp_path / ".keys")
    monkeypatch.setattr(at_rest, "SCRYPT", {"n": 2 ** 10, "r": 8, "p": 1})
    monkeypatch.setattr(at_rest, "_alert", lambda kind: None)
    yield
    at_rest.use_key(KEY)


@pytest.fixture
def linux(monkeypatch):
    """A system with no DPAPI whose unlock secret is SECRET; set `held["secret"]` to change or remove it."""
    held = {"secret": SECRET, "why": "no unlock secret has been made"}
    monkeypatch.setattr(at_rest, "dpapi_available", lambda: False)
    monkeypatch.setattr(at_rest, "_unlock_secret",
                        lambda: (held["secret"], "" if held["secret"] else held["why"]))
    at_rest.use_key(None)
    return held


def _recovery_of(key: bytes) -> str:
    """The recovery key a person would have kept for `key`."""
    at_rest.use_key(key)
    code = at_rest.recovery_key()
    at_rest.use_key(None)
    return code


def test_on_linux_the_key_file_holds_only_a_wrapped_key_that_opens_again_with_the_secret(tmp_path, linux):
    path = tmp_path / "conversations.json"
    atomic_write_text(path, '"kept"')
    text = at_rest.key_file().read_text(encoding="utf-8")
    record = json.loads(text)
    assert at_rest.is_sealed(path.read_text(encoding="utf-8"))
    assert record["keys"][0]["by"] == "secret" and at_rest.status()["protection"] == "secret"
    at_rest.forget()
    assert at_rest.open_text(path) == '"kept"'
    raw = at_rest._key_for(record["current"])
    assert raw.hex() not in text and SECRET.decode() not in text


def test_without_the_secret_an_existing_key_is_locked_and_its_file_is_never_replaced(tmp_path, linux):
    path = tmp_path / "conversations.json"
    atomic_write_text(path, '"kept"')
    before = at_rest.key_file().read_text(encoding="utf-8")
    for other in (None, b"another secret entirely, long enough"):
        linux["secret"] = other
        at_rest.forget()
        assert not at_rest.status()["sealing"] and at_rest.status()["why_not"]
        with pytest.raises(at_rest.UnreadableFile):
            at_rest.open_text(path)
        assert at_rest.key_file().read_text(encoding="utf-8") == before
        assert "can't be opened here" in at_rest.start_problem([tmp_path])
    linux["secret"] = SECRET
    at_rest.forget()
    assert at_rest.open_text(path) == '"kept"' and at_rest.start_problem([tmp_path]) == ""


def test_with_no_secret_and_no_key_nothing_is_sealed_and_no_key_file_is_made(tmp_path, linux):
    linux["secret"] = None
    at_rest.forget()
    path = tmp_path / "conversations.json"
    atomic_write_text(path, "[]")
    assert path.read_text(encoding="utf-8") == "[]" and not at_rest.key_file().exists()
    assert "files stay plain" in at_rest.status()["why_not"] and at_rest.start_problem([tmp_path]) == ""
    with pytest.raises(ValueError, match="nothing here protects"):
        at_rest.restore(_recovery_of(KEY))


def test_a_changed_wrapped_entry_is_refused(linux):
    entry = at_rest._wrap(KEY, SECRET)
    assert at_rest._unwrap(entry, SECRET) == KEY
    with pytest.raises(ValueError):
        at_rest._unwrap({**entry, "id": "00000000"}, SECRET)
    with pytest.raises(ValueError):
        at_rest._unwrap(entry, SECRET + b"x")


def test_the_recovery_key_opens_windows_files_on_linux_and_keeps_the_windows_entry(tmp_path, linux):
    """Data copied from the PC: files sealed under the PC's key, and a key file holding only its DPAPI entry."""
    at_rest.use_key(KEY)
    path = tmp_path / "conversations.json"
    atomic_write_text(path, '"from the PC"')
    code = at_rest.recovery_key()
    windows_entry = {"id": at_rest._kid(KEY), "blob": "bm90IGEgZHBhcGkgYmxvYg=="}
    at_rest.KEY_DIR.mkdir(parents=True)
    at_rest.key_file().write_text(json.dumps({"v": 1, "protection": "dpapi", "current": windows_entry["id"],
                                              "keys": [windows_entry]}), encoding="utf-8")
    before = at_rest.key_file().read_text(encoding="utf-8")
    at_rest.use_key(None)
    assert not at_rest.status()["sealing"] and "recovery key" in at_rest.start_problem([tmp_path])
    assert at_rest.key_file().read_text(encoding="utf-8") == before  # never replaced by a new key
    at_rest.forget()
    assert at_rest.restore(code) == windows_entry["id"]
    at_rest.forget()
    assert at_rest.open_text(path) == '"from the PC"' and at_rest.start_problem([tmp_path]) == ""
    kept = json.loads(at_rest.key_file().read_text(encoding="utf-8"))["keys"]
    assert windows_entry in kept and [e["by"] for e in kept if "by" in e] == ["secret"]


def test_files_copied_without_their_key_file_stop_a_start_until_the_recovery_key_is_entered(tmp_path, linux):
    at_rest.use_key(KEY)
    atomic_write_text(tmp_path / "conversations.json", '"from the PC"')
    code = at_rest.recovery_key()
    at_rest.use_key(None)
    assert at_rest.unopenable([tmp_path]) == [tmp_path / "conversations.json"]
    assert "1 sealed files" in at_rest.start_problem([tmp_path])
    at_rest.restore(code)
    assert at_rest.unopenable([tmp_path]) == [] and at_rest.start_problem([tmp_path]) == ""
    assert at_rest.open_text(tmp_path / "conversations.json") == '"from the PC"'


@pytest.mark.skipif(sys.platform != "win32", reason="DPAPI is Windows'")
def test_windows_still_opens_its_own_entry_in_a_key_file_linux_has_added_to(tmp_path):
    at_rest.use_key(None)
    path = tmp_path / "conversations.json"
    atomic_write_text(path, '"kept"')
    record = json.loads(at_rest.key_file().read_text(encoding="utf-8"))
    record["keys"].append(at_rest._wrap(at_rest._key_for(record["current"]), SECRET))
    at_rest.key_file().write_text(json.dumps(record), encoding="utf-8")
    at_rest.forget()
    assert at_rest.open_text(path) == '"kept"' and at_rest.status()["protection"] == "dpapi"
    at_rest.restore(_recovery_of(KEY))  # another key recovered on Windows: the Linux entry is still kept
    assert sum(1 for e in json.loads(at_rest.key_file().read_text(encoding="utf-8"))["keys"]
               if e.get("by") == "secret") == 1


def test_a_mia_with_no_window_does_not_start_over_files_she_cannot_open(monkeypatch, capsys):
    from core import runtime

    monkeypatch.setattr(at_rest, "start_problem", lambda: "MIA's sealed files can't be opened here: locked.")
    monkeypatch.setattr(runtime, "Runtime", lambda: pytest.fail("she was built anyway"))
    assert runtime.main() == 3 and "can't be opened here" in capsys.readouterr().out


# ------------------------------------------------------------------ where the secret comes from


def _systemd(monkeypatch, tmp_path, opens=True):
    """A stand-in for systemd-creds: `encrypt` writes the secret to the file reversed, `decrypt` gives it back (or
    fails when `opens` is False). Returns the list of commands it was given."""
    ran = []

    def run(args, given=None):
        """One call of the tool."""
        ran.append(args)
        if "encrypt" in args:
            open(args[-1], "wb").write(given[::-1])
            return subprocess.CompletedProcess(args, 0, b"", b"")
        if "decrypt" in args and opens:
            return subprocess.CompletedProcess(args, 0, open(args[-2], "rb").read()[::-1] + b"\n", b"")
        return subprocess.CompletedProcess(args, 1, b"", b"no")

    monkeypatch.setattr(key_unlock, "_run", run)
    monkeypatch.setattr(key_unlock, "supported", lambda: True)
    monkeypatch.setattr(key_unlock.shutil, "which", lambda name: "/usr/bin/" + name)
    monkeypatch.setenv(key_unlock.ENV_FILE, str(tmp_path / "config" / "data-key.cred"))
    monkeypatch.delenv("CREDENTIALS_DIRECTORY", raising=False)
    return ran


def test_the_service_reads_its_secret_from_the_credential_folder_and_refuses_a_cut_off_one(tmp_path, monkeypatch):
    monkeypatch.setenv(key_unlock.ENV_FILE, str(tmp_path / "none.cred"))
    monkeypatch.setenv("CREDENTIALS_DIRECTORY", str(tmp_path))
    (tmp_path / key_unlock.NAME).write_bytes(SECRET + b"\n")
    assert key_unlock.find() == (SECRET, "")
    (tmp_path / key_unlock.NAME).write_bytes(b"short")
    monkeypatch.setattr(key_unlock.shutil, "which", lambda name: "/usr/bin/" + name)
    secret, why = key_unlock.find()
    assert secret is None and "no unlock secret has been made yet" in why
    monkeypatch.setattr(key_unlock.shutil, "which", lambda name: None)  # the phone: no systemd at all
    secret, why = key_unlock.find()
    assert secret is None and "nothing to keep an unlock secret with" in why and "python -m" not in why


def test_a_terminal_has_systemd_open_the_secret_and_never_passes_it_as_an_argument(tmp_path, monkeypatch):
    ran = _systemd(monkeypatch, tmp_path)
    path = key_unlock.make()
    secret, why = key_unlock.find()
    assert path == key_unlock.credential_file() and len(secret) == 64 and why == ""
    assert all(secret.decode() not in " ".join(args) for args in ran)
    assert all("--user" in args and f"--name={key_unlock.NAME}" in args for args in ran)


def test_making_the_secret_never_replaces_one_that_is_there(tmp_path, monkeypatch):
    _systemd(monkeypatch, tmp_path)
    path = key_unlock.make()
    before = path.read_bytes()
    with pytest.raises(key_unlock.UnlockError, match="never replaced"):
        key_unlock.make()
    assert path.read_bytes() == before


def test_a_new_secret_that_does_not_read_back_is_removed_not_kept(tmp_path, monkeypatch):
    _systemd(monkeypatch, tmp_path, opens=False)
    with pytest.raises(key_unlock.UnlockError, match="didn't read back"):
        key_unlock.make()
    assert not key_unlock.credential_file().exists()


def test_a_secret_this_machine_cannot_open_is_reported_with_the_reason(tmp_path, monkeypatch):
    _systemd(monkeypatch, tmp_path)
    key_unlock.make()
    _systemd(monkeypatch, tmp_path, opens=False)
    secret, why = key_unlock.find()
    assert secret is None and "couldn't open its unlock secret" in why


# ------------------------------------------------------------------ the command-line tool


def test_protect_makes_the_secret_once_and_says_when_one_is_already_there(tmp_path, monkeypatch, capsys):
    _systemd(monkeypatch, tmp_path)
    monkeypatch.setattr(at_rest, "dpapi_available", lambda: False)
    monkeypatch.setattr(key_unlock, "has_tpm", lambda: False)
    assert data_key.main(["protect"]) == 0
    assert "no TPM chip" in capsys.readouterr().out
    kept = key_unlock.credential_file().read_bytes()
    assert data_key.main(["protect"]) == 0 and "already made" in capsys.readouterr().out
    _systemd(monkeypatch, tmp_path, opens=False)
    assert data_key.main(["protect"]) == 1 and "isn't replaced" in capsys.readouterr().out
    assert key_unlock.credential_file().read_bytes() == kept


def test_on_windows_protect_has_nothing_to_set_up(monkeypatch, capsys):
    monkeypatch.setattr(at_rest, "dpapi_available", lambda: True)
    assert data_key.main(["protect"]) == 0 and "nothing to set up" in capsys.readouterr().out


def test_restore_asks_for_the_key_without_showing_it_and_says_when_files_still_do_not_open(tmp_path, monkeypatch,
                                                                                           capsys):
    at_rest.use_key(KEY)
    code = at_rest.recovery_key()
    atomic_write_text(tmp_path / "conversations.json", '"mine"')
    at_rest.use_key(bytes(32))
    atomic_write_text(tmp_path / "health.json", '"under a key nobody kept"')
    at_rest.use_key(bytes([7]) * 32)
    monkeypatch.setattr(data_key, "folders", lambda: [tmp_path])
    monkeypatch.setattr(data_key.getpass, "getpass", lambda prompt: code)
    assert data_key.main(["restore"]) == 1
    said = capsys.readouterr().out
    assert "Restored key" in said and "1 sealed files still don't open" in said and code not in said
    assert at_rest.open_text(tmp_path / "conversations.json") == '"mine"'
    monkeypatch.setattr(data_key.getpass, "getpass", lambda prompt: "not a key")
    assert data_key.main(["restore"]) == 1 and "Not restored" in capsys.readouterr().out
