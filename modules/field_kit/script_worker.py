"""
modules.field_kit.script_worker
==================================

Runs a Field Kit script (docs/ROADMAP.md milestone 11.4) off the GUI
thread, streaming its output back line by line — same scoped
`QThread`-per-run pattern as `core/chat_worker.py`'s
`ChatWorker`: a script can run indefinitely (a network diagnostic loop,
a long-running build), and reading its output synchronously on the GUI
thread would freeze the whole app for as long as it runs.

The actual process management (write content to a temp file, start it,
merge stdout+stderr) lives in `core/script_runner.py` and is Qt-free —
this class is only the "stream lines back via signals, support a Stop
button" wrapper around it.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QThread, Signal

from core.script_runner import cleanup_script_file, start_script_process, terminate_process_tree


class ScriptWorker(QThread):
    output_line = Signal(str)
    finished_with_code = Signal(int)

    def __init__(self, interpreter: str, content: str) -> None:
        super().__init__()
        self._interpreter = interpreter
        self._content = content
        self._process: Optional[object] = None

    def run(self) -> None:
        process, script_path = start_script_process(self._interpreter, self._content)
        self._process = process
        try:
            for line in process.stdout:
                self.output_line.emit(line.rstrip("\n"))
            process.wait()
        finally:
            cleanup_script_file(script_path)
        self.finished_with_code.emit(process.returncode)

    def stop(self) -> None:
        """
        Called from the GUI thread (a "Stop" button). Uses
        terminate_process_tree() (kills the whole process group), not
        a plain process.terminate() — see core/script_runner.py's
        docstring for the real bug (an orphaned grandchild process
        blocking this worker's output-reading loop for the remainder
        of its runtime) that a single-PID terminate() doesn't fix.
        """
        if self._process is not None and self._process.poll() is None:
            terminate_process_tree(self._process)
