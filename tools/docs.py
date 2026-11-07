"""
tools.docs
============

Working down the documentation backlog (DEC-0104, core/code_atlas.py): see what a file still lacks, write the
docstrings (by reading the code: what it does, and how when that isn't plain), and put them in place.

    .venv\\Scripts\\python -m tools.docs next 15          the files with the most undocumented, engine first
    .venv\\Scripts\\python -m tools.docs show core/x.py   each undocumented definition with its code, to write from
    .venv\\Scripts\\python -m tools.docs apply docs.json  insert them: {"core/x.py": {"func": "...", "Cls.meth": "..."}}
    .venv\\Scripts\\python -m tools.docs stale [base]     docstrings that may be out of date since base (HEAD: your
                                                    uncommitted changes); run it before every commit (DEC-0110)

`apply` puts each docstring where Python expects it (after the whole signature, at the body's indentation), refuses
a definition that already has one, checks each file still parses, then lowers the ratchet
(`python -m core.code_atlas baseline`) and regenerates docs/ATLAS.md.
"""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ORDER = ("core", "server", "tools", "modules", "gui", "tests")  # the engine first: it's what a rebuild starts from


def definitions(tree: ast.Module) -> dict:
    """Every class, function and method in a parsed file by its dotted name ("func", "Cls", "Cls.meth"), not
    functions nested in functions (code_atlas counts the same ones)."""
    out = {}

    def visit(body, prefix=""):
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                out[prefix + node.name] = node
                if isinstance(node, ast.ClassDef):
                    visit(node.body, prefix + node.name + ".")
    visit(tree.body)
    return out


def insert(text: str, docs: dict[str, str]) -> str:
    """Pure logic. The file's text with each docstring put first in its definition's body (one ending in a quote
    gets a space, so it doesn't run into the closing quotes). Raises ValueError for a name that isn't there, one
    that already has a docstring, or a body on the def line itself."""
    tree = ast.parse(text)
    found = definitions(tree)
    lines = text.splitlines(keepends=True)
    inserts = []
    for name, doc in docs.items():
        node = found.get(name)
        if node is None:
            raise ValueError(f"{name}: not in the file")
        if ast.get_docstring(node):
            raise ValueError(f"{name}: already documented")
        first = node.body[0]
        if first.lineno == node.lineno:
            raise ValueError(f"{name}: its body is on the def line; document it by hand")
        if "\\" in doc:  # inside a plain docstring it's an escape: "\," warns, "\n" breaks the line
            raise ValueError(f"{name}: say it without a backslash")
        indent = " " * first.col_offset
        body = doc.strip().replace('"""', "'''").splitlines()
        if body and body[-1].endswith('"'):  # a closing quote would run into the docstring's own """
            body[-1] += " "
        if len(body) == 1:
            block = f'{indent}"""{body[0]}"""\n'
        else:
            block = (f'{indent}"""{body[0]}\n' + "".join(f"{indent}{l}\n" if l.strip() else "\n" for l in body[1:])
                     + f'{indent}"""\n')
        inserts.append((first.lineno - 1, block))
    for at, block in sorted(inserts, reverse=True):
        lines.insert(at, block)
    new = "".join(lines)
    ast.parse(new)  # still Python
    return new


def main(argv: list[str]) -> int:
    """The command line (see the module docstring): next, show, apply, stale."""
    from core import code_atlas

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if not argv:
        print(__doc__)
        return 1
    if argv[0] == "stale":
        from core import doc_freshness

        found = doc_freshness.between(argv[1] if len(argv) > 1 else "HEAD")
        if not found:
            print("Every changed definition's docstring was changed with it, or its code didn't change.")
            return 0
        print("Their code changed and their docstrings didn't: read each, and change the words where they're no "
              "longer true.")
        print(doc_freshness.describe(found, limit=200))
        return 1
    if argv[0] == "next":
        found = code_atlas.census()
        rank = lambda kv: (ORDER.index(kv[0].split("/")[0]) if kv[0].split("/")[0] in ORDER else 9, -len(kv[1]["undocumented"]))  # noqa: E731
        rows = sorted(((k, v) for k, v in found.items() if v["undocumented"]), key=rank)
        for name, info in rows[:int(argv[1]) if len(argv) > 1 else 15]:
            print(f"{len(info['undocumented']):4}  {name}")
        return 0
    if argv[0] == "show":
        path = ROOT / argv[1]
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines(keepends=True)
        for name, node in definitions(ast.parse(text)).items():
            if not ast.get_docstring(node) and not (isinstance(node, ast.FunctionDef)
                                                    and code_atlas.named_as_sentence(argv[1], node.name)):
                end = getattr(node, "end_lineno", node.lineno)
                print(f"### {name}  (lines {node.lineno}-{end})")
                print("".join(lines[node.lineno - 1:min(end, node.lineno + 40)]))
        return 0
    if argv[0] == "apply":
        combined = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
        for name, docs in combined.items():
            path = ROOT / name
            path.write_text(insert(path.read_text(encoding="utf-8"), docs), encoding="utf-8")
            print(f"{name}: {len(docs)} documented")
        found = code_atlas.census()
        code_atlas.save_baseline(found)
        code_atlas.ATLAS.write_text(code_atlas.render(found), encoding="utf-8")
        t = code_atlas.totals(found)
        print(f"ratchet lowered, atlas regenerated: {t['defs_documented']:,} of {t['defs']:,} documented")
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
