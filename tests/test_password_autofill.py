"""
tests/test_password_autofill.py — filling a login on the phone (core/password_autofill.py, DEC-0035's next step):
sites matched by host (a subdomain fits), apps by their package naming the site, best first, never a password, and
only with the vault unlocked.
"""

from types import SimpleNamespace

import pytest

from core import password_autofill as pa


def _login(entry_id, title, url, username="me"):
    """A login as the vault gives it while it's open."""
    return SimpleNamespace(entry_id=entry_id, title=title, url=url, username=username, password="hunter2")


def test_a_site_is_its_bare_host():
    assert pa.host_of("https://www.Bank.com/login?x=1") == "bank.com"
    assert pa.host_of("accounts.google.com") == "google.com"
    assert pa.host_of("") == ""


def test_sites_fit_by_host_and_apps_by_their_package():
    bank = _login("1", "Bank", "bank.com")
    assert pa.fits(bank, domain="bank.com") == 3
    assert pa.fits(bank, domain="secure.bank.com") == 2
    assert pa.fits(bank, domain="notbank.com") == 0  # a look-alike never fits
    assert pa.fits(_login("2", "Facebook", "facebook.com"), package="com.facebook.katana") == 1
    assert pa.fits(_login("3", "Mail", "mail.com"), package="com.android.chrome") == 0


def test_matches_are_best_first_and_never_carry_a_password():
    vault = SimpleNamespace(logins=lambda: [_login("a", "Bank (old)", "secure.bank.com"), _login("b", "Bank", "bank.com"),
                                            _login("c", "Shop", "shop.com")])
    found = pa.matches(vault, domain="bank.com")
    assert [m["id"] for m in found] == ["b", "a"] and all("password" not in m for m in found)


def test_a_locked_vault_says_so(tmp_path):
    from core.password_vault import PasswordVault, VaultLocked

    vault = PasswordVault(None, data_dir=tmp_path)
    vault.setup("correct horse battery staple 1")
    vault.save("Bank", "me", "pw-1234567", "bank.com")
    assert [m["title"] for m in pa.matches(vault, domain="bank.com")] == ["Bank"]
    vault.lock()
    with pytest.raises(VaultLocked):
        pa.matches(vault, domain="bank.com")
