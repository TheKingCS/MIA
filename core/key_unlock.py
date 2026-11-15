"""
core.key_unlock
=================

Where the secret that opens MIA's data key comes from on Linux (DEC-0126's Linux step, for MIA OS and the Pi:
DEC-0168). On Windows the data key in data/.keys/ is protected by DPAPI; Linux has no DPAPI, so there
`core.at_rest` wraps the data key under an **unlock secret**, and this module is the only place that knows where
that secret is kept.

**What keeps it.** systemd's credentials (`systemd-creds`, systemd 256 or later: Fedora, Raspberry Pi OS 13). The
secret is 32 random bytes, stored encrypted in one file (`credential_file()`, ~/.config/mia/data-key.cred) that
only this user on this machine can open: systemd encrypts it with the machine's TPM chip when there is one, and
with the machine's own key otherwise. So, as with DPAPI, there's nothing to type when MIA starts, and the file is
useless on another computer.

**How MIA gets it** (`find`), in order:
1. From the service: `deploy/mia-runtime.service` names the file (`LoadCredentialEncrypted=`), systemd opens it and
   hands the runtime the secret in `$CREDENTIALS_DIRECTORY/mia-data-key`, a file only that service can read.
2. From a terminal (`python -m tools.data_key ...`, `tools.move_home`): by asking systemd to open the same file
   (`systemd-creds --user decrypt`).
When neither works `find` returns no secret and the reason, and `at_rest` seals nothing (or, when a data key is
already there, stops and says it's locked). A system with no systemd at all (the phone, which also calls itself
Linux, until its Keystore step) gets the plain reason that nothing here keeps a secret.

**Making it** (`make`, `python -m tools.data_key protect`, run by `deploy/install_runtime.sh`): once. An existing
credential file is never replaced, even one that won't open: the data key is wrapped under it, so replacing it
would lock every sealed file until the recovery key was entered.

What it can't do: a machine with no TPM and no disk encryption (the Pi as it ships) keeps the machine's key on the
same drive as the data, so a drive read elsewhere can open both. There the protection is against a copy of MIA's
folder (a backup, a sync), not a stolen drive. Not yet run on a real Linux machine: the tests stand in for systemd.
"""

from __future__ import annotations

import os
import secrets
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

NAME = "mia-data-key"  # the credential's name: in the unit, in the file, and in $CREDENTIALS_DIRECTORY
ENV_FILE = "MIA_DATA_KEY_CRED"  # another place for the credential file (tests, an unusual install)
TOOL = "systemd-creds"
MIN_SECRET = 16  # bytes: a shorter "secret" (an empty or cut-off file) is refused, never used to wrap a key


class UnlockError(ValueError):
    """The unlock secret couldn't be made or kept; the message says why."""


def supported() -> bool:
    """Whether this system can keep an unlock secret at all: Linux with systemd's credential tool."""
    return sys.platform.startswith("linux") and shutil.which(TOOL) is not None


def credential_file() -> Path:
    """Where the encrypted unlock secret is kept: `MIA_DATA_KEY_CRED` when set, else ~/.config/mia/data-key.cred
    (under `XDG_CONFIG_HOME` when that's set). Outside MIA's data folder on purpose: it belongs to the machine."""
    asked = (os.environ.get(ENV_FILE) or "").strip()
    if asked:
        return Path(asked).expanduser()
    base = (os.environ.get("XDG_CONFIG_HOME") or "").strip()
    return (Path(base).expanduser() if base else Path.home() / ".config") / "mia" / "data-key.cred"


def _usable(secret: bytes) -> Optional[bytes]:
    """A secret as read, without the line end a tool may add; None when it's too short to be one."""
    secret = secret.strip()
    return secret if len(secret) >= MIN_SECRET else None


def _run(args: list[str], given: Optional[bytes] = None) -> subprocess.CompletedProcess:
    """Runs systemd's credential tool, the secret only ever on its standard input or output (never an argument)."""
    return subprocess.run([TOOL, *args], input=given, capture_output=True, timeout=60, check=False,
                          creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))


def find() -> tuple[Optional[bytes], str]:
    """The unlock secret and "", or None and why there isn't one here (see the module's opening for the order)."""
    folder = (os.environ.get("CREDENTIALS_DIRECTORY") or "").strip()
    if folder:
        try:
            secret = _usable((Path(folder) / NAME).read_bytes())
        except OSError:
            secret = None
        if secret is not None:
            return secret, ""
    try:
        path = credential_file()
    except RuntimeError:  # no home folder to look in
        return None, "this system has nowhere to keep an unlock secret"
    if shutil.which(TOOL) is None:
        return None, ("this system has nothing to keep an unlock secret with" if not path.is_file()
                      else f"{TOOL} isn't on this system to open {path.name}")
    if not path.is_file():
        return None, "no unlock secret has been made yet: run python -m tools.data_key protect"
    try:
        done = _run(["--user", "decrypt", f"--name={NAME}", str(path), "-"])
    except (OSError, subprocess.SubprocessError) as problem:
        return None, f"{TOOL} couldn't be run ({type(problem).__name__})"
    secret = _usable(done.stdout) if done.returncode == 0 else None
    if secret is None:
        log.error("The unlock secret in %s wouldn't open (%s exit %s)", path, TOOL, done.returncode)
        return None, f"this machine couldn't open its unlock secret ({path.name})"
    return secret, ""


def has_tpm() -> bool:
    """Whether systemd finds a TPM chip to bind the secret to (else it uses the machine's own key)."""
    try:
        return _run(["has-tpm2", "--quiet"]).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def make() -> Path:
    """Makes this machine's unlock secret and keeps it encrypted in `credential_file()`, then opens it again to be
    sure it reads back. Returns the file. UnlockError when the system can't keep one, when a file is already there
    (never replaced: see the module's opening), or when it didn't read back (the new file is then removed)."""
    path = credential_file()
    if path.exists():
        raise UnlockError(f"{path} is already there; it's never replaced, because the data key opens with it.")
    if not supported():
        raise UnlockError(f"this system has no {TOOL} (it needs Linux with systemd 256 or later)")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path.parent, 0o700)
    except OSError:
        pass
    secret = secrets.token_hex(32).encode("ascii")
    try:
        done = _run(["--user", "encrypt", f"--name={NAME}", "-", str(path)], given=secret)
    except (OSError, subprocess.SubprocessError) as problem:
        raise UnlockError(f"{TOOL} couldn't be run ({type(problem).__name__})") from None
    if done.returncode != 0 or not path.is_file():
        path.unlink(missing_ok=True)
        raise UnlockError(f"{TOOL} couldn't keep the secret: "
                          f"{done.stderr.decode('utf-8', 'replace').strip()[:200] or 'no reason given'}")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    back, why = find_in_file()
    if back != secret:
        path.unlink(missing_ok=True)
        raise UnlockError(f"the new secret didn't read back ({why or 'it came back different'}); nothing was kept")
    return path


def find_in_file() -> tuple[Optional[bytes], str]:
    """`find`, but only from the credential file (what a terminal uses), ignoring a service's own copy."""
    kept = os.environ.pop("CREDENTIALS_DIRECTORY", None)
    try:
        return find()
    finally:
        if kept is not None:
            os.environ["CREDENTIALS_DIRECTORY"] = kept
