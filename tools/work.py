"""
tools.work
============

The team's development tasks from the command line (DEC-0068; the records are
`work/tasks/`, the rules `core/work_tasks.py`). Commit the task files with the
work, like any other change.

    .venv\\Scripts\\python -m tools.work list                 (what's open)
    .venv\\Scripts\\python -m tools.work list --ready         (what can start now)
    .venv\\Scripts\\python -m tools.work list --all
    .venv\\Scripts\\python -m tools.work show T-0001
    .venv\\Scripts\\python -m tools.work new "Title" --owner claude --depends T-0001 --files core/x.py
    .venv\\Scripts\\python -m tools.work claim T-0001 --by claude [--files core/x.py core/y.py]
    .venv\\Scripts\\python -m tools.work note T-0001 --by claude "what happened"
    .venv\\Scripts\\python -m tools.work done T-0001 --by claude --evidence "tests: 40 passed; commit abc123"
    .venv\\Scripts\\python -m tools.work move T-0001 blocked --by claude --why "needs a GitHub login"
"""

from __future__ import annotations

import argparse
import sys

from core import work_tasks as w


def _line(task: w.Task, tasks: dict) -> str:
    flag = "ready" if w.ready(task, tasks) else task.status
    owner = f" [{task.owner}]" if task.owner else ""
    after = f" (after {', '.join(task.depends)})" if task.depends and not w.ready(task, tasks) else ""
    return f"{task.id}  {flag:8} {task.title}{owner}{after}"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="tools.work")
    sub = parser.add_subparsers(dest="command", required=True)
    ls = sub.add_parser("list")
    ls.add_argument("--ready", action="store_true")
    ls.add_argument("--all", action="store_true")
    ls.add_argument("--owner", default="")
    sub.add_parser("show").add_argument("id")
    mk = sub.add_parser("new")
    mk.add_argument("title")
    for name in ("owner", "role", "source"):
        mk.add_argument(f"--{name}", default="")
    for name in ("depends", "files", "decisions"):
        mk.add_argument(f"--{name}", nargs="*", default=[])
    mk.add_argument("--about", default="", help="what it is (the body)")
    cl = sub.add_parser("claim")
    cl.add_argument("id")
    cl.add_argument("--by", required=True)
    cl.add_argument("--files", nargs="*")
    nt = sub.add_parser("note")
    nt.add_argument("id")
    nt.add_argument("text")
    nt.add_argument("--by", required=True)
    dn = sub.add_parser("done")
    dn.add_argument("id")
    dn.add_argument("--by", required=True)
    dn.add_argument("--evidence", required=True)
    mv = sub.add_parser("move")
    mv.add_argument("id")
    mv.add_argument("status")
    mv.add_argument("--by", required=True)
    mv.add_argument("--why", required=True)
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    tasks = w.load()
    try:
        if args.command == "list":
            shown = [t for t in tasks.values()
                     if (args.all or t.status not in w.FINISHED) and (not args.ready or w.ready(t, tasks))
                     and (not args.owner or t.owner == args.owner)]
            for task in shown:
                print(_line(task, tasks))
            if not shown:
                print("Nothing here.")
            return 0
        if args.command == "show":
            print(w._get(tasks, args.id).to_text())
            return 0
        if args.command == "new":
            task = w.new(tasks, args.title, owner=args.owner, role=args.role, source=args.source,
                         depends=args.depends, files=args.files, decisions=args.decisions,
                         body=args.about)
        elif args.command == "claim":
            task = w.claim(tasks, args.id, args.by, args.files)
        elif args.command == "note":
            task = w.note(w._get(tasks, args.id), args.by, args.text)
        elif args.command == "done":
            task = w.finish(tasks, args.id, args.by, args.evidence)
        else:
            task = w.move(tasks, args.id, args.status, args.by, args.why)
    except w.TaskError as problem:
        print(problem, file=sys.stderr)
        return 1
    print(w.save(task).relative_to(w.ROOT), "-", _line(task, {**tasks, task.id: task}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
