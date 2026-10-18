"""
tools.pc_model_check
======================

Which model should MIA's home computer run? (DEC-0022.) Runs each model
through MIA's golden set (core/model_bench.py) with Ollama on this
computer, on its graphics card, exactly as Talk calls it, and writes
what it found to `pc-check/models.md` (paste that file's contents to
Claude, or just say "done": the numbers are in the file).

Usage (from MIA's folder, with Ollama running):
    .venv\\Scripts\\python tools\\pc_model_check.py                      (qwen2.5:14b and qwen2.5:32b)
    .venv\\Scripts\\python tools\\pc_model_check.py qwen2.5:14b 80        (one model, 80 cases)

The recommendation: the most accurate model; when two are within
RIGHT_ENOUGH points of each other, the faster one.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DEFAULT_MODELS = ("qwen2.5:14b", "qwen2.5:32b")
RIGHT_ENOUGH = 3  # percentage points


def _ollama(base: str, path: str, payload: dict | None = None, timeout: float = 30) -> dict:
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(base + path, data=data, headers={"Content-Type": "application/json"},
                                 method="POST" if data is not None else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode() or "{}")


def on_gpu(base: str, model: str) -> str:
    """How much of the loaded model sits in the graphics card's memory."""
    try:
        for m in _ollama(base, "/api/ps").get("models", []):
            if m.get("name", "").startswith(model) or m.get("model", "").startswith(model):
                size, vram = m.get("size") or 0, m.get("size_vram") or 0
                return f"{round(100 * vram / size)}% on the graphics card" if size else "unknown"
    except OSError:
        pass
    return "unknown"


def recommend(rows: list[dict]) -> dict | None:
    """Pure logic. The most accurate; within RIGHT_ENOUGH points, the faster."""
    rows = [r for r in rows if r.get("done")]
    if not rows:
        return None
    best = max(r["percent"] for r in rows)
    close = [r for r in rows if best - r["percent"] <= RIGHT_ENOUGH]
    return min(close, key=lambda r: (r["median_seconds"] or 1e9))


def main(argv: list[str]) -> int:
    from core import model_bench
    from core.config_manager import ConfigManager
    from core.llm_manager import OllamaBackend

    models = [a for a in argv if not a.isdigit()] or list(DEFAULT_MODELS)
    count = next((int(a) for a in argv if a.isdigit()), None)
    config = ConfigManager()
    base = str(config.get("llm.base_url", "http://localhost:11434")).rstrip("/")
    try:
        have = {m["name"] for m in _ollama(base, "/api/tags").get("models", [])}
    except OSError:
        print("Ollama isn't answering at " + base + ". Start Ollama (it's in the Start menu), then run this again.")
        return 1
    bench = model_bench.load_cases()
    rows = []
    for model in models:
        if model not in have:
            print(f"Getting {model} first (one time; a big download)...")
            _ollama(base, "/api/pull", {"name": model, "stream": False}, timeout=7200)
        backend = OllamaBackend(base, model, keep_alive="10m", temperature=0.0)
        print(f"\n{model}: loading...")
        started = time.monotonic()
        backend.chat([{"role": "user", "content": "Say ready."}], [], 600)
        load = round(time.monotonic() - started, 1)
        where = on_gpu(base, model)
        print(f"{model}: loaded in {load} s ({where}). Running MIA's test questions...")

        def progress(s):
            print(f"  {s['done']}/{s['total']}  right so far: {s['passed']}", end="\r", flush=True)

        summary = model_bench.run(backend, bench, count=count, timeout=300, progress=progress)
        print()
        done = summary["done"] or 1
        rows.append({"model": model, "done": summary["done"], "passed": summary["passed"],
                     "percent": round(100 * summary["passed"] / done, 1), "median_seconds": summary["median_seconds"],
                     "load_seconds": load, "gpu": where,
                     "misses": [(r["description"], r["detail"][:100]) for r in summary["results"] if not r["ok"]]})
    pick = recommend(rows)
    out = ROOT / "pc-check"
    out.mkdir(exist_ok=True)
    lines = ["# MIA's home computer: which model (DEC-0022)", "",
             f"{time.strftime('%Y-%m-%d %H:%M')} · {len(bench['cases']) if count is None else count} questions per model", "",
             "| Model | Right | Typical answer | Loading | Graphics card |", "|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['model']} | {r['passed']}/{r['done']} ({r['percent']}%) | {r['median_seconds']} s | "
                     f"{r['load_seconds']} s | {r['gpu']} |")
    if pick:
        lines += ["", f"**Recommended: {pick['model']}.** In config/config.json, under \"llm\", set "
                      f"\"model\": \"{pick['model']}\" (setup_home_pc does this when you say yes)."]
    for r in rows:
        if r["misses"]:
            lines += ["", f"## {r['model']}: missed", ""] + [f"- {d}: {why}" for d, why in r["misses"][:40]]
    (out / "models.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (out / "models.json").write_text(json.dumps({"rows": rows, "recommended": pick and pick["model"]}, indent=1),
                                     encoding="utf-8")
    print("\n".join(lines[:8 + len(rows)]))
    print(f"\nSaved: {out / 'models.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
