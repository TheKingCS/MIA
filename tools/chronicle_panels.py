"""
tools.chronicle_panels
========================

Draws an issue's panels with the local image model (T-0036: SD-Turbo as ONNX
on the GPU through DirectML). It runs in the image model's own environment,
kept apart from MIA's (`C:\\Users\\zacrh\\DevTools\\imagegen\\.venv`), so it
imports nothing from MIA:

    <imagegen python> tools/chronicle_panels.py <prompts.json> <out folder> <model folder>

prompts.json is [{"file", "prompt"}] (core/chronicle_issue.panel_prompts()).
"""

import json
import sys
import time
from pathlib import Path


def main(prompts_path: str, out_dir: str, model_dir: str) -> int:
    import torch
    from optimum.onnxruntime import ORTStableDiffusionPipeline

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    pipe = ORTStableDiffusionPipeline.from_pretrained(model_dir, provider="DmlExecutionProvider")
    for n, item in enumerate(json.loads(Path(prompts_path).read_text(encoding="utf-8"))):
        started = time.time()
        image = pipe(item["prompt"][:900], num_inference_steps=4, guidance_scale=0.0, height=512, width=512,
                     generator=torch.Generator().manual_seed(1000 + n)).images[0]
        image.save(out / item["file"])
        print(f"{item['file']}: {time.time() - started:.1f}s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:4]))
