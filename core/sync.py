"""
core.sync
===========

Two-way sync between the phone and the home computer (DEC-0022, the step
after the link; Zac, 2026-10-18). A change on either one shows up on the
other: missions, the kitchen, money, the journal, quests, everything that
lives in MIA's data files, and the XP and credits you earned.

**Who syncs.** The phone drives it: whenever it can reach the PC it's
linked to (core/home_link.py: same Wi-Fi, or Tailscale), it compares,
pushes and pulls. The PC only answers (`/api/sync/*`, the person's own
link key), so it never needs to reach the phone.

**What syncs.** Two folders, matched by meaning rather than by id (the
phone's account and the PC's have different ids):
- `mine`: the person's own folder (data/profiles/<id>/);
- `home`: their household's folder (data/ for the device's first one).
In each, the JSON data files directly in it (SYNC_SUFFIXES), minus what
belongs to one device only (NEVER_SYNC: camera logins, logs, the private
journal's keys...). Photos and other files in subfolders don't sync yet.
And the account's game numbers (XP, credits, prestige, unlocked rewards).

**How a file syncs.** The phone keeps a copy of each file as it was at
the last sync (the *base*, in data/.sync/). Changed on one side only:
that side's copy wins. Changed on both: a three-way merge (merge_json):
records are matched by their id, so two people adding different
missions both stay; the same record changed on both sides keeps each
side's changed fields, and when both changed the same field the newer
file wins. The history (life_events.jsonl) is merged line by line by
event id. XP and credits add up what each side earned since the base.

**Safety.** The PC only takes a file when it's still the version the
phone saw (`expect`), so two phones can't overwrite each other; every
write goes through atomic_write_text, and the stores reading a file
read it again (core/undo_log.reload_stores), so screens update.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from pathlib import Path
from typing import Any, Optional

from core.logger import get_logger

log = get_logger(__name__)

SYNC_SUFFIXES = (".json", ".jsonl")
NEVER_SYNC = frozenset({
    "security_cameras.json", "security_logins.json",  # the cameras belong to the computer they're on
    "activity_log.json", "communication_log.json",  # what this device did
    "private_journal.json", "private_journal_keys.json",  # encrypted with keys that must move together; later
    "model_bench_cases.json", "push_subscriptions.json", "conversations.json",  # per device / shipped
})
SCOPES = ("mine", "home")
ID_HINTS = ("id",)
GAME_ADD = ("total_xp", "total_credits")
GAME_MAX = ("prestige_tier",)
GAME_UNION = ("unlocked_reward_ids",)
LOOP_SECONDS, QUIET_SECONDS, BACKOFF_SECONDS = 15, 120, 60
_MISSING = object()


# ------------------------------------------------------------------ pure logic: merging


def digest(data: Optional[bytes]) -> str:
    """A file's fingerprint, the same whatever line endings the device
    writes (MIA on Windows saves "\r\n", the phone "\n"; caught by the
    Windows CI run: without this the two would trade the file forever)."""
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest() if data is not None else ""


def _id_key(items: list) -> Optional[str]:
    """Pure logic. The key that identifies the records in a list: one every
    item has, ending in "id" (mission_id, item_id...), unique per item."""
    if not items or not all(isinstance(i, dict) for i in items):
        return None
    common = set(items[0])
    for item in items[1:]:
        common &= set(item)
    for key in sorted(common, key=lambda k: (k != "id", len(k))):
        if key == "id" or key.endswith("_id"):
            values = [i.get(key) for i in items]
            if all(isinstance(v, (str, int)) for v in values) and len(set(values)) == len(values):
                return key
    return None


def merge_json(base: Any, local: Any, remote: Any, prefer_local: bool) -> Any:
    """Pure logic. A three-way merge: what changed on each side since
    `base` is kept; when both changed the same thing, `prefer_local` says
    which side wins. `base` is _MISSING when the file is new to sync."""
    if local == remote:
        return local
    if base is not _MISSING and local == base:
        return remote
    if base is not _MISSING and remote == base:
        return local
    if isinstance(local, dict) and isinstance(remote, dict):
        b = base if isinstance(base, dict) else {}
        out = {}
        for key in list(local) + [k for k in remote if k not in local]:
            lv, rv = local.get(key, _MISSING), remote.get(key, _MISSING)
            bv = b.get(key, _MISSING) if base is not _MISSING else _MISSING
            if lv is _MISSING:  # only remote has it: new there, or deleted here
                if bv is not _MISSING and rv == bv:
                    continue  # deleted here, untouched there
                out[key] = rv
            elif rv is _MISSING:
                if bv is not _MISSING and lv == bv:
                    continue  # deleted there, untouched here
                out[key] = lv
            else:
                out[key] = merge_json(bv, lv, rv, prefer_local)
        return out
    if isinstance(local, list) and isinstance(remote, list):
        return _merge_list(base if isinstance(base, list) else _MISSING, local, remote, prefer_local)
    return local if prefer_local else remote


def _merge_list(base, local: list, remote: list, prefer_local: bool) -> list:
    key = _id_key(local) or _id_key(remote) or (_id_key(base) if base is not _MISSING else None)
    every = [i for i in local + remote + (base if base is not _MISSING else [])]
    if key is not None and all(isinstance(i, dict) and isinstance(i.get(key), (str, int)) for i in every):
        b = {i[key]: i for i in base} if base is not _MISSING else {}
        lmap, rmap = {i[key]: i for i in local}, {i[key]: i for i in remote}
        out = []
        for ident in [i[key] for i in local] + [i[key] for i in remote if i[key] not in lmap]:
            lv, rv, bv = lmap.get(ident, _MISSING), rmap.get(ident, _MISSING), b.get(ident, _MISSING)
            if lv is _MISSING:
                if bv is not _MISSING and rv == bv:
                    continue  # removed here
                out.append(rv)
            elif rv is _MISSING:
                if bv is not _MISSING and lv == bv:
                    continue  # removed there
                out.append(lv)
            else:
                out.append(merge_json(bv, lv, rv, prefer_local))
        return out
    # No ids: both only added to the end (a log), keep both additions.
    if base is not _MISSING and local[:len(base)] == base and remote[:len(base)] == base:
        return base + local[len(base):] + [i for i in remote[len(base):] if i not in local[len(base):]]
    if base is _MISSING and all(isinstance(i, (str, int, float)) for i in local + remote):
        return local + [i for i in remote if i not in local]
    return local if prefer_local else remote


def merge_lines(base: str, local: str, remote: str) -> str:
    """Pure logic. An append-only history (life_events.jsonl): every line
    from either side once (by its event_id), oldest first."""
    seen, rows = set(), []
    for text in (local, remote):
        for line in (text or "").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except ValueError:
                continue
            ident = row.get("event_id") or line
            if ident in seen:
                continue
            seen.add(ident)
            rows.append((str(row.get("at") or ""), line))
    rows.sort(key=lambda r: r[0])
    return "".join(line + "\n" for _at, line in rows)


def merge_file(name: str, base: Optional[bytes], local: bytes, remote: bytes, prefer_local: bool) -> bytes:
    if name.endswith(".jsonl"):
        return merge_lines((base or b"").decode("utf-8", "replace"), local.decode("utf-8", "replace"),
                           remote.decode("utf-8", "replace")).encode("utf-8")
    try:
        lv, rv = json.loads(local.decode("utf-8") or "null"), json.loads(remote.decode("utf-8") or "null")
        bv = json.loads(base.decode("utf-8") or "null") if base is not None else _MISSING
    except ValueError:
        return local if prefer_local else remote  # not JSON we can read: the newer one
    return json.dumps(merge_json(bv, lv, rv, prefer_local), indent=2, ensure_ascii=False).encode("utf-8")


def merge_game(base: dict, local: dict, remote: dict) -> dict:
    """Pure logic. The account's game numbers: what each side earned since
    the base adds up; prestige is the higher; unlocked rewards, both."""
    out = {}
    for key in GAME_ADD:
        b = int(base.get(key, 0) or 0)
        out[key] = max(0, b + (int(local.get(key, 0) or 0) - b) + (int(remote.get(key, 0) or 0) - b))
    for key in GAME_MAX:
        out[key] = max(int(local.get(key, 0) or 0), int(remote.get(key, 0) or 0))
    for key in GAME_UNION:
        merged = list(local.get(key) or [])
        merged += [i for i in remote.get(key) or [] if i not in merged]
        out[key] = merged
    return out


# ------------------------------------------------------------------ this device's folders


def syncable(name: str) -> bool:
    return name.endswith(SYNC_SUFFIXES) and name not in NEVER_SYNC and not name.startswith(".")


def folders(context, profile_id: str) -> dict[str, Path]:
    """`mine` and `home` on this device, for this person."""
    personal = getattr(context, "personal_data", None)
    households = getattr(context, "households", None)
    mine = personal.folder(profile_id) if personal is not None else None
    home = None
    if households is not None:
        hid = households.household_of(profile_id)
        home = households.folder(hid) if hid else None
    if home is None and personal is not None:
        home = personal.shared_dir
    return {k: v for k, v in (("mine", mine), ("home", home)) if v is not None}


def manifest(context, profile_id: str) -> dict:
    """{scope: {name: [hash, mtime]}} of the syncable files, and the game numbers."""
    out = {}
    for scope, folder in folders(context, profile_id).items():
        files = {}
        if folder.is_dir():
            for path in sorted(folder.iterdir()):
                if path.is_file() and syncable(path.name):
                    data = path.read_bytes()
                    files[path.name] = [digest(data), path.stat().st_mtime]
        out[scope] = files
    out["game"] = game_numbers(context, profile_id)
    return out


def game_numbers(context, profile_id: str) -> dict:
    profiles = getattr(context, "profiles", None)
    profile = profiles.get_profile(profile_id) if profiles is not None else None
    if profile is None:
        return {}
    return {k: getattr(profile, k, None) for k in GAME_ADD + GAME_MAX + GAME_UNION}


def set_game_numbers(context, profile_id: str, values: dict) -> None:
    config = context.config
    record = dict(config.get(f"profiles.{profile_id}") or {})
    if not record:
        return
    for key in GAME_ADD + GAME_MAX + GAME_UNION:
        if key in values:
            record[key] = values[key]
    config.set(f"profiles.{profile_id}", record)
    config.save()  # profiles are read from the config each time: nothing to reload


def path_for(context, profile_id: str, scope: str, name: str) -> Path:
    """The file a scope and name mean here; refuses anything else."""
    if scope not in SCOPES or not syncable(name) or "/" in name or "\\" in name or name in ("..", "."):
        raise ValueError("That isn't a file MIA syncs.")
    folder = folders(context, profile_id).get(scope)
    if folder is None:
        raise ValueError("That folder isn't here.")
    return folder / name


def write_file(context, path: Path, data: bytes) -> None:
    """Write a synced file the way MIA writes, and let its stores read it again."""
    from core.atomic_write import atomic_write_text
    from core.undo_log import reload_stores

    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(path, data.decode("utf-8"))
    reload_stores(context, [path])


# ------------------------------------------------------------------ the phone's side: one sync


class SyncState:
    """What the last sync left behind, per device (data/.sync/)."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def base(self, scope: str, name: str) -> Optional[bytes]:
        path = self.root / scope / name
        return path.read_bytes() if path.is_file() else None

    def set_base(self, scope: str, name: str, data: bytes) -> None:
        path = self.root / scope / name
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_bytes(data)
        tmp.replace(path)

    def game(self) -> dict:
        try:
            return json.loads((self.root / "game.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def set_game(self, values: dict) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "game.json").write_text(json.dumps(values), encoding="utf-8")

    def status(self) -> dict:
        try:
            return json.loads((self.root / "status.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def set_status(self, **values) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "status.json").write_text(json.dumps({**self.status(), **values}), encoding="utf-8")


def state_for(context) -> SyncState:
    personal = getattr(context, "personal_data", None)
    shared = personal.shared_dir if personal is not None else Path(__file__).resolve().parent.parent / "data"
    return SyncState(Path(shared) / ".sync")


def owner(context) -> Optional[str]:
    """Whose data this device syncs: the person signed in here (the phone has one)."""
    profiles = getattr(context, "profiles", None)
    if profiles is None:
        return None
    active = profiles.get_active_profile()
    people = profiles.list_profiles()
    return (active or (people[0] if people else None)).profile_id if (active or people) else None


def sync_now(context, call=None, lock=None) -> dict:
    """One sync with the linked home computer. `call` is home_link.home_call
    (tests pass their own). Returns what happened: {pushed, pulled, merged,
    files, at}. Raises HomeLinkError when the computer can't be reached."""
    from core.home_link import home_call

    call = call or home_call
    lock = lock or threading.Lock()
    pid = owner(context)
    if pid is None:
        raise ValueError("No account on this device to sync.")
    state = state_for(context)
    remote = call(context, "/api/sync/manifest", timeout=10)
    done = {"pushed": 0, "pulled": 0, "merged": 0, "files": 0}
    here = folders(context, pid)
    for scope in SCOPES:
        folder = here.get(scope)
        if folder is None:
            continue
        theirs = remote.get(scope) or {}
        names = set(theirs)
        if folder.is_dir():
            names |= {p.name for p in folder.iterdir() if p.is_file() and syncable(p.name)}
        for name in sorted(n for n in names if syncable(n)):
            done["files"] += 1
            path = folder / name
            local = path.read_bytes() if path.is_file() else None
            base = state.base(scope, name)
            rhash, rtime = (theirs.get(name) or ["", 0])[:2]
            lhash, bhash = digest(local), digest(base)
            if lhash == rhash:
                if local is not None and bhash != lhash:
                    state.set_base(scope, name, local)
                continue
            local_changed, remote_changed = lhash != bhash, rhash != bhash
            if local is not None and (not remote_changed or not rhash):
                _push(context, call, scope, name, local, rhash)
                state.set_base(scope, name, local)
                done["pushed"] += 1
                continue
            got = call(context, f"/api/sync/file?scope={scope}&name={name}", timeout=30, raw=True)
            if local is None or not local_changed:
                with lock:
                    write_file(context, path, got)
                state.set_base(scope, name, got)
                done["pulled"] += 1
                continue
            prefer_local = (path.stat().st_mtime if path.is_file() else 0) >= float(rtime or 0)
            merged = merge_file(name, base, local, got, prefer_local)
            with lock:
                if merged != local:
                    write_file(context, path, merged)
            if merged != got:
                _push(context, call, scope, name, merged, digest(got))
            state.set_base(scope, name, merged)
            done["merged"] += 1
    # The account's XP, credits and the rest.
    theirs = remote.get("game") or {}
    mine = game_numbers(context, pid)
    if theirs and mine:
        # The first time there's no base: count from the lower total, so it ends at the higher one.
        base = state.game() or {k: min(int(mine.get(k) or 0), int(theirs.get(k) or 0)) for k in GAME_ADD}
        merged = merge_game(base, mine, theirs)
        if any(merged.get(k) != mine.get(k) for k in merged):
            with lock:
                set_game_numbers(context, pid, merged)
        if any(merged.get(k) != theirs.get(k) for k in merged):
            call(context, "/api/sync/game", merged, timeout=10)
        state.set_game(merged)
    done["at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    state.set_status(last=done["at"], **{k: done[k] for k in ("pushed", "pulled", "merged", "files")}, problem="")
    return done


def _push(context, call, scope: str, name: str, data: bytes, expect: str) -> None:
    import base64

    call(context, "/api/sync/file", {"scope": scope, "name": name, "expect": expect,
                                     "data": base64.b64encode(data).decode("ascii")}, timeout=30)


# ------------------------------------------------------------------ the phone's side: keeping at it


class SyncLoop:
    """Every LOOP_SECONDS on a linked device: sync when something changed
    here (MIA's live counter moved) or QUIET_SECONDS passed; after a
    failure, wait BACKOFF_SECONDS. A background thread; never touches a
    store without the server's turn lock."""

    def __init__(self, context, lock) -> None:
        self.context, self.lock = context, lock
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._last_live = None
        self._last_sync = 0.0
        self._next_try = 0.0
        self.thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self.thread is None:
            self.thread = threading.Thread(target=self._run, name="mia-sync", daemon=True)
            self.thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()

    def poke(self) -> None:
        self._wake.set()

    def _run(self) -> None:
        from core import live
        from core.home_link import HomeLinkError, linked

        while not self._stop.is_set():
            self._wake.wait(LOOP_SECONDS)
            poked = self._wake.is_set()
            self._wake.clear()
            if self._stop.is_set() or not linked(self.context):
                continue
            now = time.monotonic()
            version = live.version() if hasattr(live, "version") else None
            due = poked or version != self._last_live or now - self._last_sync > QUIET_SECONDS
            if not due or now < self._next_try:
                continue
            try:
                sync_now(self.context, lock=self.lock)
                self._last_sync = time.monotonic()
                self._last_live = live.version() if hasattr(live, "version") else None
            except (HomeLinkError, ValueError, OSError) as problem:
                self._next_try = time.monotonic() + BACKOFF_SECONDS
                state_for(self.context).set_status(problem=str(problem))
            except Exception:
                log.exception("Sync failed.")
                self._next_try = time.monotonic() + BACKOFF_SECONDS
                state_for(self.context).set_status(problem="Sync hit a problem; it tries again in a minute.")


def status(context) -> dict:
    from core.home_link import linked

    s = state_for(context).status()
    return {"linked": linked(context), "last": s.get("last", ""), "problem": s.get("problem", ""),
            "pushed": s.get("pushed", 0), "pulled": s.get("pulled", 0), "merged": s.get("merged", 0)}
