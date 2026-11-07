"""
tools.conversation_check
==========================

The golden conversation corpus, asked for real (DEC-0067; P5 of
docs/PERSONALITY_AND_ECOSYSTEM_AUDIT.md): greetings, jokes, frustration,
disagreement and the rest, through the same steps a turn takes, on this
computer's model, for each device she answers on. Read-only like
tools/intelligence_check.py: lookups run, a change she asks for is only noted.

Each answer is checked by code for what the audit measured: length (and
spoken seconds), filler openings, closing offers, lists, markdown, guilt, and
robot phrases. Zac rates a sample by hand; this is the part code can count.

Writes `pc-check/conversation-<label>.md` and `.json`, which hold real
answers, so `pc-check/` stays out of git.

    .venv\\Scripts\\python -m tools.conversation_check --label baseline
    .venv\\Scripts\\python -m tools.conversation_check --label phase1 --surface glasses phone
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from core.personality import guilt_in

ROOT = Path(__file__).resolve().parent.parent
CASES = ROOT / "data" / "conversation_cases.json"
WORDS_A_SECOND = 2.5  # about 150 words a minute, spoken

CHECKS = {
    "filler": re.compile(r"^(certainly|sure thing|sure|of course|absolutely|great question|i'?d be happy|i can help)\b", re.I),
    "offer": re.compile(r"(let me know[^.?!]*|anything else[^.?!]*|feel free[^.?!]*|is there anything[^.?!]*)[.?!]?\s*$", re.I),
    "list": re.compile(r"(^|\n)\s*([-*•]|\d+[.)])\s", re.M),
    "markdown": re.compile(r"\*\*|__|^#+\s", re.M),
    "shortfall": re.compile(r"\b(haven'?t (completed|finished|done)|still (haven'?t|need to finish)|you didn'?t|not (yet )?completed)\b", re.I),
    "stiff_ai": re.compile(r"\b(designed to|simulate conversation|language model|i do not experience|don'?t experience emotions)\b", re.I),
    "robot": re.compile(r"\b(i will now|i'll now|accessing|retrieving|processing your request|as an ai language model|"
                        r"i am unable to|unfortunately,? i)\b", re.I),
}


def flags(text: str) -> list[str]:
    """Pure logic. What the code checks found in one answer."""
    text = (text or "").strip()
    found = [name for name, pattern in CHECKS.items() if pattern.search(text)]
    if guilt_in(text):
        found.append("guilt")
    return found


def words(text: str) -> int:
    """Pure logic. How many words a text has."""
    return len((text or "").split())


def ask(context, case: dict, surface: str) -> dict:
    """One case, the way a turn answers it, without changing anything."""
    from core import question_plans
    from core.assistant_chat import build_chat_request, named_tool
    from core.tool_loop import run as run_loop

    history = [SimpleNamespace(role=r, content=c, privacy="", timestamp="") for r, c in case.get("before", [])]
    talk = SimpleNamespace(conversation_id=f"conv-{case['id']}", messages=history, mode=None, journal=False,
                           surface=surface)
    started = time.monotonic()
    planned = question_plans.answer(context, talk, case["say"])
    if planned is not None:
        full, sheet = planned
        route = f"plan: {sheet.plan}"
    else:
        messages, tools = build_chat_request(context, talk, case["say"])
        reply = run_loop(context, context.llm, messages, tools, case["say"], named_tool(context, case["say"], tools))
        route = f"model, {len(tools)} tools"
        if reply is None:
            return {"route": route, "full": "", "said": "", "seconds": round(time.monotonic() - started, 1),
                    "note": "the model didn't answer"}
        full = reply.content or ""
        if reply.tool_calls:
            route += " (wanted " + ", ".join(c.name for c in reply.tool_calls) + ")"
    said = compose(context, full, surface)
    return {"route": route, "full": full, "said": said, "seconds": round(time.monotonic() - started, 1)}


def compose(context, full: str, surface: str) -> str:
    """What she'd say on `surface`: the composer when it exists, else the answer as is."""
    try:
        from core.response_composer import compose as composer
    except ImportError:  # the baseline, before phase 1
        return full
    return composer(context, full, surface).say


def summary(rows: list[dict]) -> dict:
    """Pure logic. Per surface: how many cases, the median and 90th-percentile words, median spoken seconds, how many stayed within 25 words, median time, and how many each check flagged."""
    out = {}
    for surface in sorted({r["surface"] for r in rows}):
        mine = [r for r in rows if r["surface"] == surface]
        counts = sorted(words(r["said"]) for r in mine)
        out[surface] = {
            "cases": len(mine),
            "words_median": statistics.median(counts) if counts else 0,
            "words_p90": counts[int(0.9 * (len(counts) - 1))] if counts else 0,
            "spoken_seconds_median": round(statistics.median(counts) / WORDS_A_SECOND, 1) if counts else 0,
            "within_25_words": sum(1 for c in counts if c <= 25),
            "seconds_median": statistics.median(r["seconds"] for r in mine) if mine else 0,
            **{f"flag_{name}": sum(1 for r in mine if name in r["flags"]) for name in [*CHECKS, "guilt"]},
        }
    return out


def write(rows: list[dict], label: str, model: str) -> Path:
    """Writes the run to pc-check/conversation-<label>.json and .md (the summary, then each answer with its flags; real answers, so pc-check stays out of git). Returns the .md path."""
    out = ROOT / "pc-check"
    out.mkdir(exist_ok=True)
    stats = summary(rows)
    data = {"label": label, "model": model, "when": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "summary": stats, "rows": rows}
    (out / f"conversation-{label}.json").write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    lines = [f"# Conversation check: {label}", "", f"Model `{model}`. Real answers: keep out of git.", ""]
    for surface, s in stats.items():
        lines.append(f"**{surface}**: " + ", ".join(f"{k.replace('_', ' ')} {v}" for k, v in s.items()))
    lines.append("")
    for r in rows:
        lines += [f"## {r['id']} ({r['category']}, {r['surface']}) {r['seconds']}s, {r['route']}",
                  f"> {r['say']}", "", r["said"] or "(nothing)", ""]
        if r["said"] != r["full"]:
            lines += ["Full answer:", "", r["full"], ""]
        if r["flags"]:
            lines += ["Flags: " + ", ".join(r["flags"]), ""]
    path = out / f"conversation-{label}.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", default="run")
    parser.add_argument("--surface", nargs="*", default=["glasses", "phone"])
    parser.add_argument("--only", nargs="*", default=[], help="case ids or categories")
    args = parser.parse_args()
    logging.disable(logging.INFO)
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    from tools.intelligence_check import build_context

    context = build_context()
    model = context.config.get("llm.model", "")
    cases = json.loads(CASES.read_text(encoding="utf-8"))["cases"]
    if args.only:
        cases = [c for c in cases if c["id"] in args.only or c["category"] in args.only]
    rows = []
    for surface in args.surface:
        for case in cases:
            try:
                row = ask(context, case, surface)
            except Exception as exc:  # one case failing never stops the run
                row = {"route": "error", "full": "", "said": "", "seconds": 0, "note": f"{type(exc).__name__}: {exc}"}
            row.update(id=case["id"], category=case["category"], kind=case["kind"], say=case["say"], surface=surface,
                       flags=flags(row["said"]))
            rows.append(row)
            print(f"{surface:7} {case['id']:6} {row['seconds']:5.1f}s {words(row['said']):4d}w "
                  f"{' '.join(row['flags'])}", flush=True)
            write(rows, args.label, model)
    print(json.dumps(summary(rows), indent=1))


if __name__ == "__main__":
    main()
