"""
tools.live_sweep
==================

The live sweep, kept (brainstorm round 15, 2026-11-25: nine sweeps that day, each a scratch script, found most of the
day's bugs): everyday phrasings (`tests/live_sweep_corpus.py`) asked through the WHOLE turn
(core/assistant_turn.run_assistant_turn) on this computer's model, against made-up records in a throwaway folder
(tests/live_model_check's fixtures: never his data, and tools that change records only change those), and each
answer checked by code for the signs that kept showing up: no reply, raw JSON, a sheet or a tool's words said to him
("the fact sheet", "Answer from what you know"), a tool refusing a name it should know, the same line twice, or a
reply that says it did something with no tool run.

Writes `pc-check/live-sweep-<label>.md` (each phrasing, its route, tools, the reply and its flags); `pc-check/`
stays out of git. A flag is a lead for the next session, not a verdict: read the reply.

    .venv\\Scripts\\python -m tools.live_sweep                     (every phrasing)
    .venv\\Scripts\\python -m tools.live_sweep --area money        (one area)
    .venv\\Scripts\\python -m tools.live_sweep --label after-fix
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# what kept showing up wrong in the sweeps of 2026-11-25, each as (flag, a pattern on the reply)
FLAGS = (
    ("raw tool call", re.compile(r'^\s*[\[{]\s*"(?:name|function|tool)"|<tool_call>', re.I)),
    ("sheet words", re.compile(r"\bfact sheet\b|\bthe sheet\b|Answer from what you know|\(not yet confirmed\)", re.I)),
    ("not available", re.compile(r"\bisn't available on this MIA\b", re.I)),
    ("didn't know", re.compile(r"\bI don't have (?:that|any) information\b|\bI'm not sure what\b", re.I)),
    ("name refused", re.compile(r"\bI don't have (?:a|an) [\w ]+ called\b", re.I)),
    ("third person", re.compile(r"\b(?:Her|She) (?:offline library|library)\b|\bthe project he's\b", re.I)),
    ("echoed request", re.compile(r"^\s*I (?:want|would like|'d like) to (?:learn|know)\b", re.I)),
)


def flags_of(reply: str, tools_called: list) -> list:
    """Pure logic. The signs a reply shows (see `FLAGS`), plus none at all, a line said twice in a row, and a claim of
    a change with no tool run."""
    text = str(reply or "")
    found = [name for name, pattern in FLAGS if pattern.search(text)]
    if not text.strip():
        found.append("no reply")
    lines = [l.strip() for l in re.split(r"(?<=[.!?])\s+|\n+", text) if len(l.strip()) > 25]
    if any(a == b for a, b in zip(lines, lines[1:])):
        found.append("said twice")
    if not tools_called and re.search(r"\bI(?:'ve| have) (?:added|logged|set|scheduled|recorded|saved)\b", text):
        found.append("claimed a change")
    return found


def run(areas=None, label: str = "sweep") -> Path:
    """Asks every phrasing (of `areas`, or all) through the whole turn and writes the report; returns its path."""
    logging.disable(logging.CRITICAL)
    import os
    import tempfile

    # everything the turn keeps goes in a throwaway home, never his (set before MIA's modules read it)
    os.environ.setdefault("MIA_HOME", tempfile.mkdtemp(prefix="mia_live_sweep_"))
    import tests.live_model_check as fixtures
    from core.assistant_turn import run_assistant_turn
    from tests.live_sweep_corpus import CORPUS

    context = fixtures._build_context()
    fixtures._seed_fixtures(context)
    rows, flagged = [], 0
    for area, phrasings in CORPUS.items():
        if areas and area not in areas:
            continue
        for said in phrasings:
            turns = said if isinstance(said, (list, tuple)) else [said]
            conversation = context.conversations.start_new_active_conversation()
            for words in turns:
                started = time.monotonic()
                try:
                    turn = run_assistant_turn(context, conversation, words)
                    reply = turn.replies[-1] if turn.replies else ""
                    route, tools = turn.route, list(turn.tools_called or [])
                except Exception as problem:  # noqa: BLE001 - a crash is a finding, never the end of the sweep
                    reply, route, tools = f"CRASH {type(problem).__name__}: {problem}", "crash", []
                marks = flags_of(reply, tools) + (["crash"] if route == "crash" else [])
                flagged += bool(marks)
                rows.append((area, words, route, tools, reply, marks, time.monotonic() - started))
                print(f"[{area}] {words} -> {route} {tools} {'FLAGS: ' + ', '.join(marks) if marks else ''}")
                sys.stdout.flush()
    out = ROOT / "pc-check" / f"live-sweep-{label}.md"
    out.parent.mkdir(exist_ok=True)
    body = [f"# Live sweep: {label}", "", f"{len(rows)} turns, {flagged} flagged.", ""]
    for area, words, route, tools, reply, marks, seconds in rows:
        body += [f"## [{area}] {words}", f"- route: {route}; tools: {', '.join(tools) or 'none'}; {seconds:.1f}s",
                 f"- flags: {', '.join(marks) or 'none'}", "", "> " + reply.replace(chr(10), chr(10) + "> "), ""]
    out.write_text("\n".join(body), encoding="utf-8")
    print(f"\nWrote {out} ({flagged} of {len(rows)} flagged)")
    return out


def main(argv=None) -> int:
    """The command line: areas to ask (all by default) and the report's label."""
    parser = argparse.ArgumentParser(description="Ask everyday phrasings through the whole turn on this PC's model.")
    parser.add_argument("--area", nargs="*", default=None, help="areas of the corpus (money, home, ...)")
    parser.add_argument("--label", default="sweep", help="the report's name: pc-check/live-sweep-<label>.md")
    args = parser.parse_args(argv)
    run(set(args.area) if args.area else None, args.label)
    return 0


if __name__ == "__main__":
    sys.exit(main())
