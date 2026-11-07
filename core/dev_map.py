"""
core.dev_map
==============

MIA's architecture and her branches of growth, derived from the code and the
history (DEC-0078, T-0029; `docs/DEVELOPMENTAL_INDEPENDENCE_REVIEW.md`
section 6.2). Never hand-drawn: read from the repository with Python's own
`ast`, so nothing is run.

- **Layers**: core, modules, gui, server, tools, web, the phone, tests, with
  their files and lines.
- **Imports**: which core modules the most others depend on, and whether the
  layering rule CLAUDE.md sets holds: `core/` imports neither `gui/` nor
  `modules/`, and a module never imports another module. A break is listed
  with its file and line.
- **Where the docs and the code disagree** (DEC-0071 point 1, T-0020's first
  piece): a file named in the docs that say how things are now (CLAUDE.md,
  the architecture and module docs; not the logs, which name what was removed)
  that isn't there.
- **Growth**: finished tasks by the area of MIA they changed, by week, with
  the ledger's skills beside them (core/dev_ledger.py).
"""

from __future__ import annotations

import ast
import re
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LAYERS = {"core": "core", "modules": "modules", "gui": "gui", "server": "server", "tools": "tools", "web": "web",
          "android-phone": "phone", "tests": "tests"}
SKIP = {".venv", "__pycache__", "node_modules", "build", ".git", ".gradle"}
DOCS_CHECKED = ("CLAUDE.md", "docs/ARCHITECTURE.md", "docs/MODULE_SPEC.md", "docs/ADDING_MODULES.md")  # how things are now, not history
# Where the rule is crossed by design (CLAUDE.md says so), with why.
SANCTIONED = {
    "core/application.py": "boot sequencing lives here: it creates the Qt app and shows the screens",
    "core/module_manager.py": "module discovery scans modules/ by design",
    "core/module_validator.py": "it checks a module against modules.module_base before install",
}
SHARED = ("modules.module_base",)  # the base every module subclasses, not a module
NAMED = re.compile(r"`((?:core|tools|server|gui|web)/[\w./-]+\.(?:py|js|html|css))`")


def _files(root: Path, folder: str, suffixes: tuple[str, ...]) -> list[Path]:
    """Every file under a folder with one of these suffixes, skipping the SKIP folders (caches, venvs...); [] when the folder doesn't exist."""
    base = root / folder
    if not base.exists():
        return []
    return [p for p in base.rglob("*") if p.suffix in suffixes and not (set(p.parts) & SKIP)]


def _imports(path: Path) -> list[tuple[str, int]]:
    """Pure logic over one file. Each absolute import in it, with its line ([] when it doesn't parse); relative imports are left out."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out += [(a.name, node.lineno) for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            out.append((node.module, node.lineno))
    return out


def layering(root: Path = ROOT) -> list[dict]:
    """Every break of the layering rule: core reaching gui or modules, a module reaching another module."""
    breaks = []
    for path in _files(root, "core", (".py",)):
        if path.relative_to(root).as_posix() in SANCTIONED:
            continue
        for name, line in _imports(path):
            if name.split(".")[0] in ("gui", "modules"):
                breaks.append({"file": path.relative_to(root).as_posix(), "line": line, "imports": name,
                               "rule": "core/ never imports gui/ or modules/"})
    for path in _files(root, "modules", (".py",)):
        own = path.relative_to(root).parts[1] if len(path.relative_to(root).parts) > 2 else ""
        for name, line in _imports(path):
            parts = name.split(".")
            if name in SHARED or any(name.startswith(s + ".") for s in SHARED):
                continue
            if parts[0] == "modules" and len(parts) > 1 and parts[1] != own and (root / "modules" / parts[1]).is_dir():
                breaks.append({"file": path.relative_to(root).as_posix(), "line": line, "imports": name,
                               "rule": "a module never imports another module"})
    return breaks


def doc_mismatches(root: Path = ROOT) -> list[dict]:
    """Files the docs name that aren't in the repository."""
    out = []
    for doc in DOCS_CHECKED:
        path = root / doc
        if not path.exists():
            continue
        for named in sorted(set(NAMED.findall(path.read_text(encoding="utf-8", errors="replace")))):
            if not (root / named).exists():
                out.append({"doc": doc, "names": named})
    return out


def growth(tasks: dict) -> dict:
    """Finished tasks by the area they changed, and by ISO week."""
    areas: Counter = Counter()
    weeks: Counter = Counter()
    for t in tasks.values():
        if t.status != "done":
            continue
        top = {f.split("/")[0] for f in t.files if f} or {"(no files)"}
        for a in top:
            areas[LAYERS.get(a, a)] += 1
        try:
            year, week, _ = date.fromisoformat(t.updated or t.created).isocalendar()
            weeks[f"{year}-W{week:02d}"] += 1
        except ValueError:
            pass
    return {"areas": areas.most_common(), "weeks": sorted(weeks.items())}


def architecture(root: Path = ROOT, tasks: dict = None) -> dict:
    """The whole picture, for the dev window."""
    layers = []
    for folder, name in LAYERS.items():
        files = _files(root, folder, (".py", ".js", ".kt", ".html", ".css"))
        lines = 0
        for f in files:
            try:
                lines += sum(1 for _ in f.open(encoding="utf-8", errors="replace"))
            except OSError:
                pass
        layers.append({"layer": name, "folder": folder, "files": len(files), "lines": lines})
    inbound: Counter = Counter()
    for path in _files(root, "core", (".py",)) + _files(root, "modules", (".py",)) + _files(root, "server", (".py",)):
        for mod in {n for n, _ in _imports(path) if n.startswith("core.")}:
            inbound[mod] += 1
    if tasks is None:
        from core import work_tasks

        tasks = work_tasks.load()
    return {"layers": layers, "depended_on": inbound.most_common(12), "layering": layering(root),
            "sanctioned": [{"file": f, "why": why} for f, why in SANCTIONED.items()],
            "docs": doc_mismatches(root), "growth": growth(tasks)}
