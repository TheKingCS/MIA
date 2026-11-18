"""
core.desktop_session
======================

How MIA's own desktop session finds her (FW-03, DEC-0278; `docs/mia_os/MIA_OS_FINAL_IMPLEMENTATION_ROADMAP.md` §4). On
MIA OS her runtime is a systemd user service, separate from the window that shows her, so the window can't be handed
a sign-in token in-process the way the Windows desktop app does (`modules/web_home`). Instead the runtime writes a
small **session file** when it starts in a desktop session:
- the local address of her server (127.0.0.1 only);
- a sign-in token for the person signed in, if there is one;
- who that is, and when it was written.

The shell (`gui/os_shell.py`) reads it.

**Where and who can read it.** The path comes from `MIA_DESKTOP_SESSION_FILE`, which the image's service sets to
`$XDG_RUNTIME_DIR/mia/desktop.json`. That's the person's own runtime folder: in memory, readable only by them, and
gone when they sign out. The file is written with owner-only permissions and replaced whole. Anyone who can read it
is already the person (the same boundary as running as them, DEC-0253). The runtime removes it when it stops.

**Nothing changes on Windows:** without the variable, nothing is written.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

ENV = "MIA_DESKTOP_SESSION_FILE"


def path_from_env() -> Optional[Path]:
    """The session file's path when this runtime serves a desktop session, else None."""
    value = os.environ.get(ENV, "").strip()
    return Path(value) if value else None


def front_end_url(session: dict) -> str:
    """Pure logic. The address the shell opens: her web front end, signed in when the session carries a token."""
    base = str(session.get("url") or "").rstrip("/")
    token = session.get("token")
    return f"{base}/web/" + (f"#token={token}" if token else "")


def write(context, path: Path, now: Optional[datetime] = None) -> bool:
    """Starts her server on 127.0.0.1 (it stays closed to anything outside unless phone access is on) and writes the
    session file, owner-only. Whether it was written."""
    server = getattr(context, "phone_server", None)
    if server is None or not server.ensure_local():
        log.warning("The desktop session file wasn't written: her server isn't running.")
        return False
    from core.person_settings import person_id

    who = person_id(context)
    token = server.local_session(who) if who else None
    data = {"url": server.local_url, "token": token, "profile_id": who,
            "at": (now or datetime.now()).isoformat(timespec="seconds"), "pid": os.getpid()}
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(path.parent, 0o700)
        except OSError:
            pass
        tmp = path.with_name(f".{path.name}.tmp")
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f)
        os.replace(tmp, path)
    except OSError:
        log.exception("The desktop session file couldn't be written")
        return False
    return True


def read(path: Path) -> Optional[dict]:
    """The session as written, or None when there's none yet or it can't be read."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) and data.get("url") else None


def clear(path: Optional[Path]) -> None:
    """Removes the session file (the runtime is stopping, so the token in it is no longer good)."""
    if path is None:
        return
    try:
        Path(path).unlink(missing_ok=True)
    except OSError:
        log.exception("The desktop session file couldn't be removed")
