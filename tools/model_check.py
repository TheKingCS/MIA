"""
tools.model_check
===================

Runs one of the phone's models (core/local_model.MODELS) through MIA's
golden set (core/model_bench.py) with llama.cpp's server on a computer,
started exactly as the phone starts it. CI's "Model check" workflow uses
it to compare the models' accuracy; speed belongs to the phone's own
Model test screen (docs/PHONE_MODEL_TEST.md).

Usage: python tools/model_check.py <model id> <cases> <llama-server> <models folder>
Prints a Markdown summary; writes model-check/<model id>.json.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main(model_id: str, cases: int, binary: str, folder: str) -> int:
    from core import model_bench
    from core.llm_manager import OpenAIBackend
    from core.local_model import MODELS_BY_ID, PORT, server_args

    model = MODELS_BY_ID[model_id]
    path = Path(folder) / model.file
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        print(f"Downloading {model.file}…", file=sys.stderr)
        urllib.request.urlretrieve(model.url, path)
    log = open(ROOT / "llama-server.log", "wb")
    started = time.monotonic()
    server = subprocess.Popen(server_args(binary, str(path), threads=os.cpu_count() or 4), stdout=log, stderr=subprocess.STDOUT)
    backend = OpenAIBackend(f"http://127.0.0.1:{PORT}", model_id)
    try:
        while not backend.is_available(2):
            if server.poll() is not None or time.monotonic() - started > 600:
                print((ROOT / "llama-server.log").read_text(errors="replace")[-2000:], file=sys.stderr)
                return 1
            time.sleep(1)
        load = round(time.monotonic() - started, 1)

        def progress(summary: dict) -> None:
            print(f"{summary['done']}/{summary['total']} done, {summary['passed']} right", file=sys.stderr)

        summary = model_bench.run(backend, model_bench.load_cases(), count=cases, progress=progress)
    finally:
        server.terminate()
    summary.update(model_id=model_id, load_seconds=load)
    out = ROOT / "model-check"
    out.mkdir(exist_ok=True)
    (out / f"{model_id}.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")

    print(f"## {model.name}\n")
    print(f"**Picked the right tool: {summary['passed']} of {summary['done']} "
          f"({round(100 * summary['passed'] / max(1, summary['done']))}%)**\n")
    print(f"On GitHub's computer ({os.cpu_count()} cores): typical case {summary['median_seconds']} s, reading "
          f"{summary['read_per_second']} tokens/s, writing {summary['write_per_second']} tokens/s, loading {load} s.\n")
    misses = [r for r in summary["results"] if not r["ok"]]
    if misses:
        print("| Missed | Said | What happened |\n|---|---|---|")
        for r in misses:
            print(f"| {r['description']} | {r['prompt']} | {r['detail'][:120]} |")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]))
