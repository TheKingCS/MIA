"""
tools.make_model_bench
========================

Freezes MIA's golden set (tests/live_model_check.py) into
data/model_bench_cases.json for the model test (core/model_bench.py,
docs/PHONE_MODEL_TEST.md): for each case, the exact messages and
offered tools MIA's request builder makes with the PC's full set of
tools, against the live check's placeholder records (an alarm called
"Wake Up", a riding mower...; never anyone's real data).

Run after changing the golden set, the assistant's tools or its system
prompt: `python -m tools.make_model_bench`. tests/test_model_bench.py
fails while the file is out of date.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def build() -> dict:
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    import tests.live_model_check as live  # isolates every data file in a temp folder on import
    from core.assistant_chat import build_chat_request

    context = live._build_context()
    live._seed_fixtures(context)
    cases = []
    for description, prompt, expected, *expected_args in live.GOLDEN_CASES:
        conversation = context.conversations.start_new_active_conversation()
        messages, tools = build_chat_request(context, conversation, prompt)
        cases.append({"description": description, "prompt": prompt, "expected": expected,
                      "arguments": expected_args[0] if expected_args else None,
                      "messages": messages, "tools": tools})
    return {"about": "MIA's golden set for the model test (tools/make_model_bench.py). Placeholder data only.",
            "destructive": sorted(context.assistant_actions.destructive_action_names()), "cases": cases}


def main() -> int:
    out = ROOT / "data" / "model_bench_cases.json"
    out.write_text(json.dumps(build(), indent=1, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
