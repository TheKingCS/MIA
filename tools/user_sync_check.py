"""
tools.user_sync_check
=======================

A User Sync topic doesn't ship until it passes this
(docs/GLASSES_FIRST_BOOT_PLAN.md): the sample answers in
`data/user_sync_cases.json`, each with the chips they must produce, run
through the real extraction with the real model on this computer's
Ollama. Nothing else may come out: an extra chip is a guess, and fails.

Usage (from MIA's folder, with Ollama running):
    .venv\\Scripts\\python -m tools.user_sync_check                (qwen2.5:14b)
    .venv\\Scripts\\python -m tools.user_sync_check qwen3:14b
"""

from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.user_sync import NOTHING, SKIP, TOPICS  # noqa: E402

CASES = ROOT / "data" / "user_sync_cases.json"
BASE = "http://localhost:11434"


class Ollama:
    def __init__(self, model: str) -> None:
        self.model = model

    def generate(self, prompt: str) -> str:
        data = json.dumps({"model": self.model, "prompt": prompt, "stream": False, "options": {"temperature": 0}}).encode()
        request = urllib.request.Request(BASE + "/api/generate", data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=180) as response:
            return json.loads(response.read().decode()).get("response", "")


def missing_and_extra(chips: list[dict], case: dict) -> tuple[list[str], list[str]]:
    """Pure logic. What the case wanted and didn't get; what came out that it didn't want."""
    by_kind = {"recipes": "recipe.add", "missions": "mission.add", "memories": "memory.add"}
    missing, extra = [], []
    for group, kind in by_kind.items():
        got = [c["text"] for c in chips if c["kind"] == kind]
        wanted = case.get(group) or []
        missing += [w for w in wanted if not any(w.lower() in g.lower() for g in got)]
        extra += [g for g in got if not any(w.lower() in g.lower() for w in wanted)]
    return missing, extra


def run_case(context, case: dict) -> list[dict]:
    topic = TOPICS[case["topic"]]
    answers = [{"q": q, "a": a} for q, a in zip(topic["questions"], case["answers"])
               if not SKIP.fullmatch(a.strip(" .!")) and not NOTHING.fullmatch(a.strip(" .!"))]
    return (topic["extract"](context, answers) or []) if answers else []


def main() -> int:
    model = sys.argv[1] if len(sys.argv) > 1 else "qwen2.5:14b"
    context = SimpleNamespace(llm=Ollama(model), kitchen=None, missions=None)
    cases = json.loads(CASES.read_text(encoding="utf-8"))
    passed = 0
    for case in cases:
        started = time.monotonic()
        chips = run_case(context, case)
        missing, extra = missing_and_extra(chips, case)
        right = not missing and not extra
        passed += right
        print(f"{'pass' if right else 'FAIL'}  {time.monotonic() - started:4.1f}s  {case['topic']}: {case['name']}")
        if not right:
            print(f"      got {[c['text'] for c in chips]}; missing {missing}; extra {extra}")
    print(f"{passed} of {len(cases)} with {model}")
    return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    raise SystemExit(main())
