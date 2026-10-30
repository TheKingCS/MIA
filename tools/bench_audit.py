"""
tools.bench_audit
===================

What MIA's routing does today with each Intelligence Benchmark question
(tests/intelligence_bench.py, docs/INTELLIGENCE_BENCHMARK.md): answered
by code (a direct lookup), offered which tools, or left to the model with
no tools at all. No model is called; this is the routing alone, the same
decision build_chat_request() makes.

    python -m tools.bench_audit            # a Markdown table
    python -m tools.bench_audit --summary  # counts per category
"""

from __future__ import annotations

import argparse
import logging


def audit() -> list[dict]:
    from tests.assistant_registry import build_desktop_registry, demo_context, offered_tools
    from tests.intelligence_bench import QUESTIONS

    registry = build_desktop_registry()
    context = demo_context()
    rows = []
    for qid, question in QUESTIONS.items():
        direct = registry.direct_lookup(question)
        tools = offered_tools(registry, question, context)
        route = "code" if direct else ("tools" if tools else "model only")
        rows.append({"id": qid, "question": question, "route": route,
                     "direct": direct.name if direct else "", "tools": tools})
    return rows


def main() -> None:
    logging.disable(logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", action="store_true")
    args = parser.parse_args()
    rows = audit()
    if args.summary:
        from tests.intelligence_bench import CATEGORIES

        for cat, name in CATEGORIES.items():
            mine = [r for r in rows if r["id"].startswith(cat)]
            counts = {route: sum(r["route"] == route for r in mine) for route in ("code", "tools", "model only")}
            print(f"{cat} {name}: {len(mine)} questions; " + ", ".join(f"{k} {v}" for k, v in counts.items()))
        return
    print("| ID | Route today | Tool(s) |")
    print("|---|---|---|")
    for r in rows:
        shown = r["direct"] or ", ".join(r["tools"][:4]) + (f" (+{len(r['tools']) - 4})" if len(r["tools"]) > 4 else "")
        print(f"| {r['id']} | {r['route']} | {shown or '—'} |")


if __name__ == "__main__":
    main()
