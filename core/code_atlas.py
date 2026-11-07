"""
core.code_atlas
=================

Documentation for everything MIA is made of (DEC-0104, Zac 2026-11-06: "every
line of code ... should have documentation that explains what it is and what
it does and how it does it, so that if MIA ever needed to redo this entire
process herself, she could. And this should be an ongoing thing").

What it measures, read from the code with Python's own parser (`ast`), never
by hand:

- **A file** is documented when it opens with its docstring (Python) or its
  header comment (JavaScript `/* ... */`, Kotlin `/** ... */` or `//`): what it
  is, what it does, how.
- **A class, a function or a method** is documented when it has its own
  docstring. Functions nested inside another are the enclosing function's
  to explain, so they aren't counted.

What it keeps:

- `census()`: every file, how many of its classes and functions are
  documented, and its own first paragraph.
- `render()`: `docs/ATLAS.md`, the map of MIA file by file, layer by layer,
  generated, never edited by hand (a test keeps it current).
- `work/doc_baseline.json`: the ratchet. Each existing file's count of
  undocumented definitions may only go down; a file that isn't in it (a new
  one) must be fully documented. `tests/test_documentation.py` enforces both,
  and `dev.docs` (core/loops.py) watches the share documented, so the backlog
  is visible until it's gone.

    python -m core.code_atlas            rewrite docs/ATLAS.md
    python -m core.code_atlas baseline   rewrite the ratchet (after documenting: it can only go down)
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
PY_LAYERS = ("core", "server", "gui", "modules", "tools", "tests")
OTHER = (("web", "*.js"), ("android-phone/app/src/main/java", "*.kt"))
BASELINE = ROOT / "work" / "doc_baseline.json"
ATLAS = ROOT / "docs" / "ATLAS.md"


def _first_paragraph(text: str) -> str:
    """Pure logic. A docstring's or comment's first real paragraph, one line: what the file is."""
    lines = [l.strip(" *#/=-") .strip() for l in (text or "").strip().splitlines()]
    paras, cur = [], []
    for line in lines:
        if not line:
            if cur:
                paras.append(" ".join(cur))
                cur = []
            continue
        cur.append(line)
    if cur:
        paras.append(" ".join(cur))
    # skip a title line that is only the file's own dotted name ("core.loops")
    paras = [p for p in paras if not re.fullmatch(r"[\w.]+(\.(py|js|kt))?", p)]
    return paras[0][:300] if paras else ""


def py_file(path: Path) -> dict:
    """One Python file: its docstring's first paragraph, and its classes, functions and methods (not nested ones),
    each documented or not."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return {"about": "", "doc": False, "defs": 0, "undocumented": [], "lines": 0}
    undocumented, defs = [], 0

    def visit(body, prefix=""):
        nonlocal defs
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                defs += 1
                name = prefix + node.name
                if not ast.get_docstring(node):
                    undocumented.append(name)
                if isinstance(node, ast.ClassDef):
                    visit(node.body, name + ".")  # methods, not functions nested in functions
    visit(tree.body)
    doc = ast.get_docstring(tree) or ""
    return {"about": _first_paragraph(doc), "doc": bool(doc.strip()), "defs": defs, "undocumented": undocumented,
            "lines": len(path.read_text(encoding="utf-8", errors="replace").splitlines())}


def other_file(path: Path) -> dict:
    """A JavaScript or Kotlin file: documented when it opens with a header comment."""
    text = path.read_text(encoding="utf-8", errors="replace")
    head = text.lstrip()
    if path.suffix == ".kt":  # after the package line and the imports
        body = "\n".join(l for l in text.splitlines() if not l.startswith(("package ", "import ")) and l.strip())
        head = body.lstrip()
    comment = ""
    if head.startswith("/*"):
        comment = head[2:head.find("*/")] if "*/" in head else head[2:]
    elif head.startswith("//"):
        comment = "\n".join(l[2:] for l in head.splitlines() if l.startswith("//"))
    return {"about": _first_paragraph(comment), "doc": bool(comment.strip()), "defs": 0, "undocumented": [],
            "lines": len(text.splitlines())}


def census(root: Path = ROOT) -> dict[str, dict]:
    """Every file MIA is made of: relative path -> what py_file()/other_file() say about it."""
    out = {}
    for layer in PY_LAYERS:
        for path in sorted((root / layer).rglob("*.py")):
            if "__pycache__" not in path.parts:
                out[path.relative_to(root).as_posix()] = py_file(path)
    for folder, pattern in OTHER:
        for path in sorted((root / folder).rglob(pattern)) if (root / folder).exists() else []:
            if "vendor" not in path.parts:  # outside code keeps its own documentation (web/vendor/README.md)
                out[path.relative_to(root).as_posix()] = other_file(path)
    return out


def totals(found: dict[str, dict], layer: Optional[str] = None) -> dict:
    """Pure logic. How much is documented: files, and classes/functions/methods."""
    rows = [v for k, v in found.items() if layer is None or k.startswith(layer + "/")]
    defs = sum(v["defs"] for v in rows)
    missing = sum(len(v["undocumented"]) for v in rows)
    return {"files": len(rows), "files_documented": sum(1 for v in rows if v["doc"]), "defs": defs,
            "defs_documented": defs - missing, "lines": sum(v["lines"] for v in rows)}


def baseline(path: Path = BASELINE) -> dict[str, int]:
    """The ratchet as kept: file -> how many undocumented definitions it may still have."""
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("undocumented", {})
    except (OSError, ValueError):
        return {}


def save_baseline(found: dict[str, dict], path: Path = BASELINE) -> None:
    """Keep each file's count of undocumented definitions now (python -m core.code_atlas baseline)."""
    from core.atomic_write import atomic_write_text

    body = {"about": "core/code_atlas.py (DEC-0104): each file's undocumented classes and functions. It may only go "
                     "down; a file not listed must be fully documented. Rewrite with python -m core.code_atlas baseline.",
            "undocumented": {k: len(v["undocumented"]) for k, v in sorted(found.items()) if v["undocumented"]}}
    atomic_write_text(path, json.dumps(body, indent=1) + "\n")


def problems(found: dict[str, dict], kept: dict[str, int]) -> list[str]:
    """Pure logic. What the ratchet refuses: a file without its own description, a new file with anything
    undocumented, an old file with more undocumented than before."""
    out = []
    for name, info in found.items():
        if not info["doc"]:
            out.append(f"{name}: no description at the top (what it is, what it does, how)")
        allowed = kept.get(name, 0)
        if len(info["undocumented"]) > allowed:
            extra = info["undocumented"][:5]
            out.append(f"{name}: {len(info['undocumented'])} undocumented (allowed {allowed}), e.g. {', '.join(extra)}")
    return out


LAYER_ABOUT = {
    "core": "the engine: every store, rule and calculation; knows nothing of the screens",
    "server": "the web and phone API over the engine",
    "gui": "the desktop's Qt shell and dialogs",
    "modules": "the desktop's apps, one folder each",
    "tools": "command-line tools for the PC and the development platform",
    "tests": "the test suite: what each part must do",
    "web": "the web front end (the phone, the glasses, the desktop's web view)",
    "android-phone": "the Android app that carries MIA's engine and the glasses' link",
}


def render(found: Optional[dict[str, dict]] = None) -> str:
    """docs/ATLAS.md: every file, layer by layer, with what it is."""
    found = census() if found is None else found
    all_t = totals(found)
    lines = ["# MIA's atlas: every file, what it is", "",
             "*Generated from the code by `python -m core.code_atlas` (DEC-0104); never edit by hand, a test keeps it "
             "current. Each line is the file's own first paragraph: to change it, change the file. How to rebuild MIA "
             "from these, in what order: `docs/REBUILD.md`.*", "",
             f"{all_t['files']} files, {all_t['lines']:,} lines; {all_t['files_documented']} files describe themselves; "
             f"{all_t['defs_documented']:,} of {all_t['defs']:,} classes and functions are documented.", ""]
    for layer in (*PY_LAYERS, "web", "android-phone"):
        rows = {k: v for k, v in found.items() if k.startswith(layer + "/")}
        if not rows:
            continue
        t = totals(found, layer)
        lines += [f"## {layer}/: {LAYER_ABOUT.get(layer, '')}", "",
                  f"{t['files']} files, {t['lines']:,} lines"
                  + (f"; {t['defs_documented']:,} of {t['defs']:,} classes and functions documented" if t["defs"] else ""),
                  ""]
        for name, info in rows.items():
            gap = f" *({len(info['undocumented'])} undocumented)*" if info["undocumented"] else ""
            lines.append(f"- `{name}`: {info['about'] or '*(no description yet)*'}{gap}")
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys

    found = census()
    if sys.argv[1:] == ["baseline"]:
        old = baseline()
        grew = [k for k, v in found.items() if len(v["undocumented"]) > old.get(k, len(v["undocumented"]))]
        if old and grew:
            print("Not rewritten: these have more undocumented than the baseline allows:", ", ".join(grew[:10]))
            sys.exit(1)
        save_baseline(found)
        print("work/doc_baseline.json written")
    else:
        ATLAS.write_text(render(found), encoding="utf-8")
        print("docs/ATLAS.md written")
