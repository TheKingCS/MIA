"""
core.password_autofill
========================

Filling a login into another app or a website on the phone (DEC-0035's next step: "an Android autofill service";
claude, 2026-11-09). The Android side (android-phone/.../MiaAutofillService.kt, AutofillActivity.kt) finds the
username and password boxes and asks here which of the person's logins fit; the person picks one, and only then is
its password read, once, for that box. Nothing is filled without that tap, and the vault must be unlocked with the
master password first, as on the Passwords page.

- `host_of(url)`: a login's site as a bare host ("www.Bank.com/login" -> "bank.com").
- `fits(login, domain, package)`: whether a login belongs to the site Android says the boxes are on (the same host,
  or one a subdomain of the other), or, in an app with no site, to the app (a login's site name in the app's package
  name: "facebook.com" for com.facebook.katana).
- `matches(vault, domain, package)`: the fitting logins, titles and usernames only (never a password), best first.

MIA's assistant still never sees a password: none of this is a tool, and nothing here is logged.
"""

from __future__ import annotations

import re
from urllib.parse import urlsplit

_PREFIXES = ("www.", "m.", "mobile.", "login.", "accounts.", "account.", "auth.", "signin.")
_GENERIC = {"com", "org", "net", "android", "app", "apps", "mobile", "google", "client", "www"}


def host_of(url: str) -> str:
    """Pure logic. A site as a bare lower-case host without www-style prefixes; "" when there's none."""
    text = (url or "").strip().lower()
    if not text:
        return ""
    host = urlsplit(text if "://" in text else "https://" + text).hostname or ""
    for prefix in _PREFIXES:
        if host.startswith(prefix) and host.count(".") > 1:
            host = host[len(prefix):]
    return host


def fits(login, domain: str = "", package: str = "") -> int:
    """Pure logic. How well a login fits the boxes Android found: 3 the same site, 2 one site under the other
    (accounts.bank.com and bank.com), 1 an app whose package names the login's site, 0 not at all."""
    host = host_of(getattr(login, "url", "") or "")
    if not host:
        return 0
    want = host_of(domain)
    if want:
        if want == host:
            return 3
        if want.endswith("." + host) or host.endswith("." + want):
            return 2
        return 0
    name = host.split(".")[-2] if host.count(".") >= 1 else host
    parts = {p for p in re.split(r"[.\-_]", (package or "").lower()) if p and p not in _GENERIC}
    return 1 if name and name in parts else 0


def matches(vault, domain: str = "", package: str = "") -> list[dict]:
    """The person's logins that fit, best first: [{id, title, username, site}], never a password. The vault must be
    unlocked (VaultLocked otherwise, as on the Passwords page)."""
    scored = [(fits(login, domain, package), login) for login in vault.logins()]
    return [{"id": login.entry_id, "title": login.title, "username": login.username, "site": host_of(login.url)}
            for score, login in sorted((s for s in scored if s[0]), key=lambda s: (-s[0], s[1].title.lower()))]
