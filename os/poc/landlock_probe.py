"""
os.poc.landlock_probe
=======================

Proof of concept 6 for MIA OS (DEC-0194, `docs/mia_os/MIA_OS_CORE_ARCHITECTURE_OPEN_QUESTIONS.md` section 2): can a
Python worker of MIA's give up, by the kernel's Landlock, access to every file except the folders he granted?

What it does, on Linux only (standard library, no root):

1. Reads the kernel's Landlock version (`landlock_create_ruleset` with the version flag). None: the probe says so
   and exits 2, which is a finding, not a crash.
2. Makes a granted folder and an outside folder, each with a file.
3. Starts a worker (this file again, `--worker`) that restricts itself to: read and write in the granted folder, and
   read and execute in Python's own install (so imports keep working), then tries to read and write inside, read
   and write outside, list `/etc`, read the home folder, and import a module it hadn't imported yet.
4. Starts a second worker with a different grant, to show that a changed grant takes effect in a new worker.
5. Times many file opens inside the granted folder with and without the restriction.

It prints one line per check and a JSON summary, and exits 0 only when every check came out as Landlock promises.
Run it as `python3 os/poc/landlock_probe.py`; CI runs it (`.github/workflows/mia-os-poc.yml`).
"""

from __future__ import annotations

import ctypes
import ctypes.util
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# x86_64 and aarch64 share these numbers (they were added after the tables were unified).
SYS_CREATE_RULESET, SYS_ADD_RULE, SYS_RESTRICT_SELF = 444, 445, 446
CREATE_RULESET_VERSION = 1
RULE_PATH_BENEATH = 1
PR_SET_NO_NEW_PRIVS = 38
# Filesystem rights (ABI 1), then ABI 2's REFER and ABI 3's TRUNCATE.
EXECUTE, WRITE_FILE, READ_FILE, READ_DIR = 1, 2, 4, 8
ABI1_ALL = 0x1FFF
REFER, TRUNCATE = 1 << 13, 1 << 14
READ = READ_FILE | READ_DIR
READ_EXEC = READ | EXECUTE

_libc = ctypes.CDLL(ctypes.util.find_library("c") or "libc.so.6", use_errno=True)
_libc.syscall.restype = ctypes.c_long


class _RulesetAttr(ctypes.Structure):
    """struct landlock_ruleset_attr, its first field only (accepted by every ABI)."""
    _fields_ = [("handled_access_fs", ctypes.c_uint64)]


class _PathBeneathAttr(ctypes.Structure):
    """struct landlock_path_beneath_attr (packed: 12 bytes)."""
    _pack_ = 1
    _fields_ = [("allowed_access", ctypes.c_uint64), ("parent_fd", ctypes.c_int32)]


def abi_version() -> int:
    """The kernel's Landlock version, 0 when it has none (or it's turned off)."""
    if platform.system() != "Linux":
        return 0
    v = _libc.syscall(SYS_CREATE_RULESET, None, ctypes.c_size_t(0), ctypes.c_uint32(CREATE_RULESET_VERSION))
    return int(v) if v > 0 else 0


def handled(abi: int) -> int:
    """Every filesystem right this kernel's Landlock knows (so anything not granted is denied)."""
    rights = ABI1_ALL
    if abi >= 2:
        rights |= REFER
    if abi >= 3:
        rights |= TRUNCATE
    return rights


def restrict(grants: dict[str, int], abi: int) -> None:
    """Restricts this process, irreversibly, to the given paths and rights. OSError when the kernel refuses."""
    attr = _RulesetAttr(handled(abi))
    fd = _libc.syscall(SYS_CREATE_RULESET, ctypes.byref(attr), ctypes.c_size_t(ctypes.sizeof(attr)), ctypes.c_uint32(0))
    if fd < 0:
        raise OSError(ctypes.get_errno(), "landlock_create_ruleset")
    try:
        for path, rights in grants.items():
            if not os.path.exists(path):
                continue
            pfd = os.open(path, os.O_PATH | os.O_CLOEXEC)
            try:
                rule = _PathBeneathAttr(rights & handled(abi), pfd)
                if _libc.syscall(SYS_ADD_RULE, ctypes.c_int(fd), ctypes.c_int(RULE_PATH_BENEATH), ctypes.byref(rule),
                                 ctypes.c_uint32(0)) < 0:
                    raise OSError(ctypes.get_errno(), f"landlock_add_rule {path}")
            finally:
                os.close(pfd)
        if _libc.prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0:
            raise OSError(ctypes.get_errno(), "prctl NO_NEW_PRIVS")
        if _libc.syscall(SYS_RESTRICT_SELF, ctypes.c_int(fd), ctypes.c_uint32(0)) < 0:
            raise OSError(ctypes.get_errno(), "landlock_restrict_self")
    finally:
        os.close(fd)


def _python_paths() -> list[str]:
    """Where this Python's code lives (read and execute stay allowed, so imports keep working)."""
    found = {sys.base_prefix, sys.prefix, os.path.dirname(os.path.realpath(sys.executable))}
    found |= {p for p in sys.path if p and os.path.isdir(p)}
    found |= {"/usr/lib", "/usr/lib64", "/lib", "/lib64", "/usr/local/lib"}
    return sorted(p for p in found if os.path.isdir(p))


def _try(action) -> str:
    """Runs one file action: "allowed", or "denied" for a permission error, or the other error's name."""
    try:
        action()
        return "allowed"
    except PermissionError:
        return "denied"
    except OSError as problem:
        return type(problem).__name__ + f" ({problem.errno})"


def _opens(folder: str, n: int = 3000) -> float:
    """Seconds for n opens and reads of one file in the folder."""
    path = os.path.join(folder, "inside.txt")
    started = time.perf_counter()
    for _ in range(n):
        with open(path, "rb") as f:
            f.read(1)
    return time.perf_counter() - started


def worker(granted: str, outside: str, abi: int) -> dict:
    """The worker's side: restricts itself to the grant, then tries each thing and reports what happened."""
    before = _opens(granted)
    grants = {granted: READ | WRITE_FILE | (1 << 8) | (1 << 5) | (TRUNCATE if abi >= 3 else 0)}  # read, write, make, remove
    for p in _python_paths():
        grants.setdefault(p, READ_EXEC)
    restrict(grants, abi)
    home = os.path.expanduser("~")
    checks = {
        "read inside the grant": _try(lambda: open(os.path.join(granted, "inside.txt")).read()),
        "write inside the grant": _try(lambda: open(os.path.join(granted, "new.txt"), "w").write("ok")),
        "read outside": _try(lambda: open(os.path.join(outside, "outside.txt")).read()),
        "write outside": _try(lambda: open(os.path.join(outside, "new.txt"), "w").write("no")),
        "list /etc": _try(lambda: os.listdir("/etc")),
        "list the home folder": _try(lambda: os.listdir(home)),
        "import a module not loaded yet": _try(lambda: __import__("xml.dom.minidom")),
    }
    after = _opens(granted)
    return {"checks": checks, "opens_before_s": round(before, 4), "opens_after_s": round(after, 4)}


EXPECTED = {"read inside the grant": "allowed", "write inside the grant": "allowed", "read outside": "denied",
            "write outside": "denied", "list /etc": "denied", "list the home folder": "denied",
            "import a module not loaded yet": "allowed"}


def run_worker(granted: str, outside: str, abi: int) -> dict:
    """Starts a worker process with this grant and returns its report."""
    out = subprocess.run([sys.executable, __file__, "--worker", granted, outside, str(abi)], capture_output=True,
                         text=True, timeout=120)
    if out.returncode != 0:
        return {"error": (out.stderr or out.stdout).strip()[-800:]}
    return json.loads(out.stdout)


def main() -> int:
    """Runs the probe and prints the findings; 0 when Landlock did everything promised."""
    if len(sys.argv) == 5 and sys.argv[1] == "--worker":
        print(json.dumps(worker(sys.argv[2], sys.argv[3], int(sys.argv[4]))))
        return 0
    abi = abi_version()
    summary = {"kernel": platform.release(), "python": platform.python_version(), "landlock_abi": abi}
    if not abi:
        summary["finding"] = "This kernel has no Landlock (or it's turned off): PoC 6 can't be shown here."
        print(json.dumps(summary, indent=2))
        return 2
    with tempfile.TemporaryDirectory(dir=os.path.expanduser("~")) as base:
        a, b = Path(base, "granted_a"), Path(base, "granted_b")
        for folder, name in ((a, "inside.txt"), (b, "inside.txt"), (a, "outside.txt"), (b, "outside.txt")):
            folder.mkdir(exist_ok=True)
            (folder / name).write_text("x")
        first = run_worker(str(a), str(b), abi)
        second = run_worker(str(b), str(a), abi)  # the grant changed: a new worker sees the new one
        summary["worker_with_grant_a"] = first
        summary["worker_with_grant_b"] = second
    ok = all(r.get("checks") == EXPECTED for r in (first, second))
    for label, report in (("grant a", first), ("grant b", second)):
        for check, result in (report.get("checks") or {}).items():
            mark = "ok " if result == EXPECTED[check] else "BAD"
            print(f"{mark} [{label}] {check}: {result} (expected {EXPECTED[check]})")
        if "error" in report:
            print(f"BAD [{label}] the worker failed: {report['error']}")
    if first.get("opens_before_s"):
        summary["slowdown"] = round(first["opens_after_s"] / max(first["opens_before_s"], 1e-9), 2)
    summary["passed"] = ok
    print(json.dumps(summary, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
