"""
core.linked_devices
=====================

The phones linked to MIA on this computer (DEC-0022, `core/home_link.py`),
seen and withdrawn from the computer's side (2026-11-10).

A phone links once with its person's password and gets a device key back;
the computer keeps only the key's hash, under `home_link.devices` in
config, with whose it is and when it linked. Until now only the phone
itself could remove its key, so a lost phone stayed trusted. These are the
helpers the server uses to list a person's linked phones (with when each
last reached the computer), unlink one from the Sign-ins page, and unlink
all of them with "sign out everywhere" or a password change.

A device is named to the page by the first DEVICE_ID_CHARS characters of
its hash: enough to tell two apart, never the key.

**Device records** (WP-10, DEC-0242, REQ-DST-005/006/029): each entry also
says what the device is (`name`, in words from its browser's description
when it linked, and `kind`), its key's `scope`, and on the page whether it's
`stale` (not seen for STALE_DAYS). A person's key can do what that person
can (`PERSON`); a household device's key (`HOUSEHOLD`, the household display
to come, WP-20) reaches only `HOUSEHOLD_ROUTES` and is refused anywhere else
(`allows`).

**A lost device** (Q-90): reported lost on the Sign-ins page (`mark_lost`),
its key is refused at once, like an unlinked one, and its hash is kept on
LOST_KEY; when that device next reaches the computer it's answered "erase"
(`lost`, HTTP 410 with X-MIA-Erase), and it erases its MIA data
(core/home_link.py). Erasing happens only when it reconnects: best effort.
"""

from __future__ import annotations

import hashlib
from datetime import date, datetime
from typing import Optional

KEY = "home_link.devices"
LOST_KEY = "home_link.lost"
DEVICE_ID_CHARS = 12
STALE_DAYS = 90
LOST_KEPT_DAYS = 180  # how long a lost device's hash waits for it to reconnect
PERSON, HOUSEHOLD = "person", "household"
# What a household device's key may reach (WP-10): its live updates only, until the household display's own view is
# built (WP-20) and its routes are added here. Anything else answers 403.
HOUSEHOLD_ROUTES = ("/api/live",)


def _devices(config) -> dict:
    """Every linked device's entry, hash to {"profile_id", "linked", "last_seen"?}, as a fresh dict."""
    return dict(config.get(KEY, {}) or {})


def _save(config, devices: dict) -> None:
    """Writes the device entries back to config."""
    config.set(KEY, devices)
    config.save()


def key_hash(key: str) -> str:
    """The hash a device key is kept under."""
    return hashlib.sha256(key.encode()).hexdigest()


def for_key(config, key: str, today: Optional[date] = None) -> Optional[str]:
    """Whose device key this is (a profile id), or None. Stamps the device's last_seen, at most once a day so a
    phone's every request doesn't rewrite config."""
    devices = _devices(config)
    digest = key_hash(key)
    found = devices.get(digest)
    profile_id = found.get("profile_id") if isinstance(found, dict) else None
    if profile_id:
        day = (today or date.today()).isoformat()
        if str(found.get("last_seen", ""))[:10] != day:
            devices[digest] = {**found, "last_seen": day}
            _save(config, devices)
    return profile_id


def record(profile_id: str, name: str = "", kind: str = "phone", scope: str = PERSON) -> dict:
    """Pure logic. A new device's record: whose, what it is (its name in words, its kind), its key's scope, and when
    it linked."""
    return {"profile_id": profile_id, "name": (name or "")[:80], "kind": kind or "phone",
            "scope": HOUSEHOLD if scope == HOUSEHOLD else PERSON, "linked": linked_at()}


def scope_of(config, key: str) -> str:
    """A linked device's key scope (a person's, unless it says household); "" for a key that isn't linked."""
    entry = _devices(config).get(key_hash(key))
    if not isinstance(entry, dict):
        return ""
    return HOUSEHOLD if entry.get("scope") == HOUSEHOLD else PERSON


def allows(scope: str, path: str) -> bool:
    """Pure logic. Whether a key of this scope may reach this path: a person's anywhere they can, a household
    device's only HOUSEHOLD_ROUTES (REQ-DST-029)."""
    if scope == HOUSEHOLD:
        return any(path == route or path.startswith(route + "/") or path.startswith(route + "?")
                   for route in HOUSEHOLD_ROUTES)
    return scope == PERSON


def _stale(entry: dict, today: date) -> bool:
    """Pure logic. Whether a device hasn't reached the computer for STALE_DAYS (since it linked, if never)."""
    seen = str(entry.get("last_seen") or entry.get("linked") or "")[:10]
    try:
        return (today - date.fromisoformat(seen)).days >= STALE_DAYS
    except ValueError:
        return False


def listed(config, profile_id: str, today: Optional[date] = None) -> list[dict]:
    """A person's linked devices for the Sign-ins page, newest link first: {"id", "name", "kind", "scope", "linked",
    "last_seen", "stale"}; then those reported lost, each {"id", "name", "kind", "lost", "told"} (told: when it was
    answered "erase", "" while it hasn't reconnected)."""
    today = today or date.today()
    rows = [{"id": digest[:DEVICE_ID_CHARS], "name": entry.get("name", ""), "kind": entry.get("kind", "phone"),
             "scope": entry.get("scope", PERSON), "linked": entry.get("linked", ""),
             "last_seen": entry.get("last_seen", ""), "stale": _stale(entry, today)}
            for digest, entry in _devices(config).items()
            if isinstance(entry, dict) and entry.get("profile_id") == profile_id]
    lost = [{"id": digest[:DEVICE_ID_CHARS], "name": entry.get("name", ""), "kind": entry.get("kind", "phone"),
             "lost": entry.get("lost", ""), "told": entry.get("told", "")}
            for digest, entry in _lost(config).items()
            if isinstance(entry, dict) and entry.get("profile_id") == profile_id]
    return sorted(rows, key=lambda row: row["linked"], reverse=True) + sorted(lost, key=lambda r: r["lost"], reverse=True)


def _lost(config) -> dict:
    """The devices reported lost and still waiting to reconnect: hash to {"profile_id", "name", "kind", "lost",
    "told"?}, as a fresh dict."""
    return dict(config.get(LOST_KEY, {}) or {})


def mark_lost(config, profile_id: str, device_id: str, today: Optional[date] = None) -> bool:
    """Reports one of this person's devices lost: its key is refused from now on (its record leaves the linked ones),
    and its hash waits on LOST_KEY so the device is told to erase when it reconnects. False if there's none of theirs
    by that id. Old lost entries (LOST_KEPT_DAYS) are dropped."""
    device_id = str(device_id or "")
    if len(device_id) != DEVICE_ID_CHARS:
        return False
    devices = _devices(config)
    match = [digest for digest, entry in devices.items() if digest.startswith(device_id)
             and isinstance(entry, dict) and entry.get("profile_id") == profile_id]
    if len(match) != 1:
        return False
    entry = devices.pop(match[0])
    day = (today or date.today())
    lost = {digest: e for digest, e in _lost(config).items() if isinstance(e, dict)
            and (day - date.fromisoformat(str(e.get("lost", day.isoformat()))[:10])).days < LOST_KEPT_DAYS}
    lost[match[0]] = {"profile_id": profile_id, "name": entry.get("name", ""), "kind": entry.get("kind", "phone"),
                      "lost": linked_at()}
    config.set(KEY, devices)
    config.set(LOST_KEY, lost)
    config.save()
    return True


def lost(config, key: str) -> Optional[dict]:
    """None for a key that isn't a device reported lost; else {"profile_id", "first"} (so it's answered "erase",
    never let in). The first time it asks, when it was told is noted for the page and `first` is True, so the
    security log says it once."""
    digest = key_hash(key)
    entries = _lost(config)
    entry = entries.get(digest)
    if not isinstance(entry, dict):
        return None
    first = not entry.get("told")
    if first:
        entries[digest] = {**entry, "told": linked_at()}
        config.set(LOST_KEY, entries)
        config.save()
    return {"profile_id": entry.get("profile_id", ""), "first": first}


def unlink(config, profile_id: str, device_id: str) -> bool:
    """Removes one of this person's linked devices by its listed id (a phone found again links afresh; a lost one is
    `mark_lost`); False if there's none of theirs by that id."""
    device_id = str(device_id or "")
    if len(device_id) != DEVICE_ID_CHARS:
        return False
    devices = _devices(config)
    match = [digest for digest, entry in devices.items() if digest.startswith(device_id)
             and isinstance(entry, dict) and entry.get("profile_id") == profile_id]
    if len(match) != 1:
        return False
    del devices[match[0]]
    _save(config, devices)
    return True


def unlink_all(config, profile_id: str) -> int:
    """Removes every phone linked for this person (sign out everywhere, a password change); how many there were."""
    devices = _devices(config)
    kept = {digest: entry for digest, entry in devices.items()
            if not (isinstance(entry, dict) and entry.get("profile_id") == profile_id)}
    removed = len(devices) - len(kept)
    if removed:
        _save(config, kept)
    return removed


def linked_at() -> str:
    """The `linked` stamp for a new device: now, to the second."""
    return datetime.now().isoformat(timespec="seconds")
