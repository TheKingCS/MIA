"""
tools.cloud_tests
===================

Runs the test suite in a place without the PC's libraries (a cloud session:
no PySide6, pyserial, mutagen, libzim...). Each library on STUBBED that
can't be imported is replaced by an empty stand-in before pytest starts, so
tests that only import a Qt module on the way (the parity checks, the voice
tools' routing, the glasses asks) run instead of failing to import.

    python -m tools.cloud_tests tests/test_parity.py tests/test_glasses.py tests/test_web_surfaces.py

Give it the files you need: over the whole suite the stand-ins pile up until
the cloud machine runs out of memory (seen 2026-11-07).

What a stand-in can't do still fails: anything that serves through FastAPI
(the endpoint tests) or plays music. Those failures say the library is
missing, not that the code is wrong; the PC's own run is the real check.
Never imported by MIA itself.
"""

from __future__ import annotations

import importlib
import importlib.abc
import importlib.machinery
import sys
import types
from unittest.mock import MagicMock

STUBBED = ("PySide6", "serial", "fastapi", "libzim", "psutil", "pyttsx3", "vosk", "sounddevice", "mutagen",
           "starlette", "uvicorn", "ollama", "piper", "faster_whisper", "cv2")


class Stand_in(types.ModuleType):
    """An empty module: every name on it is a MagicMock, and it can have submodules."""

    __path__: list = []

    def __getattr__(self, name):
        """Any attribute is a MagicMock (dunder names stay missing, so imports behave)."""
        if name.startswith("__"):
            raise AttributeError(name)
        return MagicMock(name=name)


class _StandInFinder(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    """Makes a stand-in for any submodule of a stubbed library (PySide6.QtWidgets, serial.tools.list_ports...)."""

    def find_spec(self, name, path, target=None):
        """A spec for a submodule of a library replaced by a stand-in; None for everything else."""
        root = sys.modules.get(name.split(".")[0])
        return importlib.machinery.ModuleSpec(name, self) if isinstance(root, Stand_in) else None

    def create_module(self, spec):
        """The stand-in module itself."""
        return Stand_in(spec.name)

    def exec_module(self, module):
        """Nothing to run."""


def stub_missing() -> list[str]:
    """Replaces each library on STUBBED that won't import with a stand-in; returns the ones replaced."""
    replaced = []
    for root in STUBBED:
        try:
            importlib.import_module(root)
        except Exception:
            sys.modules[root] = Stand_in(root)
            replaced.append(root)
    sys.meta_path.insert(0, _StandInFinder())
    return replaced


def main(argv: list[str]) -> int:
    """Stubs the missing libraries, says which, and runs pytest with the arguments given."""
    import pytest

    replaced = stub_missing()
    print("Stand-ins for: " + (", ".join(replaced) or "nothing (every library is here)"))
    return pytest.main(argv or ["-q"])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
