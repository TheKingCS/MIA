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
"""

from __future__ import annotations

import hashlib
from datetime import date, datetime
from typing import Optional

KEY = "home_link.devices"
DEVICE_ID_CHARS = 12


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


def listed(config, profile_id: str) -> list[dict]:
    """A person's linked phones for the Sign-ins page, newest link first: {"id", "linked", "last_seen"}."""
    rows = [{"id": digest[:DEVICE_ID_CHARS], "linked": entry.get("linked", ""), "last_seen": entry.get("last_seen", "")}
            for digest, entry in _devices(config).items()
            if isinstance(entry, dict) and entry.get("profile_id") == profile_id]
    return sorted(rows, key=lambda row: row["linked"], reverse=True)


def unlink(config, profile_id: str, device_id: str) -> bool:
    """Removes one of this person's linked phones by its listed id; False if there's none of theirs by that id."""
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
