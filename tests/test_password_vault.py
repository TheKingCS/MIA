"""
Passwords (core/password_vault.py, DEC-0035): a vault only the master
password (or the recovery code) opens; nothing readable on disk; it locks
itself; guessing gets slower; a browser export comes in; the phone and the
PC sync it still encrypted, only when they hold the same vault; and a
password never shows up anywhere it shouldn't. Placeholder logins only.
"""

import json

import pytest

import core.password_vault as pv
from core.password_vault import PasswordVault, VaultError, VaultLocked, read_csv, strength

MASTER = "correct horse battery staple"


@pytest.fixture(autouse=True)
def quick(monkeypatch):
    monkeypatch.setattr(pv, "SCRYPT", {"n": 2 ** 10, "r": 8, "p": 1})  # the real cost is slow on purpose
    pv._open.clear()
    pv._tries.clear()


@pytest.fixture
def vault(tmp_path):
    return PasswordVault(None, data_dir=tmp_path)


def test_made_opened_locked(vault, tmp_path):
    with pytest.raises(VaultError):
        vault.setup("short")
    code = vault.setup(MASTER)
    assert len(code) == 29 and code.count("-") == 4
    vault.save("Example Bank", "robin@example.com", "s3cret-Placeholder!", "https://bank.example.com", folder="Banking")
    raw = (tmp_path / "password_vault.json").read_text()
    for plain in ("Example Bank", "robin@example.com", "s3cret-Placeholder!", "bank.example.com", "Banking"):
        assert plain not in raw  # nothing readable on disk, titles included
    vault.lock()
    with pytest.raises(VaultLocked):
        vault.logins()
    again = PasswordVault(None, data_dir=tmp_path)  # a fresh start: still locked, count only
    assert again.is_set_up() and not again.is_unlocked() and again.count() == 1
    with pytest.raises(VaultError):
        again.unlock("wrong password here")
    again.unlock(MASTER)
    assert again.get(again.logins()[0].entry_id).password == "s3cret-Placeholder!"


def test_the_recovery_code_opens_it_and_sets_a_new_master(vault):
    code = vault.setup(MASTER)
    vault.save("Example Mail", "robin", "pw-one-Placeholder")
    vault.lock()
    vault.unlock(recovery=code.lower().replace("-", " "))  # however it's typed
    vault.reset_master("a brand new master password")
    vault.lock()
    with pytest.raises(VaultError):
        vault.unlock(MASTER)
    vault.unlock("a brand new master password")
    assert vault.logins()[0].title == "Example Mail"


def test_it_locks_itself_and_guessing_slows_down(vault, monkeypatch):
    vault.setup(MASTER)
    clock = [1000.0]
    monkeypatch.setattr(pv.time, "monotonic", lambda: clock[0])
    vault.unlock(MASTER)
    clock[0] += pv.LOCK_AFTER_SECONDS + 1
    assert not vault.is_unlocked()
    for _ in range(pv.FREE_TRIES):
        with pytest.raises(VaultError, match="not the master password"):
            vault.unlock("nope nope nope")
    with pytest.raises(VaultError, match="Wait"):
        vault.unlock(MASTER)  # even the right one waits now
    clock[0] += 20
    vault.unlock(MASTER)


def test_changing_logins_and_the_master(vault):
    vault.setup(MASTER)
    login = vault.save("Example Shop", "robin", "first-Placeholder-1")
    vault.save("Example Shop", "robin2", "", entry_id=login.entry_id, keep_password=True)
    assert vault.get(login.entry_id).password == "first-Placeholder-1" and vault.get(login.entry_id).username == "robin2"
    with pytest.raises(VaultError):
        vault.change_master("not it at all", "another long password")
    vault.change_master(MASTER, "another long password")
    vault.lock()
    vault.unlock("another long password")
    vault.delete(login.entry_id)
    assert vault.logins() == []


def test_a_browser_export_comes_in_once(vault):
    vault.setup(MASTER)
    chrome = "name,url,username,password,note\nexample.com,https://www.example.com/login,robin,Pa55-Placeholder,\n" \
             ",https://shop.example.org,robin,Pa55-Placeholder,\n"
    assert vault.import_csv(chrome) == 2 and vault.import_csv(chrome) == 0  # not doubled
    titles = sorted(l.title for l in vault.logins())
    assert titles == ["example.com", "shop.example.org"]
    assert vault.health()["reused"] and len(vault.health()["reused"]) == 2
    bitwarden = read_csv("folder,favorite,type,name,notes,fields,reprompt,login_uri,login_username,login_password,login_totp\n"
                         "Banking,,login,Example Bank,,,,https://bank.example.com,robin, spaced pw ,\n")
    assert bitwarden[0]["folder"] == "Banking" and bitwarden[0]["password"] == " spaced pw "
    with pytest.raises(VaultError):
        read_csv("a,b\n1,2\n")


def test_strength():
    assert strength("") == 0 and strength("abc12") == 0 and strength("password") == 1
    assert strength("Tr0ub4dor&3xyz!") >= 3 and strength("correct horse battery staple") >= 3


def test_sync_moves_it_encrypted_and_only_between_the_same_vault(tmp_path, monkeypatch):
    from core import sync

    phone_dir, pc_dir = tmp_path / "phone", tmp_path / "pc"
    phone = PasswordVault(None, data_dir=phone_dir)
    phone.setup(MASTER)
    a = phone.save("Example A", "robin", "aaa-Placeholder")
    pc_dir.mkdir()
    (pc_dir / "password_vault.json").write_bytes((phone_dir / "password_vault.json").read_bytes())  # synced once
    base = (phone_dir / "password_vault.json").read_bytes()
    pc = PasswordVault(None, data_dir=pc_dir)
    pv._open.clear()
    pc.unlock(MASTER)  # the same vault opens on the PC with the same master password
    pc.save("Example B", "robin", "bbb-Placeholder")
    phone.unlock(MASTER)
    phone.save("Example A", "robin", "aaa-changed-Placeholder", entry_id=a.entry_id)
    merged = sync.merge_file("password_vault.json", base, (phone_dir / "password_vault.json").read_bytes(),
                             (pc_dir / "password_vault.json").read_bytes(), True)
    assert b"Placeholder" not in merged
    (phone_dir / "password_vault.json").write_bytes(merged)
    phone._load()
    got = {l.title: l.password for l in phone.logins()}
    assert got == {"Example A": "aaa-changed-Placeholder", "Example B": "bbb-Placeholder"}
    assert sync.vault_id(phone_dir) == sync.vault_id(pc_dir) != ""
    other = PasswordVault(None, data_dir=tmp_path / "other")
    other.setup("a different long master")
    assert sync.vault_id(tmp_path / "other") != sync.vault_id(phone_dir)


def test_the_endpoints_and_never_a_password_where_it_shouldnt_be(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    import server.app as server_app
    from tests.engine_world import build_world

    world = build_world(tmp_path, monkeypatch)
    world.passwords = PasswordVault(world, data_dir=world.my_dir)
    world.profiles.set_password(world.me.profile_id, "pw")
    world.voice = world.llm = world.push_subscriptions = None
    client = TestClient(server_app.create_app(world))
    token = client.post("/api/login", json={"profile_id": world.me.profile_id, "password": "pw"}).json()["token"]
    client.headers.update({"Authorization": f"Bearer {token}"})

    assert client.get("/api/passwords").json()["set_up"] is False
    code = client.post("/api/passwords/setup", json={"master": MASTER}).json()["recovery_code"]
    saved = client.post("/api/passwords/login", json={"title": "Example Bank", "username": "robin",
                                                      "password": "Bank-Placeholder-9!"}).json()
    page = client.get("/api/passwords")
    assert page.headers["cache-control"] == "no-store"
    assert "Bank-Placeholder-9!" not in page.text and page.json()["logins"][0]["title"] == "Example Bank"
    assert client.post(f"/api/passwords/login/{saved['entry_id']}/reveal").json()["password"] == "Bank-Placeholder-9!"
    client.post("/api/passwords/lock")
    assert client.post(f"/api/passwords/login/{saved['entry_id']}/reveal").status_code == 423
    assert "logins" not in client.get("/api/passwords").json()
    assert client.post("/api/passwords/unlock", json={"master": "wrong guess here"}).status_code == 400
    assert client.post("/api/passwords/unlock", json={"recovery": code}).status_code == 200
    # Nowhere else: not the shell, the state, MIA's own files or the log.
    for path in ("/api/shell", "/api/state"):
        assert "Bank-Placeholder-9!" not in client.get(path).text
    for f in tmp_path.rglob("*"):
        if f.is_file():
            assert b"Bank-Placeholder-9!" not in f.read_bytes(), f


def test_grown_ups_only():
    from core.child_accounts import CHILD_APPS
    from core.web_surfaces import APPS_BY_ID

    assert "passwords" not in CHILD_APPS and APPS_BY_ID["passwords"].domains == ()  # and no assistant tools
