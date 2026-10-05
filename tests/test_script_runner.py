"""
tests.test_script_runner
===========================

Unit tests for core.script_runner — genuine subprocess runs, not
mocks. Unlike this project's flashing-engine/serial-monitor work
(blocked on real hardware this dev sandbox doesn't have), a script's
execution needs nothing special: real `bash`/the real Python
interpreter are both right here, so these tests exercise the actual
code path end to end.
"""

from __future__ import annotations

import sys
import time
from types import SimpleNamespace

import core.script_runner as script_runner_module
from core.script_runner import cleanup_script_file, start_script_process, terminate_process_tree


def _run_to_completion(interpreter: str, content: str) -> tuple[int, str]:
    process, script_path = start_script_process(interpreter, content)
    output = process.stdout.read()
    process.wait()
    returncode = process.returncode
    cleanup_script_file(script_path)
    return returncode, output


def test_shell_script_runs_and_captures_stdout():
    returncode, output = _run_to_completion("shell", "echo hello from shell")
    assert returncode == 0
    assert "hello from shell" in output


def test_shell_script_nonzero_exit_code_is_captured():
    returncode, _ = _run_to_completion("shell", "exit 7")
    assert returncode == 7


def test_shell_script_stderr_is_merged_into_output():
    returncode, output = _run_to_completion("shell", "echo to stderr 1>&2")
    assert returncode == 0
    assert "to stderr" in output


def test_python_script_runs_and_captures_stdout():
    returncode, output = _run_to_completion("python", "print('hello from python')")
    assert returncode == 0
    assert "hello from python" in output


def test_python_script_uses_the_same_interpreter_running_the_tests():
    returncode, output = _run_to_completion("python", "import sys; print(sys.executable)")
    assert returncode == 0
    assert output.strip() == sys.executable


def test_unknown_interpreter_falls_back_to_shell():
    returncode, output = _run_to_completion("ruby", "echo fallback works")
    assert returncode == 0
    assert "fallback works" in output


def test_multiline_shell_script_runs_correctly():
    content = "\n".join(["x=1", "y=2", "echo $((x + y))"])
    returncode, output = _run_to_completion("shell", content)
    assert returncode == 0
    assert "3" in output


def test_cleanup_script_file_removes_temp_file():
    process, script_path = start_script_process("shell", "echo hi")
    process.wait()
    assert script_path.exists()
    cleanup_script_file(script_path)
    assert not script_path.exists()


def test_cleanup_script_file_is_idempotent():
    process, script_path = start_script_process("shell", "echo hi")
    process.wait()
    cleanup_script_file(script_path)
    cleanup_script_file(script_path)  # already gone — must not raise


def test_script_can_be_terminated_before_completion():
    """
    Simulates a Stop button click on a long-running script — reading
    stdout to EOF (same as ScriptWorker.run()'s `for line in
    process.stdout` loop) must return promptly, not block for the rest
    of the script's runtime.

    Regression test for a real bug found via end-to-end testing (not
    this narrower unit test, which is exactly why it originally missed
    it — see below): a plain `process.terminate()` only kills the
    directly-Popen'd `bash` process, not `sleep 30`, which bash runs as
    a *child* process. That orphaned child keeps the merged stdout pipe
    open, so a caller reading it blocks until the orphan exits on its
    own — measured at the full ~30s, not the near-instant stop a "Stop"
    button implies. `start_script_process()` now starts the script in
    its own process group (`start_new_session=True`) specifically so
    `terminate_process_tree()` can kill the whole group, not just the
    one PID Python knows about.

    The original version of this test called `process.terminate()`
    directly and only asserted the return code was nonzero — which
    passes even with the bug present, since the direct `bash` process
    still dies just fine. It never actually read `process.stdout`
    afterward, so it never caught that a reader would block. Kept as a
    cautionary comment: a termination test isn't meaningful unless it
    exercises the same read-to-EOF path the real caller does.
    """
    process, script_path = start_script_process("shell", "sleep 30")
    start = time.time()
    terminate_process_tree(process)

    output = process.stdout.read()
    process.wait(timeout=5)
    elapsed = time.time() - start

    assert elapsed < 5.0, f"Reading stdout to EOF took {elapsed:.2f}s — an orphaned child is likely still running"
    assert process.returncode != 0
    cleanup_script_file(script_path)


# ----------------------------------------------------------------------
# terminate_process_tree — Windows branch (taskkill mocked; this dev
# sandbox has no real Windows to run it against, see script_runner.py's
# 2026-07-16 docstring note)
# ----------------------------------------------------------------------

def test_terminate_process_tree_uses_taskkill_on_windows(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    calls = []
    monkeypatch.setattr(
        script_runner_module.subprocess,
        "run",
        lambda args, **kwargs: calls.append(args) or SimpleNamespace(returncode=0),
    )
    fake_process = SimpleNamespace(pid=4242)

    terminate_process_tree(fake_process)

    assert calls == [["taskkill", "/T", "/F", "/PID", "4242"]]


def test_terminate_process_tree_swallows_taskkill_errors_on_windows(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")

    def _raise(*args, **kwargs):
        raise FileNotFoundError("taskkill not found")

    monkeypatch.setattr(script_runner_module.subprocess, "run", _raise)
    fake_process = SimpleNamespace(pid=4242)

    terminate_process_tree(fake_process)  # must not raise


def test_windows_prefers_git_bash_over_the_wsl_stub(monkeypatch, tmp_path):
    """On Windows, `bash` on the PATH is usually WSL's stub, which can't run
    a script by its Windows path; Git for Windows' bash is used instead."""
    import shutil

    from core import script_runner

    git_bash = tmp_path / "Git" / "bin" / "bash.exe"
    git_bash.parent.mkdir(parents=True)
    git_bash.write_text("")
    monkeypatch.setattr(script_runner.sys, "platform", "win32")
    monkeypatch.setenv("ProgramFiles", str(tmp_path))
    assert script_runner.find_bash() == str(git_bash)
    git_bash.unlink()
    monkeypatch.setenv("ProgramFiles(x86)", str(tmp_path))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "nothing"))
    monkeypatch.setattr(shutil, "which", lambda name: r"C:\Windows\System32\bash.exe")
    assert script_runner.find_bash() == "bash"  # the WSL stub is never chosen
