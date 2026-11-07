"""
tests.test_doc_freshness
==========================

Documentation that keeps up with the code (core/doc_freshness.py, DEC-0110):
a definition whose code changed while its docstring didn't is found, changed
parameters most of all; a docstring edit, moved code or an added decorator
is not; a file's opening is asked about only when public definitions come or
go; and it reads changes from git.
"""

from __future__ import annotations

import subprocess

from core import doc_freshness as df

OLD = '''"""m: things."""


def add(a, b):
    """Adds two numbers."""
    return a + b


def same(x):
    """Returns x."""
    return x


def moved(x):
    """Doubles x."""
    return x * 2


class Box:
    """A box."""
    size: int = 1

    def open(self):
        """Opens it."""
        return True
'''

NEW = '''"""m: things."""

import functools


def add(a, b, c=0):
    """Adds two numbers."""
    return a + b + c


def same(x):
    """Returns x, unchanged."""
    return x + 0


@functools.lru_cache
def moved(x):

    """Doubles x."""

    return x * 2


class Box:
    """A box."""
    size: int = 1

    def open(self):
        """Opens it."""
        return False


def extra():
    """Something new."""


def _helper():
    """A private helper."""
'''


def test_it_finds_code_that_changed_under_an_unchanged_docstring():
    """add's parameters changed (strong); Box.open's code changed; same's docstring was edited with it (fine);
    moved only gained a decorator and blank lines (fine); Box itself didn't change; the file gained a public
    definition with the same opening."""
    found = {f["name"]: f for f in df.stale(OLD, NEW)}
    assert found["add"]["strong"] and "(+c)" in found["add"]["why"]
    assert not found["Box.open"]["strong"] and found["Box.open"]["why"].startswith("its code changed")
    assert "same" not in found and "moved" not in found and "Box" not in found
    assert "1 added" in found[df.MODULE]["why"]
    assert [f["name"] for f in df.stale(OLD, NEW)][0] == "add"  # the strongest first


def test_a_private_helper_alone_doesnt_ask_about_the_file():
    """Adding only a _private helper leaves the file's opening alone; nothing changed, nothing found."""
    assert df.stale(OLD, OLD + '\n\ndef _more():\n    """Private."""\n') == []
    assert df.stale(OLD, OLD) == [] and df.stale("not python (", OLD) == []


def test_it_reads_the_changes_from_git(tmp_path):
    """Against a commit: changed files' stale docstrings with their file, a new file left to the documentation test,
    and nothing when the working tree matches."""
    run = lambda *a: subprocess.run(["git", *a], cwd=tmp_path, capture_output=True, check=True)  # noqa: E731
    run("init", "-q")
    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "m.py").write_text(OLD, encoding="utf-8")
    run("add", ".")
    run("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "one")
    assert df.between("HEAD", root=tmp_path) == []
    (tmp_path / "core" / "m.py").write_text(NEW, encoding="utf-8")
    (tmp_path / "core" / "new.py").write_text('"""new."""\n\n\ndef f():\n    return 1\n', encoding="utf-8")
    found = df.between("HEAD", root=tmp_path)
    assert {f["file"] for f in found} == {"core/m.py"} and any(f["name"] == "add" for f in found)
    text = df.describe(found)
    assert text.startswith("- core/m.py: add: its parameters changed (+c)") and "(check this one)" in text
    assert df.describe([]) == ""
