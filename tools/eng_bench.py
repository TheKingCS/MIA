"""
tools.eng_bench
=================

Runs MIA's engineering bench (core/eng_bench.py) against a model on this computer's Ollama, to see whether it can
do a specialist's work (the local specialists plan, S0b; DEC-0197):

    python -m tools.eng_bench --model qwen2.5:14b
    python -m tools.eng_bench --model <another> --mode tools

It asks every task both ways (the model alone, and the model choosing MIA's calculators), prints each verdict as it
goes and a table by discipline at the end, and keeps the results in work/eng_bench/<model>.json so models can be
compared. It needs Ollama running with that model pulled; it changes nothing in MIA.
"""

from __future__ import annotations

import json
import re
import sys
import urllib.request
from datetime import datetime
from typing import Optional

from core import eng_bench
from core.data_root import WORK_DIR

URL = __import__("core.llm_manager", fromlist=["local_server_url"]).local_server_url() + "/api/generate"


# The most a model may write for one task. A thinking model (qwen3) otherwise thinks without end: on the PC's first
# run (2026-11-17) it spent over an hour on 36 tasks and never finished. Past this, its answer is cut and unreadable.
MAX_TOKENS = 3072


def ollama(model: str, url: str = URL, timeout: float = 600.0, max_tokens: int = MAX_TOKENS):
    """A function from a prompt to that model's reply, at temperature 0 so a run can be repeated, cut at
    max_tokens."""
    def ask(prompt: str) -> str:
        """One question to the model."""
        body = json.dumps({"model": model, "prompt": prompt, "stream": False,
                           "options": {"temperature": 0, "num_predict": max_tokens}}).encode()
        request = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=timeout) as answer:
            return json.loads(answer.read()).get("response", "")
    return ask


def table(summary: dict) -> str:
    """The summary as lines of text: one for each mode and discipline."""
    lines = []
    for mode, by_discipline in summary.items():
        for discipline, c in by_discipline.items():
            lines.append(f"{mode:6} {discipline:11} good {c['good'] * 100:5.1f}%  right {c['right']} asked {c['asked']} "
                         f"wrong {c['wrong']} guessed {c['guessed']} unreadable {c['unreadable']}  "
                         f"{c['seconds']:.1f} s a task")
    return "\n".join(lines)


def main(argv: Optional[list] = None) -> int:
    """`python -m tools.eng_bench --model NAME [--mode alone|tools] [--url URL]`: 0 when the run finished. Prints in
    UTF-8 whatever the console's own encoding (2026-11-17: gpt-oss writes a narrow no-break space, which Windows'
    console encoding can't print, and the run died half way)."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = list(argv if argv is not None else sys.argv[1:])

    def option(name: str, default: str = "") -> str:
        """The value after an option, or its default."""
        return args[args.index(name) + 1] if name in args and args.index(name) + 1 < len(args) else default
    model = option("--model")
    if not model:
        print(__doc__.strip())
        return 1
    modes = [option("--mode")] if option("--mode") else list(eng_bench.MODES)
    ask, rows = ollama(model, option("--url", URL)), []
    for mode in modes:
        rows += eng_bench.run(ask, mode, progress=lambda r: print(
            f"{r['mode']:6} {r['task']:4} {r['verdict']:10} got {r['got'] or '-'} (expected {r['expected']}) "
            f"{r['seconds']} s {r['detail']}"))
    result = {"model": model, "at": datetime.now().isoformat(timespec="seconds"), "summary": eng_bench.summary(rows),
              "rows": rows}
    out = WORK_DIR / "eng_bench" / (re.sub(r"[^\w.-]+", "_", model) + ".json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=1), encoding="utf-8")
    print("\n" + table(result["summary"]) + f"\nKept in {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
