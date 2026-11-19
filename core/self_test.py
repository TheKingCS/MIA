"""
core.self_test
==============

MIA's self-test (FW-04): whether this install of MIA works, checked without his data. `python -m core.self_test`
always runs the check in a new, empty folder: it starts itself again with `MIA_HOME` set to a temporary folder (or
to `--home`, which must be empty), so the stores it opens are new ones and his are never read. The check builds MIA,
starts her schedule, makes one change through the action contract (a grocery item), reads it back (DEC-0218), and
stops. Exit 0 when every step passed, 1 when one failed (each step is printed), 2 when the folder isn't empty.

The image runs it after each boot as one of greenboot's checks (`os/files/greenboot/`), under a dynamic user that
can't read anyone's home.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

FLAG = "MIA_SELF_TEST_INSIDE"


def steps() -> list[tuple[str, bool, str]]:
    """The check itself, run inside the throwaway folder: [(step, passed, what was found)]."""
    out: list[tuple[str, bool, str]] = []

    def step(name: str, passed: bool, found: str = "") -> bool:
        """Notes one step."""
        out.append((name, bool(passed), found))
        return bool(passed)

    try:
        from core.runtime import Runtime

        runtime = Runtime(take_lock=False)
    except Exception as problem:  # noqa: BLE001 - a MIA that can't be built fails the test, said plainly
        step("build MIA", False, f"{type(problem).__name__}: {problem}"[:200])
        return out
    step("build MIA", True, f"{len(runtime.services())} services")
    tools = len(runtime.context.assistant_actions._actions)
    step("her tools", tools > 100, f"{tools} tools")
    try:
        runtime.start(serve=False)
        step("start her schedule", runtime.readiness() in ("core", "models", "all"), runtime.readiness())
        actions = runtime.context.actions
        proposal = actions.propose(runtime.context, "grocery.add", {"name": "self-test item"})
        done = actions.approve(runtime.context, proposal.proposal_id)
        step("make a change", done.status == "executed", done.result[:120])
        step("read it back", done.read_back == "ok", done.read_back or "not read back")
    except Exception as problem:  # noqa: BLE001 - any failure is a failed step, said plainly
        step("run", False, f"{type(problem).__name__}: {problem}"[:200])
    finally:
        runtime.stop()
    return out


def main(argv: Optional[list] = None) -> int:
    """Runs the self-test in an empty folder (see the module's opening) and prints each step."""
    args = list(sys.argv[1:] if argv is None else argv)
    if os.environ.get(FLAG) == "1":
        results = steps()
        for name, passed, found in results:
            print(f"{'ok  ' if passed else 'FAIL'} {name}{': ' + found if found else ''}", flush=True)
        return 0 if results and all(passed for _, passed, _ in results) else 1
    home = Path(args[args.index("--home") + 1]) if "--home" in args else Path(tempfile.mkdtemp(prefix="mia-self-test-"))
    home.mkdir(parents=True, exist_ok=True)
    if any(home.iterdir()):
        print(f"The self-test runs only in an empty folder; {home} isn't.", flush=True)
        return 2
    env = {**os.environ, "MIA_HOME": str(home), FLAG: "1", "QT_QPA_PLATFORM": "offscreen"}
    env.pop("MIA_DESKTOP_SESSION_FILE", None)
    done = subprocess.run([sys.executable, "-m", "core.self_test"], env=env, cwd=str(Path(__file__).resolve().parent.parent),
                          capture_output=True, text=True, encoding="utf-8", errors="replace",
                          creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    said = [line for line in (done.stdout or "").splitlines() if line.startswith(("ok  ", "FAIL"))]
    print("\n".join(said) or (done.stderr or "")[-2000:], flush=True)  # its steps; its log stays in its folder
    return done.returncode if said else (done.returncode or 1)


if __name__ == "__main__":
    sys.exit(main())
