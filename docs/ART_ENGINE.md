# MIA's image engine: ComfyUI on the PC (DEC-0138)

MIA paints backdrops and portal pictures on the PC's own graphics card (the RX 7900 XTX), through **ComfyUI**, a free
local image engine. MIA only talks to it on this computer (`http://127.0.0.1:8188`); nothing is sent anywhere else.
Until it's running, the Theme Studio and "paint me…" say so and point here.

*Checked 2026-11-08. AMD's ROCm now runs on Windows and ComfyUI ships with it, but AMD's own announcement names its
newest cards; the RX 7900 XTX works through the community route below. Expect some setup time the first time.*

## 1. Install ComfyUI

**Try first: the ComfyUI Desktop installer.** Download the Windows installer from comfy.org/download and run it. It
comes with AMD ROCm 7.1.1. When it starts, check its log says it found the RX 7900 XTX (not "CPU").

**If it doesn't use the card: the manual route** (from a working RX 7900 XTX guide):

1. Install the AMD HIP SDK 7.1, an AMD Adrenalin driver 25.20.01.17 or newer, Python 3.12 and Git.
2. Install `uv`, clone ComfyUI (`git clone https://github.com/comfyanonymous/ComfyUI`), and make its environment:
   `uv venv C:\ComfyUI\.venv --python 3.12`.
3. Install AMD's ROCm wheels for Windows (rocm-rel-7.1.1, from repo.radeon.com) and the ROCm builds of torch,
   torchvision and torchaudio, then ComfyUI's `requirements.txt`, each with `--python C:\ComfyUI\.venv\Scripts\python.exe`.
4. Before starting, set: `PYTORCH_NO_HIP_MEMORY_CACHING=1`, `HIP_VISIBLE_DEVICES=0`, `HSA_OVERRIDE_GFX_VERSION=11.0.0`.
5. Start it: `python main.py --listen 127.0.0.1 --port 8188`.

## 2. Give it a model

Put one SDXL checkpoint (a `.safetensors` file) in ComfyUI's `models\checkpoints` folder. The SDXL 1.0 base model from
Stability AI's Hugging Face page is a good start; any SDXL model whose licence you're happy with works. MIA picks an
SDXL one by itself; to choose, set `art.checkpoint` in MIA's `config\config.json` to its file name.

## 3. Check it from MIA

Open the Theme Studio. Under **Backdrop** it says "ComfyUI is running on AMD Radeon RX 7900 XTX" once MIA can reach it.
Then try: "Paint me a fantasy castle village at dusk for my background." A picture takes about a minute.

If ComfyUI runs on another port or computer, set `art.engine_url` in `config\config.json`
(`"art": {"engine_url": "http://127.0.0.1:8188", "checkpoint": ""}`).

## What MIA paints, and doesn't

Places and scenes, in her style for the use (a wide, atmospheric environment for a backdrop; a framed scene for a
portal), never with text, logos or people in them. She won't paint sexual content, gore or a real person's likeness.
Each painting is kept in your own folder (`data\profiles\<you>\art\`), with what it was painted from.

## Sources

- AMD x ComfyUI, ROCm on Windows (January 2026): https://www.amd.com/en/blogs/2026/amd-comfyui-advancing-professional-quality-generative-ai-ryzen-radeon.html
- ComfyUI on an RX 7900 XTX with native ROCm 7.1 on Windows: https://joshwaamein.github.io/posts/comfyui-amd-rx7900xtx-rocm-windows/
