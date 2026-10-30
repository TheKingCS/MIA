"""
tools.intelligence_check
==========================

Zac's Intelligence Benchmark, asked for real: every question in
tests/intelligence_bench.py through the same steps a turn takes (a
question plan, a lookup answered by code, or the model with the tool
loop), on this computer's model and the person's real records. Read-only:
lookups run, but a change the model asks for is only noted, never made.

Writes `pc-check/intelligence.md` (each question, how it was answered,
how long it took, the answer) and `pc-check/intelligence.json`. Both
hold real answers about real records, so `pc-check/` stays out of git.

    .venv\\Scripts\\python -m tools.intelligence_check                 (every question)
    .venv\\Scripts\\python -m tools.intelligence_check B C              (categories)
    .venv\\Scripts\\python -m tools.intelligence_check --model qwen3:14b (another model)
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent


class _Warnings(logging.Handler):
    """The warnings a question raised: an answer replaced for an unchecked number, a failed lookup."""

    def __init__(self) -> None:
        super().__init__(logging.WARNING)
        self.seen: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.seen.append(record.getMessage())


def build_context(model: str = ""):
    from core.application import MIAApplication
    from core.config_manager import ConfigManager
    from core.core_runtime import build_core_context
    from core.event_bus import EventBus

    context = build_core_context(ConfigManager(), EventBus())
    app = MIAApplication.__new__(MIAApplication)
    app.context, app.config = context, context.config
    app._register_assistant_actions()
    if model and context.llm is not None:
        context.llm._backend._model = model
        if model.startswith("qwen3"):
            context.llm._backend._think = False  # answer directly, as Talk would need it to
    return context


def ask(context, qid: str, question: str) -> dict:
    """One question, the way a turn answers it, without changing anything."""
    from core import question_plans
    from core.assistant_chat import build_chat_request, named_tool
    from core.tool_loop import run as run_loop

    talk = SimpleNamespace(conversation_id=f"bench-{qid}", messages=[], mode=None, journal=False)
    started = time.monotonic()
    planned = question_plans.answer(context, talk, question)
    if planned is not None:
        said, sheet = planned
        return {"route": f"plan: {sheet.plan}", "answer": said, "lookups": sheet.looked_up,
                "seconds": round(time.monotonic() - started, 1)}
    direct = context.assistant_actions.direct_lookup(question, context)
    if direct is not None:
        said = context.assistant_actions.execute(context, direct.name, direct.direct_arguments(question))
        return {"route": f"code: {direct.name}", "answer": said, "lookups": [direct.name],
                "seconds": round(time.monotonic() - started, 1)}
    messages, tools = build_chat_request(context, talk, question)
    reply = run_loop(context, context.llm, messages, tools, question, named_tool(context, question, tools))
    out = {"route": f"model, {len(tools)} tools", "seconds": round(time.monotonic() - started, 1), "lookups": []}
    if reply is None:
        return {**out, "answer": "", "note": "the model didn't answer"}
    if reply.tool_calls:  # what it wanted to do: never done here
        return {**out, "answer": reply.content or "", "note": "wanted to " + ", ".join(c.name for c in reply.tool_calls)}
    return {**out, "answer": reply.content or ""}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("categories", nargs="*", help="A to G (default: all)")
    parser.add_argument("--model", default="", help="another model on this computer's Ollama")
    args = parser.parse_args()
    logging.disable(logging.INFO)
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # a piped Windows console is cp1252
    from tests.intelligence_bench import CATEGORIES, QUESTIONS

    context = build_context(args.model)
    model = args.model or context.config.get("llm.model", "")
    picked = [c.upper() for c in args.categories] or list(CATEGORIES)
    watcher = _Warnings()
    logging.getLogger().addHandler(watcher)
    rows = []
    for qid, question in QUESTIONS.items():
        if qid[0] not in picked:
            continue
        watcher.seen = []
        try:
            row = ask(context, qid, question)
        except Exception as exc:  # one question failing never stops the run
            row = {"route": "error", "answer": "", "seconds": 0, "lookups": [], "note": f"{type(exc).__name__}: {exc}"}
        row.update(id=qid, question=question, warnings=list(watcher.seen))
        rows.append(row)
        print(f"{qid:4} {row['seconds']:5.1f}s  {row['route'][:28]:28}  {'! ' if row['warnings'] or row.get('note') else ''}"
              f"{question[:60]}", flush=True)
        write(rows, model, quiet=True)  # after every question: a crash never loses the run
    write(rows, model)


def write(rows: list[dict], model: str, quiet: bool = False) -> None:
    from tests.intelligence_bench import CATEGORIES

    out = ROOT / "pc-check"
    out.mkdir(exist_ok=True)
    stem = "intelligence" + (f"-{model.replace(':', '-')}" if model else "")
    (out / f"{stem}.json").write_text(json.dumps({"model": model, "rows": rows}, indent=1), encoding="utf-8")
    lines = [f"# Intelligence Benchmark, asked for real ({model}, {time.strftime('%Y-%m-%d %H:%M')})", "",
             "| Category | Asked | Plan | Code | Model | Flagged | Median s | Max s |", "|---|---|---|---|---|---|---|---|"]
    for cat, name in CATEGORIES.items():
        mine = [r for r in rows if r["id"][0] == cat]
        if not mine:
            continue
        secs = sorted(r["seconds"] for r in mine)
        flagged = sum(1 for r in mine if r["warnings"] or r.get("note") or not r["answer"].strip())
        lines.append(f"| {cat} {name} | {len(mine)} | {sum(r['route'].startswith('plan') for r in mine)} | "
                     f"{sum(r['route'].startswith('code') for r in mine)} | {sum(r['route'].startswith('model') for r in mine)} | "
                     f"{flagged} | {secs[len(secs) // 2]} | {secs[-1]} |")
    lines += ["", "Flagged: an answer replaced for a number it couldn't back up, a change it wanted (never made), "
              "an error, or no answer.", ""]
    for r in rows:
        lines += [f"## {r['id']}. {r['question']}", "",
                  f"*{r['route']} · {r['seconds']} s" + (f" · looked up: {', '.join(r['lookups'])}" if r["lookups"] else "")
                  + (f" · {r['note']}" if r.get("note") else "") + "*", ""]
        lines += [f"> ⚠ {w}" for w in r["warnings"]] + ([""] if r["warnings"] else [])
        lines += [r["answer"].strip() or "(no answer)", ""]
    (out / f"{stem}.md").write_text("\n".join(lines), encoding="utf-8")
    if not quiet:
        print(f"\nWrote pc-check/{stem}.md and .json")


if __name__ == "__main__":
    main()
