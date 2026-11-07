"""
core.doc_freshness
====================

Documentation that keeps up with the code (DEC-0110; Zac, 2026-11-07: "when
anything is changed it needs to be reflected in that file's documentation as
well"). DEC-0104 makes sure every definition *has* a docstring; this checks
that a docstring is still *true* after its code changes.

**What it finds** (`stale()`, comparing two versions of a file): every
class, function and method whose code changed while its docstring stayed
word for word the same, with why:
- its parameters changed (added, removed, renamed) and its docstring
  didn't: the strongest sign the words are out of date;
- its code changed and its docstring didn't: worth a read, often fine;
- the file's opening docstring stayed the same while public definitions (not
  _private helpers) were added or removed: does it still say what it holds?

Only real changes count: a docstring edit alone, moving code, or adding a
decorator (`@life_events.on_change` adds history, not a new job) is not a
change to what a function does. A class is compared by its own statements
(its fields), not its methods, which are compared on their own.

**Where it's used:**
- `python -m tools.docs stale [base]`: before a commit, against HEAD (the
  uncommitted changes) or any base; it exits 1 when something needs a look.
- Every lab review (core/work_review.py): the reviewer is given the list for
  the change it reviews, and a stale docstring is a problem to name.
- The `dev.doc_freshness` loop (core/loops.py): how many definitions changed
  in the last week's commits without their docstrings changing.

Code reads it; a person (or MIA) decides whether the words still hold. When
they do, nothing needs changing: the check is a prompt to look, not a rule
that every change must touch its docstring.
"""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
LAYERS = ("core", "server", "tools", "modules", "gui", "tests")
MODULE = "(the file)"


def _strip(node: ast.AST) -> str:
    """Pure logic. A definition's code with its docstring, its decorators and its nested definitions left out, as a
    dump that ignores line numbers: what it does, not how it's laid out."""
    body = list(getattr(node, "body", []))
    if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None), ast.Constant) \
            and isinstance(body[0].value.value, str):
        body = body[1:]
    if isinstance(node, ast.ClassDef):
        body = [s for s in body if not isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
        return ast.dump(ast.Module(body=body, type_ignores=[])) + ast.dump(ast.Tuple(elts=node.bases, ctx=ast.Load()))
    args = ast.dump(node.args) if hasattr(node, "args") else ""
    return args + ast.dump(ast.Module(body=body, type_ignores=[])) + (ast.dump(node.returns) if getattr(node, "returns", None) else "")


def _params(node: ast.AST) -> list[str]:
    """Pure logic. A function's parameter names, in order (none for a class)."""
    a = getattr(node, "args", None)
    if a is None:
        return []
    names = [x.arg for x in a.posonlyargs + a.args + a.kwonlyargs]
    names += [f"*{a.vararg.arg}"] if a.vararg else []
    names += [f"**{a.kwarg.arg}"] if a.kwarg else []
    return names


def definitions(text: str) -> dict[str, dict]:
    """Pure logic. Every class, function and method in a file (not functions nested in functions, as in the atlas)
    by its dotted name, each with its docstring, its code (stripped) and its parameters; and the file's own
    docstring under MODULE. A file that won't parse has none."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return {}
    out = {MODULE: {"doc": ast.get_docstring(tree) or "", "code": "", "params": []}}

    def visit(body, prefix=""):
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                name = prefix + node.name
                out[name] = {"doc": ast.get_docstring(node) or "", "code": _strip(node), "params": _params(node)}
                if isinstance(node, ast.ClassDef):
                    visit(node.body, name + ".")
    visit(tree.body)
    return out


def _public(names: set) -> set:
    """Pure logic. The names that aren't _private helpers (nor the file itself)."""
    return {n for n in names if n != MODULE and not n.rsplit(".", 1)[-1].startswith("_")}


def stale(old_text: str, new_text: str) -> list[dict]:
    """Pure logic. The docstrings in a file that may no longer be true: each definition in both versions whose code
    changed while its docstring stayed the same ({name, why, strong}), and the file's opening when public definitions
    came or went and it didn't change. A docstring that was edited, or code that didn't change, is never listed."""
    old, new = definitions(old_text), definitions(new_text)
    if not old or not new:
        return []
    out = []
    for name, now in new.items():
        before = old.get(name)
        if name == MODULE or before is None or now["code"] == before["code"] or now["doc"] != before["doc"]:
            continue
        added = [p for p in now["params"] if p not in before["params"]]
        gone = [p for p in before["params"] if p not in now["params"]]
        if added or gone:
            what = ", ".join([f"+{p}" for p in added] + [f"-{p}" for p in gone])
            out.append({"name": name, "strong": True,
                        "why": f"its parameters changed ({what}) and its docstring didn't"})
        else:
            out.append({"name": name, "strong": False, "why": "its code changed and its docstring didn't"})
    came = _public(set(new) - set(old))
    went = _public(set(old) - set(new))
    if (came or went) and new[MODULE]["doc"] == old[MODULE]["doc"] and old[MODULE]["doc"]:
        bits = ([f"{len(came)} added"] if came else []) + ([f"{len(went)} removed"] if went else [])
        out.append({"name": MODULE, "strong": False,
                    "why": f"definitions were {' and '.join(bits)}; does its opening still say what it holds?"})
    return sorted(out, key=lambda f: (not f["strong"], f["name"]))


def _git(*args: str, root: Path = ROOT) -> str:
    """Runs git in the repo and returns what it printed (empty when it fails)."""
    try:
        done = subprocess.run(["git", *args], cwd=str(root), capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=60)
    except (OSError, subprocess.SubprocessError):
        return ""
    return done.stdout if done.returncode == 0 else ""


def between(base: str = "HEAD", head: Optional[str] = None, root: Path = ROOT) -> list[dict]:
    """Every docstring that may be out of date in the Python files changed from `base` to `head` (the working tree
    when head is None), each {file, name, why, strong}. A file new since base is left out: tests/test_documentation.py
    already makes it document everything."""
    span = [base, head] if head else [base]
    files = [f for f in _git("diff", "--name-only", *span, "--", "*.py", root=root).splitlines()
             if f.split("/", 1)[0] in LAYERS]
    out = []
    for rel in files:
        old = _git("show", f"{base}:{rel}", root=root)
        if not old:
            continue
        if head:
            new = _git("show", f"{head}:{rel}", root=root)
        else:
            path = Path(root) / rel
            new = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
        out += [{"file": rel, **f} for f in stale(old, new)]
    return out


def describe(found: list[dict], limit: int = 40) -> str:
    """The list for a person or a reviewer: one line each, the strongest first; empty when there's nothing."""
    if not found:
        return ""
    lines = [f"- {f['file']}: {f['name']}: {f['why']}" + (" (check this one)" if f["strong"] else "")
             for f in found[:limit]]
    more = f"\n- and {len(found) - limit} more" if len(found) > limit else ""
    return "\n".join(lines) + more
