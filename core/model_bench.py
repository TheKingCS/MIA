"""
core.model_bench
==================

"Can the model on this device do MIA's job?" (2026-10-07, DEC-0019,
docs/PHONE_MODEL_TEST.md). Replays MIA's golden set (tests/
live_model_check.py) against a model and reports two things:

- **Right tool:** for each thing a person says, did the model call the
  tool MIA expects (with the person's actual words and numbers), call
  nothing when nothing was needed, or avoid anything destructive?
- **Speed:** how long reading the request and writing the answer took
  (llama.cpp's own timings when the server reports them).

The cases are frozen into a file by `tools/make_model_bench.py`: the
exact messages and offered tools MIA's request builder makes for each
(`core.assistant_chat.build_chat_request`, with the PC's full set of
tools). So a phone, whose engine has fewer tools, still asks its model
exactly what the PC would. Tool calls are never executed here.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Callable, Optional

CASES_FILE = Path(__file__).resolve().parent.parent / "data" / "model_bench_cases.json"


def arguments_match(arguments: dict, expected: dict) -> tuple[bool, str]:
    """Pure logic. Did the model pass the person's actual words/numbers?
    Strings match case-insensitively as substrings either way ("mower" vs
    "Riding Mower"); numbers must be equal. Only listed keys are checked."""
    for key, want in expected.items():
        got = arguments.get(key)
        if isinstance(want, (int, float)):
            try:
                if abs(float(str(got).replace(",", "").replace("$", "")) - float(want)) > 1e-6:
                    return False, f"argument {key}={got!r}, expected {want!r}"
            except (TypeError, ValueError):
                return False, f"argument {key}={got!r}, expected {want!r}"
        else:
            got_text = " ".join(got) if isinstance(got, list) else str(got or "")
            if want.lower() not in got_text.lower() and got_text.lower() not in want.lower():
                return False, f"argument {key}={got!r}, expected something like {want!r}"
            if not got_text:
                return False, f"argument {key} missing"
    return True, f"called with {arguments}"


def score(case: dict, called: list, arguments: Optional[dict], destructive: set) -> tuple[bool, str]:
    """Pure logic. One case's verdict, the same rules as the live check."""
    expected = case.get("expected")
    if expected is None:
        return called == [], f"expected no tool call, got {called}"
    if expected == "safe":
        return not any(name in destructive for name in called), f"expected no destructive tool call, got {called}"
    if called != [expected]:
        return False, f"expected [{expected}], got {called}"
    if case.get("arguments"):
        return arguments_match(arguments or {}, case["arguments"])
    return True, f"called {expected}"


def load_cases(path: Optional[Path] = None) -> dict:
    return json.loads(Path(path or CASES_FILE).read_text(encoding="utf-8"))


def pick(cases: list, count: Optional[int]) -> list:
    """Pure logic. `count` cases spread evenly over the set (every area,
    not just the first few), or all of them."""
    if not count or count >= len(cases):
        return list(cases)
    step = len(cases) / count
    return [cases[int(i * step)] for i in range(count)]


def run(backend, bench: dict, count: Optional[int] = None, timeout: float = 300.0,
        progress: Optional[Callable[[dict], None]] = None, should_stop: Callable[[], bool] = lambda: False) -> dict:
    """Runs the cases through `backend` (core.llm_manager's LLMBackend).
    Calls `progress(summary)` after each case. Returns the summary."""
    from core.llm_manager import LLMUnavailableError, _looks_like_malformed_tool_call

    cases = pick(bench["cases"], count)
    destructive = set(bench.get("destructive", []))
    results: list[dict] = []
    summary = {"total": len(cases), "done": 0, "passed": 0, "results": results, "stopped": False}
    for case in cases:
        if should_stop():
            summary["stopped"] = True
            break
        started = time.monotonic()
        error = ""
        try:
            reply = backend.chat(case["messages"], case["tools"], timeout)
            if not reply.tool_calls and _looks_like_malformed_tool_call(reply.content):
                reply = backend.chat(case["messages"], [], timeout)  # what MIA does too
            called = [call.name for call in reply.tool_calls]
            arguments = reply.tool_calls[0].arguments if reply.tool_calls else None
            ok, detail = score(case, called, arguments, destructive)
            answer = (reply.content or "")[:160]
        except LLMUnavailableError as problem:
            ok, detail, called, answer, error = False, "the model didn't answer", [], "", str(problem)[:200]
        timings = dict(getattr(backend, "last_timings", {}) or {})
        results.append({
            "description": case["description"], "prompt": case["prompt"], "ok": ok, "detail": detail,
            "called": called, "answer": answer, "error": error, "seconds": round(time.monotonic() - started, 2),
            "prompt_tokens": timings.get("prompt_n"), "prompt_ms": timings.get("prompt_ms"),
            "answer_tokens": timings.get("predicted_n"), "answer_ms": timings.get("predicted_ms"),
        })
        summary["done"] = len(results)
        summary["passed"] = sum(1 for r in results if r["ok"])
        summary.update(speed(results))
        if progress is not None:
            progress(summary)
    summary.update(speed(results))
    return summary


def speed(results: list) -> dict:
    """Pure logic. The middle (median) case's seconds, and reading and
    writing speeds in tokens per second over every case that reported them."""
    if not results:
        return {"median_seconds": None, "read_per_second": None, "write_per_second": None}
    seconds = sorted(r["seconds"] for r in results)
    read_tokens = sum(r["prompt_tokens"] or 0 for r in results)
    read_ms = sum(r["prompt_ms"] or 0 for r in results)
    write_tokens = sum(r["answer_tokens"] or 0 for r in results)
    write_ms = sum(r["answer_ms"] or 0 for r in results)
    return {
        "median_seconds": seconds[len(seconds) // 2],
        "read_per_second": round(1000 * read_tokens / read_ms, 1) if read_ms else None,
        "write_per_second": round(1000 * write_tokens / write_ms, 1) if write_ms else None,
    }
