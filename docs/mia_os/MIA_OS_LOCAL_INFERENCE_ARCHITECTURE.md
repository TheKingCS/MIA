# MIA OS: local inference (Prompt 07 §5)

*Claude (Opus), 2026-11-17. Planning only. Hardware facts are Prompt 06's.*

## 1. What runs where (verified 2026-11-17)

| Device | Runner | Models |
|---|---|---|
| PC (RX 7900 XTX 24 GB) | Ollama (version read from its API on the PC), ROCm on Windows; ROCm 7.2 and `ollama-rocm` 0.24 on Fedora 45 (PoC 2) | everyday `qwen2.5:14b`; specialists `qwen2.5:32b`, `qwen3:14b`, `qwen3-coder:30b`; vision `qwen2.5vl:7b`; `nomic-embed-text`; `llama3.2` 3B; reviewers to bench: `gpt-oss:20b`, `mistral-small:24b` |
| Phone (Galaxy A54) | llama.cpp's server inside the app | 0.5B to 1.5B |
| Model node (DEC-0202, when bought) | Ollama or llama.cpp's server | 70B dense, 120B MoE, two families at once |
| Pi + AI HAT+ 2 (later) | Hailo's runtime | 1B to 3B |

## 2. The PC's settings (proposed; measured before and after)

| Setting | Now | Proposed | Why | Evidence |
|---|---|---|---|---|
| Flash attention | automatic where supported | force on (`OLLAMA_FLASH_ATTENTION=1`) | needed for a quantized cache | Ollama FAQ (as quoted) |
| Attention (K/V) cache | f16 | `q8_0` | about half the memory with little loss: the everyday 14B and another 14B fit together | Ollama FAQ (as quoted); global to all models |
| Loaded models | default | `OLLAMA_MAX_LOADED_MODELS=2` | the everyday model stays while a specialist loads | — |
| Parallel requests per model | default 1 | 1 now; W1 measures 2 to 4 for the Workroom | memory scales with parallel × context | Ollama FAQ (as quoted) |
| Keep-alive | everyday model `-1` (always) | as is; specialists 10 minutes | avoids cold starts on conversation | `config/config.json` |

**Re-bench after any change** (`tools.eng_bench`, the golden set): a setting that lowers a score is reverted.

## 3. Choosing a runner

| Runner | For | Against | Decision |
|---|---|---|---|
| Ollama | packaged in Fedora; one API for text, chat, tools, embeddings, vision; model library | one queue, limited batching | **primary** |
| llama.cpp server | the phone; Vulkan anywhere; OpenAI-compatible | fewer conveniences | **phone and fallback** |
| vLLM | real batching for many agents | heavier; narrower ROCm support on consumer cards | **watch** (Workroom) |
| ONNX Runtime | Kokoro TTS | ROCm execution provider deprecated in favour of MIGraphX (ROCm 7.1+) | **voice only** |

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-INT-005 | Inference settings shall be changed only with a bench run before and after, and reverted when a score drops. | Must | R1 | PC | New | M | DEC-0208 → 07 |
| REQ-INT-006 | The everyday model shall stay loaded while a specialist's model runs, where memory allows. | Should | R1 | PC | New (needs the cache setting) | M: both loaded, `ollama ps` | DEC-0204 → 07 |
