"""
core.script_runner
=====================

Executes a Field Kit script (docs/ROADMAP.md milestone 11.4) — writes
its content to a fresh temp file and starts it running as a real
subprocess. No sandboxing: these are the user's own trusted scripts on
their own offline device, same "single-user offline tool" stance this
project already takes for third-party module installation (see
CLAUDE.md's "known intentional simplifications").

Deliberately just the process-management half (start it, hand back the
live handle, clean up the temp file when the caller says it's done) —
not the streaming-output-into-a-QThread half, which is a GUI-facing
concern living in modules/field_kit/script_worker.py (same split as
core/llm_manager.py's chat_with_tools() vs.
core/chat_worker.py's ChatWorker). Keeping this function
plain and Qt-free is also what makes it real-testable: unlike this
milestone's flashing-engine/serial-monitor siblings, a script's
execution needs no special hardware or permissions this dev sandbox
lacks, so this is exercised here with genuine subprocess runs, not
mocks.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

_INTERPRETER_SUFFIXES = {"python": ".py", "shell": ".sh"}


def _interpreter_command(interpreter: str, script_path: Path) -> list[str]:
    if interpreter == "python":
        return [sys.executable, str(script_path)]
    return ["bash", str(script_path)]


def start_script_process(interpreter: str, content: str) -> tuple[subprocess.Popen, Path]:
    """
    Writes `content` to a fresh temp file and starts it running,
    returning the live `Popen` handle (stdout+stderr merged, line-
    buffered text mode, so a caller can read output as it arrives) and
    the temp file's path. The caller is responsible for deleting the
    temp file once the process has exited (`cleanup_script_file()`) —
    not done here, since the file must still exist for the whole
    process lifetime.

    `start_new_session=True` puts the script in its own process
    group — found necessary via real end-to-end testing, not a
    precaution added speculatively: a shell script's own child
    processes (e.g. `sleep 30` forked by the `bash` this function
    starts) are NOT killed by terminating just the `bash` process
    itself, and since that child inherits the same merged stdout pipe,
    a caller reading it (`for line in process.stdout`) blocks until
    that orphan eventually exits on its own — up to the full ~30s in
    the case that surfaced this, not the near-instant stop a "Stop"
    button implies. `terminate_process_tree()` below is the fix's other
    half — it must signal the whole process group, not just this PID.
    """
    suffix = _INTERPRETER_SUFFIXES.get(interpreter, ".sh")
    fd, path_str = tempfile.mkstemp(suffix=suffix, prefix="mia_script_")
    script_path = Path(path_str)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(content)
    script_path.chmod(0o700)

    process = subprocess.Popen(
        _interpreter_command(interpreter, script_path),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        start_new_session=True,
    )
    return process, script_path


def terminate_process_tree(process: subprocess.Popen) -> None:
    """
    Signals the entire process group `start_script_process()` created
    for `process`, not just the single PID Python knows about — see
    that function's docstring for the real bug (an orphaned child
    process blocking output for the remainder of its runtime) this
    fixes. Safe to call on an already-exited process.
    """
    try:
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
    except (ProcessLookupError, PermissionError, OSError):
        pass


def cleanup_script_file(script_path: Path) -> None:
    script_path.unlink(missing_ok=True)
