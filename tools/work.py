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
    .venv\\Scripts\\python -m tools.work done T-0001 --by claude --tests tests/test_x.py   (runs them: the evidence)
    .venv\\Scripts\\python -m tools.work history "relay"            (search who did what)
    .venv\\Scripts\\python -m tools.work history --task T-0001
    .venv\\Scripts\\python -m tools.work resume T-0001              (where an interrupted task got to)
    .venv\\Scripts\\python -m tools.work resolve T-0001 --by claude --how "why" --lesson "what the reviewer should check"

Every change is recorded in work/activity.jsonl (core/work_activity.py).
"""

from __future__ import annotations

import argparse
import sys

from core import work_activity as activity
from core import work_tasks as w


def _line(task: w.Task, tasks: dict) -> str:
    """Pure logic. A task in one line: its id, ready or its status, title, owner, and what it waits on."""
    flag = "ready" if w.ready(task, tasks) else task.status
    owner = f" [{task.owner}]" if task.owner else ""
    waiting = [d for d in task.depends if tasks.get(d) is None or tasks[d].status != "done"]
    after = f" (after {', '.join(waiting)})" if task.status == "open" and waiting else ""
    return f"{task.id}  {flag:8} {task.title}{owner}{after}"


def main(argv=None) -> int:
    """The work-queue command line: list (ready, all, by owner), show, new, claim and the rest of a task's steps. Returns the exit code."""
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
    dn.add_argument("--evidence", default="")
    dn.add_argument("--tests", nargs="*", default=[], help="test files to run; their result is the evidence")
    hs = sub.add_parser("history")
    hs.add_argument("text", nargs="?", default="")
    hs.add_argument("--task", default="")
    hs.add_argument("--who", default="")
    sub.add_parser("resume").add_argument("id")
    sub.add_parser("agents")
    rn = sub.add_parser("run", help="work a task as a role, through the lab, as far as review")
    rn.add_argument("id")
    rn.add_argument("--as", dest="role", required=True)
    rv_ = sub.add_parser("review", help="an independent review of a task waiting for one")
    rv_.add_argument("id")
    rv_.add_argument("--as", dest="role", required=True)
    sub.add_parser("approve", help="Zac only, at the keyboard: merge a reviewed task").add_argument("id")
    rs = sub.add_parser("resolve", help="answer a review's objection: what changed, or why it doesn't hold")
    rs.add_argument("id")
    rs.add_argument("--by", required=True)
    rs.add_argument("--how", required=True)
    rs.add_argument("--lesson", default="", help="what the reviewer should check next time, if it was wrong")
    lr = sub.add_parser("learn", help="MIA writes what a finished task taught (work/knowledge, DEC-0073)")
    lr.add_argument("ids", nargs="*", help="task ids; none means every finished task not yet written up")
    sub.add_parser("knowledge", help="what the team has learned, newest last")
    lp = sub.add_parser("loops", help="MIA's improvement loops on this PC (DEC-0094): list, or --run now")
    lp.add_argument("--run", action="store_true")
    ms = sub.add_parser("mission", help="the council's missions (DEC-0076): new, start, pause, done, list")
    ms.add_argument("act", choices=["new", "start", "pause", "done", "list"])
    ms.add_argument("what", nargs="?", default="", help="the goal (new) or the mission's id")
    ms.add_argument("--scope", nargs="*", default=[], help="paths its changes may touch (new)")
    ms.add_argument("--tasks", type=int, default=5)
    ms.add_argument("--hours", type=float, default=8.0)
    ms.add_argument("--calls", type=int, default=60)
    rr = sub.add_parser("runner", help="work an active mission: one step, or until it stops")
    rr.add_argument("id")
    rr.add_argument("--once", action="store_true")
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
        if args.command == "history":
            for e in activity.search(args.text, args.task, args.who):
                print(f"{e['at']}  {e['who']:8} {e['action']:7} {e['task']:7} {e['detail']}")
            return 0
        if args.command == "agents":
            from core.work_agents import load as load_agents

            registry = load_agents()
            for role in registry.roles.values():
                provider = registry.providers[role.provider]
                here = "here" if provider.available() else "not here"
                print(f"{role.role:24} {role.tier:10} {role.provider:12} ({here})")
            return 0
        if args.command == "run":
            from core import work_loop
            from core.work_agents import AgentError, load as load_agents

            try:
                stopped = work_loop.run(args.id, args.role, load_agents())
            except (AgentError, work_loop.LoopError) as problem:
                print(f"Stopped: {problem}", file=sys.stderr)
                return 1
            print(_line(w.load()[args.id.upper()], w.load()), f"(stopped at {stopped}: waiting for review and Zac)")
            return 0
        if args.command == "resolve":
            from core import work_review

            try:
                count = work_review.resolve(args.id, args.by, args.how, confirm=input, lesson=args.lesson)
            except work_review.ReviewError as problem:
                print(f"Stopped: {problem}", file=sys.stderr)
                return 1
            print(f"{args.id.upper()}: {count} objection(s) answered and kept in the history.")
            return 0
        if args.command in ("review", "approve"):
            from core import work_review
            from core.work_agents import AgentError, load as load_agents

            try:
                if args.command == "review":
                    said = work_review.review(args.id, args.role, load_agents(), ask=work_review.ask_provider,
                                              diff=work_review.lab_diff)
                    print(f"{args.id.upper()}: {said}")
                else:
                    merged = work_review.approve(args.id, confirm=input)
                    print(f"{args.id.upper()} approved and merged as {merged[:10]}. Restart MIA to load it.")
            except (AgentError, work_review.ReviewError) as problem:
                print(f"Stopped: {problem}", file=sys.stderr)
                return 1
            return 0
        if args.command == "mission":
            from core import work_runner

            try:
                if args.act == "list":
                    for m in work_runner.missions().values():
                        used = work_runner.spent(m)
                        print(f"{m.id}  {m.status:7} {m.goal}  (tasks {used['tasks']}/{m.tasks}, "
                              f"{used['hours']:g}/{m.hours:g} h; scope {', '.join(m.scope)})")
                elif args.act == "new":
                    m = work_runner.new(args.what, args.scope, tasks=args.tasks, hours=args.hours, calls=args.calls)
                    print(f"{m.id}: {m.goal} (paused until you start it: python -m tools.work mission start {m.id})")
                else:
                    status = {"start": "active", "pause": "paused", "done": "done"}[args.act]
                    m = work_runner.set_status(args.what, status, "zac", confirm=input if status == "active" else None)
                    print(f"{m.id} is {m.status}." + (f" Run it: python -m tools.work runner {m.id}" if status == "active" else ""))
            except ValueError as problem:
                print(f"Stopped: {problem}", file=sys.stderr)
                return 1
            return 0
        if args.command == "runner":
            import time

            from core import work_runner
            from core.work_agents import load as load_agents

            while True:
                said = work_runner.step(args.id, load_agents())
                print(said, flush=True)
                if args.once or said.startswith(("stop", "No mission")) or " is paused" in said or " is done" in said:
                    return 0
                if said.startswith(("hold", "idle")) or "usage limit" in said:
                    time.sleep(300)  # nothing to do now: look again in five minutes
        if args.command == "loops":
            from core import loops

            if args.run:
                loops.run(None, "device", force=True, heavy=True)  # the suite and the audit too
            for l in loops.summary(None, "device"):
                value = "—" if l["value"] is None else f"{l['value']:g}{l['unit']}"
                print(f"{l['id']:22} {l['state']:6} {value:>8}  {l['why'] or l['detail']}"
                      + (f"  -> {l['task']}" if l["task"] else ""))
            return 0
        if args.command == "knowledge":
            from core import dev_knowledge

            for e in dev_knowledge.entries():
                print(f"{e['id']}  {e.get('status', ''):9} {e['kind']:17} {e['title']}  ({', '.join(e.get('from') or [])})")
            return 0
        if args.command == "learn":
            from core import dev_knowledge

            ids = [i.upper() for i in args.ids] or [t.id for t in tasks.values() if t.status == "done"]
            for task_id in ids:
                try:
                    kept = dev_knowledge.retrospective(task_id)
                except OSError as problem:
                    print(f"{task_id}: the local model didn't answer ({problem})", file=sys.stderr)
                    return 1
                for e in kept:
                    activity.record("mia", "learn", task_id, f"{e['id']} {e['kind']}: {e['title']}")
                print(f"{task_id}: " + ("; ".join(f"{e['id']} {e['title']}" for e in kept) or "nothing new"))
            return 0
        if args.command == "resume":
            task = w._get(tasks, args.id)
            step = activity.last_step(task.id)
            print(_line(task, tasks))
            print("Last step:", f"{step['at']} {step['who']} {step['action']}: {step['detail']}" if step else "nothing recorded")
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
            evidence = [args.evidence.strip()] if args.evidence.strip() else []
            if args.tests:
                passed, summary = activity.run_tests(args.tests)
                if not passed:
                    raise w.TaskError(f"The tests didn't pass ({summary}), so it isn't done.")
                evidence.append(f"tests ({' '.join(args.tests)}): {summary}")
            if evidence:
                evidence.append("commit " + activity.commit())
            task = w.finish(tasks, args.id, args.by, "; ".join(evidence))
        else:
            task = w.move(tasks, args.id, args.status, args.by, args.why)
    except w.TaskError as problem:
        print(problem, file=sys.stderr)
        return 1
    w.save(task)
    detail = {"new": task.title, "claim": "files: " + ", ".join(task.files), "note": getattr(args, "text", ""),
              "done": task.body.rsplit("Evidence: ", 1)[-1], "move": f"{task.status}: {getattr(args, 'why', '')}"}
    activity.record(getattr(args, "by", "") or task.owner or "?", args.command, task.id, detail.get(args.command, ""))
    print(_line(task, {**tasks, task.id: task}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
