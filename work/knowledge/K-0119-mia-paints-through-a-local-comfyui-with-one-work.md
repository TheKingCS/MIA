---
id: K-0119
kind: implementation
title: MIA paints through a local ComfyUI, with one worker thread and a main-thread settle
status: confirmed
by: claude
created: 2026-11-08T12:58:21+00:00
concerns: core/art_studio.py, core/assistant_art_actions.py, web/shell.js, web/nexus3d.js, web/studio.js, server/app.py
from: dec:DEC-0138
---
core/art_studio.py talks to ComfyUI's HTTP API with urllib only: GET /system_stats (is it running), GET /object_info/CheckpointLoaderSimple (models; prefer config art.checkpoint, else one with 'xl', else the first), POST /prompt with an API-format txt2img graph (CheckpointLoaderSimple, two CLIPTextEncode, EmptyLatentImage at an SDXL bucket, KSampler dpmpp_2m/karras 28 steps cfg 6.5, VAEDecode, SaveImage), then poll GET /history/<prompt_id> and fetch GET /view?filename&subfolder&type. Use 127.0.0.1 (some browsers refuse localhost). Threading rule kept: core has no async, so the long-running painting gets one daemon thread scoped to this module; it only calls the engine and writes the PNG to art/staging/, updates its job under a lock, and calls core.live.bump() (thread-safe) so pages re-read the shell. The /api/shell endpoint calls settle(view) on the main thread under the turn lock: staged images move into the person's ArtStore and, for a 'background' request, use_as_backdrop() saves the person's own theme copy through theme.save (undoable). Themes gained a backdrop choice (art id + strength) kept by clean_theme only as a 12-hex id; exports drop it. web/shell.js puts the picture on a fixed .theme-art layer (masked in the middle) via MIA.image; MIAShell.roomLight() hands the 3D engine a promise of its URL, which nexus3d.js loads as a texture into the chamber pass with cover-fit. Tested against a stand-in ComfyUI (http.server on a free port). In the Studio, polling while a painting runs must redraw only the Backdrop section, or the 3D preview remounts every poll; and replaceChildren() turns null into the text 'null', so filter first.
