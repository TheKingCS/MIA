"""
tools.weekly_bench
====================

The weekly benchmarks, graded and kept (build plan step 5, core/benchmarks.py):
Zac's Intelligence Benchmark (tools/intelligence_check.py), the golden
conversation corpus on the glasses and the phone (tools/conversation_check.py)
and the routing audit (tools/bench_audit.py). Read-only like those: lookups
run, a change she asks for is only noted. Only the grades are kept, in
`data/dev/benchmarks`; no answer leaves this PC or is written down.

    .venv\\Scripts\\python -m tools.weekly_bench              everything (Night School runs this weekly)
    .venv\\Scripts\\python -m tools.weekly_bench routing      only the routing audit (no chat model)
"""

from __future__ import annotations

import json
import logging
import sys


def intelligence(context) -> list[dict]:
    """Every intelligence question asked through the real turn, with the warnings each raised; a question that fails is kept as an error row and the run goes on."""
    from tests.intelligence_bench import QUESTIONS
    from tools.intelligence_check import _Warnings, ask

    watcher = _Warnings()
    logging.getLogger().addHandler(watcher)
    rows = []
    for qid, question in QUESTIONS.items():
        watcher.seen = []
        try:
            row = ask(context, qid, question)
        except Exception as exc:  # one question failing never stops the run
            row = {"route": "error", "seconds": 0, "note": f"{type(exc).__name__}"}
        row.update(id=qid, warnings=list(watcher.seen))
        rows.append(row)
    return rows


def corpus(context) -> list[dict]:
    """The golden conversation corpus asked on the glasses and the phone, each answer with its flags; a case that fails is kept as an error row."""
    from tools.conversation_check import CASES, ask, flags

    rows = []
    for surface in ("glasses", "phone"):
        for case in json.loads(CASES.read_text(encoding="utf-8"))["cases"]:
            try:
                row = ask(context, case, surface)
            except Exception as exc:
                row = {"route": "error", "said": "", "seconds": 0, "note": f"{type(exc).__name__}"}
            rows.append({"id": case["id"], "surface": surface, "route": row.get("route", ""),
                         "note": row.get("note", ""), "seconds": row.get("seconds", 0), "flags": flags(row.get("said", ""))})
    return rows


def main(argv: list[str]) -> int:
    """The weekly benchmarks (all kinds, or those named): routing, intelligence and the corpus, each graded and kept in core.benchmarks for the trend. Returns the exit code."""
    from core import benchmarks
    from tools.bench_audit import audit

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    logging.disable(logging.INFO)
    only = set(argv) or set(benchmarks.KINDS)
    if "routing" in only:
        benchmarks.keep("routing", [benchmarks.grade_route(r) for r in audit(embeddings=True)])
        print("routing: kept", flush=True)
    if only & {"intelligence", "corpus"}:
        from tools.intelligence_check import build_context

        context = build_context()
        model = context.config.get("llm.model", "")
        if "intelligence" in only:
            benchmarks.keep("intelligence", [benchmarks.grade(r) for r in intelligence(context)], model)
            print("intelligence: kept", flush=True)
        if "corpus" in only:
            benchmarks.keep("corpus", [benchmarks.grade(r) for r in corpus(context)], model)
            print("corpus: kept", flush=True)
    for kind in sorted(only):
        found = benchmarks.latest(kind)
        if found:
            print(f"{kind}: {len(found['rows'])} graded, {found['clean']} clean, {found['flagged']} flagged, "
                  f"{len(found['falls'])} fell since the run before", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
