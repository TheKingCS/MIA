"""
core.self_audit
=================

MIA audits herself every week (DEC-0108; Zac, 2026-11-07: "a regular process
of auditing her own code and files and searching for ways to improve or beef
up whatever she is doing, make it more efficient, more well designed" and "a
regular audit for seeing how any of her existing infrastructure can be more
effectively interconnected").

Three audits, all read from the repository itself (no model, nothing guessed), so
the same code always gives the same findings:

1. **The code audit** (`code_findings()`): what could be clearer, leaner or
   better built. Functions too long to hold in mind (`LONG` lines), too many
   parameters, nesting too deep, the same body written twice in different
   places, a broad `except` that swallows an error without a word, very big
   files, and the TODOs left behind.
2. **The interconnection audit** (`connection_findings()`): where her parts
   don't reach each other yet. For every personal and household store: does
   it record life events (her history), can a link point at its records, can
   the Assistant read it, is it in the life state (her picture of a life),
   does a web page show it? And the events one part publishes that nothing
   hears, or that something listens for and nothing sends.
3. **The docs audit** (`core.inspection.repository_findings()`, T-0020,
   DEC-0071 point 1): where her docs disagree with the repository: a
   reference doc naming a file that isn't there, a decision recorded as
   built naming a missing file, a requirement not installed.

**What's done with them** (`weekly()`, from Night School once a week): the
report is kept (`data/dev/audit`), the best-practices series is regenerated
(core/practices.py), and at most one task a week for each audit is opened
for the top finding nobody's working on yet (`source: audit:...`), for the
usual paths: the runner, the lab, and Zac. A finding is a place to look, not
an order: some long functions are long for good reason, and the task says
so. `python -m tools.audit` shows the latest report.
"""

from __future__ import annotations

import ast
import hashlib
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from core.dev_store import DEV_DATA, DevStore

ROOT = Path(__file__).resolve().parent.parent
LAYERS = ("core", "server", "tools", "modules", "gui")  # her own code, not the tests
LONG = 80  # lines in one function
PARAMS = 8
NESTING = 5
BIG_FILE = 1500
SAME_BODY = 8  # lines: shorter repeats are usually just idiom
EVERY = timedelta(days=7)
WHO = "MIA (self-audit)"
_TODO = re.compile(r"#\s*(TODO|FIXME|XXX|HACK)\b", re.IGNORECASE)
_PAGE = re.compile(r"^def \w+_page\(", re.M)


def _files(root: Path = ROOT) -> list[Path]:
    """Every Python file of her own code."""
    return [p for layer in LAYERS for p in sorted((root / layer).rglob("*.py")) if "__pycache__" not in p.parts]


def _depth(node: ast.AST) -> int:
    """How deeply blocks nest inside a function (an if in a for in a with is 3)."""
    blocks = (ast.If, ast.For, ast.While, ast.With, ast.Try, ast.AsyncFor, ast.AsyncWith)
    best = 0
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
            continue
        inner = _depth(child)
        best = max(best, inner + 1 if isinstance(child, blocks) else inner)
    return best


def _silent(handler: ast.ExceptHandler) -> bool:
    """A handler for every error (bare or Exception) whose whole body is pass: the error disappears unseen."""
    broad = handler.type is None or (isinstance(handler.type, ast.Name) and handler.type.id in ("Exception",
                                                                                                "BaseException"))
    return broad and all(isinstance(s, ast.Pass) for s in handler.body)


def code_findings(root: Path = ROOT) -> list[dict]:
    """Every place the code audit would look, each {id, kind, file, line, name, detail, weight}, heaviest first."""
    out: list[dict] = []
    bodies: dict[str, list[tuple[str, int, str]]] = {}
    for path in _files(root):
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        try:
            tree = ast.parse(text)
        except SyntaxError:
            out.append({"kind": "unparsable", "file": rel, "line": 1, "name": rel, "detail": "doesn't parse",
                        "weight": 100})
            continue
        if len(lines) > BIG_FILE:
            out.append({"kind": "big_file", "file": rel, "line": 1, "name": rel,
                        "detail": f"{len(lines)} lines: could it be split by what each part does?",
                        "weight": len(lines) / BIG_FILE * 5})
        for i, line in enumerate(lines, 1):
            if _TODO.search(line):
                out.append({"kind": "todo", "file": rel, "line": i, "name": rel,
                            "detail": line.strip()[:120], "weight": 2})
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler) and _silent(node):
                out.append({"kind": "silent_except", "file": rel, "line": node.lineno, "name": rel,
                            "detail": "an error of any kind is swallowed without a log line", "weight": 4})
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            size = (node.end_lineno or node.lineno) - node.lineno + 1
            args = node.args
            count = len(args.args) + len(args.kwonlyargs) + len(args.posonlyargs) - (
                1 if args.args and args.args[0].arg in ("self", "cls") else 0)
            depth = _depth(node)
            if size > LONG:
                out.append({"kind": "long_function", "file": rel, "line": node.lineno, "name": node.name,
                            "detail": f"{size} lines: could it be named parts?", "weight": size / LONG * 3})
            if count > PARAMS:
                out.append({"kind": "many_params", "file": rel, "line": node.lineno, "name": node.name,
                            "detail": f"{count} parameters: would a small dataclass carry them better?",
                            "weight": count / PARAMS * 2})
            if depth >= NESTING:
                out.append({"kind": "deep_nesting", "file": rel, "line": node.lineno, "name": node.name,
                            "detail": f"blocks nested {depth} deep: early returns or a helper?", "weight": depth})
            if size >= SAME_BODY:
                body = ast.dump(ast.Module(body=[s for s in node.body if not (
                    isinstance(s, ast.Expr) and isinstance(getattr(s, "value", None), ast.Constant))],
                    type_ignores=[]))
                bodies.setdefault(hashlib.sha1(body.encode()).hexdigest(), []).append((rel, node.lineno, node.name))
    for places in bodies.values():
        files = {f for f, _l, _n in places}
        if len(files) > 1:
            first = places[0]
            out.append({"kind": "same_body", "file": first[0], "line": first[1], "name": first[2],
                        "detail": "the same body as " + ", ".join(f"{n} in {f}" for f, _l, n in places[1:4])
                                  + ": one shared function?", "weight": 6 * (len(places) - 1)})
    for f in out:
        f["id"] = f"{f['kind']}:{f['file']}:{f['name']}"
    return sorted(out, key=lambda f: (-f["weight"], f["file"], f["line"]))


# ------------------------------------------------------------------ interconnection

def _mentions(text: str, name: str) -> bool:
    """Whether code reaches a context store by name: context.name, or getattr(..., "name")."""
    return bool(re.search(rf"\.{re.escape(name)}\b", text) or re.search(rf"getattr\([^)]*[\"']{re.escape(name)}[\"']", text))


_IMPORT = re.compile(r"from core\.(\w+) import|from core import ([\w, ]+)|import core\.(\w+)")


def _imported(text: str) -> set[str]:
    """Pure logic. The core modules a text imports (from core.x import ..., from core import x, y)."""
    out = set()
    for a, b, c in _IMPORT.findall(text):
        out.update(n.strip() for n in ((a,) if a else (c,) if c else b.split(",")) if n.strip())
    return out


def _reaches(text: str, name: str, modules: dict[str, str]) -> bool:
    """Whether a surface's code reaches a store: by name itself, or through a core module it imports that does
    (one step: the web reaches the boss book through core/boss_battles.py)."""
    return _mentions(text, name) or any(_mentions(modules.get(m, ""), name) for m in _imported(text))


def _read(paths) -> str:
    """The text of every file, joined."""
    return "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in paths)


def assistant_text() -> str:
    """The code behind every Assistant tool: the desktop registry is built the way the app builds it (no Qt, no
    stores), and for each tool, its handler's own module, or only the handler when it lives in core/application.py
    (which names every store as it builds them, so the whole file would say every store is read)."""
    import inspect
    import logging

    from core.app_context import AppContext
    from core.application import MIAApplication
    from core.config_manager import ConfigManager
    from core.event_bus import EventBus

    was = logging.root.manager.disable
    logging.disable(logging.INFO)  # registering logs every tool
    try:
        app = MIAApplication.__new__(MIAApplication)
        app.context = AppContext(config=ConfigManager(), events=EventBus())
        app.config = app.context.config
        app._register_assistant_actions()
    finally:
        logging.disable(was)
    parts, modules = [], set()
    for action in app.context.assistant_actions._actions.values():
        handler = getattr(action.handler, "func", action.handler)  # a functools.partial's function
        module = getattr(handler, "__module__", "")
        try:
            if module == "core.application":
                parts.append(inspect.getsource(handler))
            elif module and module not in modules:
                modules.add(module)
                parts.append(inspect.getsource(inspect.getmodule(handler)))
        except (OSError, TypeError):
            continue
    return "\n".join(parts)


def store_connections(root: Path = ROOT, assistant: Optional[str] = None) -> list[dict]:
    """For every personal and household store: whether it records life events, can be linked, is read by the
    Assistant, is in the life state, and is shown by a web page. Read from the code, following one import into core
    (the modules that build every store, like core/application.py, don't count as reaching one); `assistant` is the
    tools' code when the caller already has it (assistant_text())."""
    import inspect

    from core import life_areas, links, personal_data

    core = root / "core"
    if assistant is None:  # the tools, the question plans and the quick spoken commands all answer by voice
        assistant = assistant_text() + _read(sorted(core.glob("question_*.py")) + [
            p for p in (core / "quick_commands.py",) if p.exists()])
    state = _read([core / "context_assembler.py"])
    # A web screen's data is put together in core: in a web_*.py file or any function named *_page (calendar_page,
    # freedom_page...), and served by server/app.py.
    pages = [p for p in sorted(core.glob("*.py"))
             if p.name.startswith("web_") or _PAGE.search(p.read_text(encoding="utf-8", errors="replace"))]
    web = _read(pages + [p for p in (core / "more_actions.py", root / "server" / "app.py") if p.exists()])
    linkable = {k.store for k in links.KINDS.values()}
    in_areas = {a.store for a in life_areas.AREAS}  # the life state's areas section reads these by its table
    modules = {p.stem: p.read_text(encoding="utf-8", errors="replace") for p in core.glob("*.py")
               if p.stem not in ("application", "personal_data", "app_context", "self_audit", "household_manager")}
    out = []
    seen = set()
    for scope, stores in (("personal", personal_data.PERSONAL_STORES), ("household", personal_data.HOUSEHOLD_STORES)):
        for name, cls in stores:
            if name in seen:
                continue
            seen.add(name)
            try:
                source = Path(inspect.getsourcefile(cls)).read_text(encoding="utf-8", errors="replace")
            except (TypeError, OSError):
                source = ""
            out.append({"store": name, "scope": scope, "class": cls.__name__,
                        "history": "life_events.record" in source or "life_events.on_change" in source,
                        "links": name in linkable,
                        "assistant": _reaches(assistant, name, modules),
                        "life_state": name in in_areas or _reaches(state, name, modules),
                        "web": _reaches(web, name, modules)})
    return out


CONNECTION_WHY = {
    "history": "it doesn't record life events, so her history and the Chronicle never see what changes in it",
    "links": "nothing can link to its records, so they can't depend on, serve or block anything",
    "assistant": "no Assistant tool reads it, so it can't be asked about by voice",
    "life_state": "it isn't in the life state, so her picture of a life leaves it out",
    "web": "no web page shows it, so the phone and the web can't see it",
}


# Connections a store goes without on purpose, and why: never offered as findings.
_SECRET = ("history", "links", "assistant", "life_state")
_RECORDS_ABOUT_HER = ("history", "links", "life_state", "web")  # her own machinery, not a person's life
BY_DESIGN: dict[str, tuple[tuple[str, ...], str]] = {
    "passwords": (_SECRET, "secrets never reach a log, a link, her voice or a summary"),
    "private_journal": (_SECRET, "private: read only when the person opens it"),
    "traces": (_RECORDS_ABOUT_HER + ("assistant",), "how she answered: hers to learn from"),
    "failures": (_RECORDS_ABOUT_HER, "the Fix-It Log: hers to learn from"),
    "ratings": (_RECORDS_ABOUT_HER + ("assistant",), "ratings of her answers: hers to learn from"),
    "life_events": (("history", "links"), "it is the history"),
    "personal_life_events": (("history", "links", "web", "assistant"), "it is the history"),
    "links": (("history", "links", "web"), "it is the links"),
    "conversations": (("history", "links", "life_state"), "the conversations themselves"),
    "communication": (("history", "links", "life_state"), "the gate for her own messages"),
    "notifications": (("history", "links", "life_state"), "the messages themselves"),
    "online_reminders": (("history", "links", "life_state", "web"), "held only until the internet is back"),
    "saga_moments": (("history", "links", "life_state", "assistant"), "kept for the Chronicles, which tell them"),
    "data_logger": (("history",), "sensor readings: too many, and too small, to be a life's history"),
    "freedom_log": (("history", "life_state"), "a daily balance snapshot; the fund itself is in finances"),
    "insights": (("history",), "what MIA noticed, kept by the gate's log, not the person's history"),
    "training": (("history", "life_state"), "the live workout; the workout it becomes is in the workout log"),
    "plaid": (("history", "links", "life_state"), "the bank connection; what it brings in is the budget's"),
}


def connection_findings(root: Path = ROOT, rows: Optional[list[dict]] = None) -> list[dict]:
    """Where her parts could reach each other: each store's missing connections (a store missing more weighs more)
    and the events nobody hears or nobody sends, heaviest first; a connection BY_DESIGN leaves out is never one.
    `rows` are store_connections() when already read."""
    from core import event_catalog

    out = []
    for row in rows if rows is not None else store_connections(root):
        wanted = [k for k in CONNECTION_WHY if k not in BY_DESIGN.get(row["store"], ((), ""))[0]]
        missing = [k for k in wanted if not row[k]]
        if missing:
            out.append({"id": f"store:{row['store']}", "kind": "store", "name": row["store"],
                        "file": f"core ({row['class']})", "missing": missing, "weight": len(missing) * 2,
                        "detail": "; ".join(CONNECTION_WHY[k] for k in missing)})
    orphans = event_catalog.orphans(event_catalog.catalogue(root))
    for name in orphans["unheard"]:
        out.append({"id": f"event:{name}", "kind": "unheard_event", "name": name, "file": "", "missing": ["heard"],
                    "weight": 3, "detail": f"`{name}` is published and nothing listens: who should react to it?"})
    for name in orphans["unsent"]:
        out.append({"id": f"event:{name}", "kind": "unsent_event", "name": name, "file": "", "missing": ["sent"],
                    "weight": 4, "detail": f"something listens for `{name}` and nothing sends it: dead code, or a "
                                          "missing publish?"})
    return sorted(out, key=lambda f: (-f["weight"], f["id"]))


def connected_share(rows: list[dict]) -> Optional[float]:
    """Pure logic. The share of the store connections that should exist that do (BY_DESIGN's left out)."""
    wanted = [(r, k) for r in rows for k in CONNECTION_WHY if k not in BY_DESIGN.get(r["store"], ((), ""))[0]]
    if not wanted:
        return None
    return round(sum(1 for r, k in wanted if r[k]) / len(wanted), 3)


# ------------------------------------------------------------------ the weekly run

def _store() -> DevStore:
    """Where the reports are kept."""
    return DevStore(DEV_DATA / "audit")


def latest(store: Optional[DevStore] = None) -> Optional[dict]:
    """The newest report, or None before the first."""
    found = (store or _store()).tail(1)
    return found[-1] if found else None


def due(now: Optional[datetime] = None, store: Optional[DevStore] = None) -> bool:
    """A week since the last audit, or never audited."""
    last = latest(store)
    if not last:
        return True
    try:
        at = datetime.fromisoformat(last["at"])
    except (KeyError, ValueError):
        return True
    now = now or datetime.now(timezone.utc)
    return now - (at if at.tzinfo else at.replace(tzinfo=timezone.utc)) >= EVERY


def _open(finding: dict, title: str, role: str, files: list[str], body: str, tasks_dir=None) -> Optional[str]:
    """One task for a finding, unless one is already open for it."""
    from core import work_tasks

    tasks = work_tasks.load(tasks_dir) if tasks_dir else work_tasks.load()
    source = f"audit:{finding['id']}"
    if any(t.source == source and t.status not in work_tasks.FINISHED for t in tasks.values()):
        return None
    task = work_tasks.new(tasks, title[:100], role=role, source=source, files=files, body=body)
    work_tasks.save(task, tasks_dir) if tasks_dir else work_tasks.save(task)
    return task.id


def _top_open(found: list[dict], tasks_dir=None) -> Optional[dict]:
    """The heaviest finding that has no task, open or finished, yet (a finished one was looked at)."""
    from core import work_tasks

    tasks = work_tasks.load(tasks_dir) if tasks_dir else work_tasks.load()
    looked = {t.source for t in tasks.values()}
    return next((f for f in found if f"audit:{f['id']}" not in looked and f["kind"] != "todo"), None)


def weekly(root: Path = ROOT, store: Optional[DevStore] = None, tasks_dir=None, open_tasks: bool = True,
           log=None, practices_out: Optional[Path] = None) -> dict:
    """All three audits (code, interconnection, docs), kept as a report; the best-practices series regenerated (into practices_out, else docs/practices);
    and up to one task for each audit's top finding nobody has looked at yet, noted in the activity log (`log`, else
    the usual one). Returns the report."""
    from core import inspection, practices, work_activity

    code = code_findings(root)
    rows = store_connections(root)
    connections = connection_findings(root, rows)
    docs = inspection.repository_findings(root)
    report = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "code": {"findings": len(code), "by_kind": _count(code), "top": code[:25]},
              "connections": {"findings": len(connections), "share": connected_share(rows), "by_kind": _count(connections),
                              "top": connections[:25]},
              "docs": {"findings": len(docs), "by_kind": _count(docs), "top": docs[:25]},
              "tasks": []}
    if open_tasks:
        top = _top_open(code, tasks_dir)
        if top:
            tid = _open(top, f"Audit: {top['kind'].replace('_', ' ')} in {top['name']}", "Software Engineer",
                        [top["file"]] if top["file"].endswith(".py") else [],
                        f"Found by the weekly code audit (core/self_audit.py, DEC-0108): `{top['file']}` line "
                        f"{top['line']}, {top['name']}: {top['detail']}\n\nLook, and make it better if it should be; "
                        "if it's this way for a good reason, say why in its docstring and close this.", tasks_dir)
            if tid:
                report["tasks"].append(tid)
        top = _top_open(connections, tasks_dir)
        if top:
            tid = _open(top, f"Interconnect: {top['name']}", "Software Engineer", [],
                        f"Found by the weekly interconnection audit (core/self_audit.py, DEC-0108): {top['name']}: "
                        f"{top['detail']}.\n\nFirst check it's so: the audit reads the code by name, and a store reached "
                        "through a variable can be missed. Then connect it where it should be, the way the other "
                        "stores do; where it shouldn't (private, or nothing to say), add it to BY_DESIGN in "
                        "core/self_audit.py with why, and close this.", tasks_dir)
            if tid:
                report["tasks"].append(tid)
        top = _top_open(docs, tasks_dir)
        if top:
            tid = _open(top, f"Docs: {top['detail']}", "Software Engineer", [top["file"]],
                        f"Found by the weekly docs audit (core/inspection.py repository_findings, T-0020): "
                        f"`{top['file']}` line {top['line']}: {top['detail']}.\n\nFix whichever is wrong: the doc "
                        "(the file moved, or was never built) or the repository (it should be there).", tasks_dir)
            if tid:
                report["tasks"].append(tid)
    try:
        report["practices"] = practices.write(practices_out) if practices_out else practices.write()
    except OSError as problem:
        report["practices"] = f"not written: {problem}"
    (store or _store()).append(report)
    line = (f"{len(code)} code findings, {len(connections)} connections to make, {len(docs)} docs to fix, "
            f"{len(report['tasks'])} tasks opened")
    try:
        work_activity.record(WHO, "audit", "", line, log) if log else work_activity.record(WHO, "audit", "", line)
    except OSError:
        pass  # the report itself is kept; the activity line is a convenience
    return report


def _count(found: list[dict]) -> dict:
    """Pure logic. How many findings of each kind."""
    out: dict[str, int] = {}
    for f in found:
        out[f["kind"]] = out.get(f["kind"], 0) + 1
    return dict(sorted(out.items()))
