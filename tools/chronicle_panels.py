"""
tools.chronicle_panels
========================

Draws an issue's panels with the local image model (T-0036: SD-Turbo as ONNX
on the GPU through DirectML). It runs in the image model's own environment,
kept apart from MIA's (`C:\\Users\\zacrh\\DevTools\\imagegen\\.venv`), so it
imports nothing from MIA:

    <imagegen python> tools/chronicle_panels.py <prompts.json> <out folder> <model folder> [<reference.png>]

prompts.json is [{"file", "prompt"}] (core/chronicle_issue.panel_prompts()). With a reference picture (the
series' look, chosen by Zac), each SDXL panel starts from it at REFERENCE_HOLD instead of from noise: the palette
and line work hold across an issue while the framing changes (T-0036: 0.7 locks the layout, 0.9 keeps only the
colours). The same character in every panel needs reference conditioning (an IP-Adapter): not yet.
"""

import json
import sys
import time
from pathlib import Path


REFERENCE_HOLD = 0.8  # img2img strength from the series' reference picture


def main(prompts_path: str, out_dir: str, model_dir: str, reference: str = "") -> int:
    import torch
    from optimum.onnxruntime import (ORTStableDiffusionPipeline, ORTStableDiffusionXLImg2ImgPipeline,
                                     ORTStableDiffusionXLPipeline)

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    # SDXL-Turbo or SD-Turbo, by what the folder says it is; both draw best at 512 px in 4 steps (T-0036)
    kind = json.loads((Path(model_dir) / "model_index.json").read_text(encoding="utf-8")).get("_class_name", "")
    start = None
    if "XL" in kind and reference and Path(reference).exists():
        from PIL import Image

        start = Image.open(reference).convert("RGB").resize((512, 512))
        pipeline = ORTStableDiffusionXLImg2ImgPipeline
    else:
        pipeline = ORTStableDiffusionXLPipeline if "XL" in kind else ORTStableDiffusionPipeline
    pipe = pipeline.from_pretrained(model_dir, provider="DmlExecutionProvider")
    for n, item in enumerate(json.loads(Path(prompts_path).read_text(encoding="utf-8"))):
        started = time.time()
        seed = torch.Generator().manual_seed(1000 + n)
        if start is not None:
            image = pipe(item["prompt"][:900], image=start, strength=REFERENCE_HOLD, num_inference_steps=4,
                         guidance_scale=0.0, generator=seed).images[0]
        else:
            image = pipe(item["prompt"][:900], num_inference_steps=4, guidance_scale=0.0, height=512, width=512,
                         generator=seed).images[0]
        image.save(out / item["file"])
        print(f"{item['file']}: {time.time() - started:.1f}s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:5]))
