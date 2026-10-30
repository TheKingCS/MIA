"""
tools.bench_audit
===================

What MIA's routing does today with each Intelligence Benchmark question
(tests/intelligence_bench.py, docs/INTELLIGENCE_BENCHMARK.md): a question
plan (core/question_plans.py: lookups by code, one answer), answered by
code (a direct lookup), offered which tools, or left to the model with no
tools at all. No chat model is called; plans are chosen with the
embedding model when this computer's Ollama has it, else by their words.

    python -m tools.bench_audit            # a Markdown table
    python -m tools.bench_audit --summary  # counts per category
"""

from __future__ import annotations

import argparse
import logging


ROUTES = ("plan", "code", "tools", "model only")


def _context(embeddings: bool):
    from types import SimpleNamespace

    from tests.assistant_registry import demo_context

    context = demo_context()
    if embeddings:
        from core.config_manager import ConfigManager
        from core.llm_manager import OllamaBackend

        url = ConfigManager().get("llm.base_url", "http://localhost:11434")
        context.llm = SimpleNamespace(_backend=OllamaBackend(url, "", "-1"), home=None)
    return context


def audit(embeddings: bool = False) -> list[dict]:
    from core.question_plans import match
    from tests.assistant_registry import build_desktop_registry, offered_tools
    from tests.intelligence_bench import QUESTIONS

    registry = build_desktop_registry()
    context = _context(embeddings)
    rows = []
    for qid, question in QUESTIONS.items():
        plan = match(context, question)
        direct = registry.direct_lookup(question)
        tools = offered_tools(registry, question, context)
        route = "plan" if plan else "code" if direct else ("tools" if tools else "model only")
        rows.append({"id": qid, "question": question, "route": route, "plan": plan.name if plan else "",
                     "direct": direct.name if direct else "", "tools": tools})
    return rows


def main() -> None:
    logging.disable(logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", action="store_true")
    parser.add_argument("--words", action="store_true", help="plans by their words only (as on the phone)")
    args = parser.parse_args()
    rows = audit(embeddings=not args.words)
    if args.summary:
        from tests.intelligence_bench import CATEGORIES

        for cat, name in CATEGORIES.items():
            mine = [r for r in rows if r["id"].startswith(cat)]
            counts = {route: sum(r["route"] == route for r in mine) for route in ROUTES}
            print(f"{cat} {name}: {len(mine)} questions; " + ", ".join(f"{k} {v}" for k, v in counts.items()))
        return
    print("| ID | Route today | Tool(s) |")
    print("|---|---|---|")
    for r in rows:
        shown = (f"plan: {r['plan']}" if r["plan"] else "") or r["direct"] or ", ".join(r["tools"][:4]) + (f" (+{len(r['tools']) - 4})" if len(r["tools"]) > 4 else "")
        print(f"| {r['id']} | {r['route']} | {shown or '—'} |")


if __name__ == "__main__":
    main()
