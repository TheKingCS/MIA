---
id: K-0296
kind: decision
title: The image sets the PC's model, not config/default_config.json
status: confirmed
by: claude
created: 2026-11-18T10:19:04+00:00
concerns: os/Containerfile, os/poc/gpu_bench.py, config/default_config.json
from: task:FW-01, dec:DEC-0206, file:os/Containerfile
---
FW-01 (2026-11-18). The reference PC runs qwen2.5:14b at a 32k context (Q-68), but config/default_config.json is shared with the Pi and the general installer (deploy/finish_install.py pulls whatever it names), so changing it would make the Pi download a 9 GB model it can't run. The Containerfile edits the image's own copy of the default config instead, and CI checks the built image's value. The GPU bench (os/poc/gpu_bench.py) measures the same model: 70.2 tokens a second on Windows with flash attention and the 8-bit cache, so the Linux bar is 63 (90%).
