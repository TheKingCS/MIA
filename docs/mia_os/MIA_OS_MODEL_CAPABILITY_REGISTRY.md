# MIA OS: the model capability registry (Prompt 07 §13)

*Claude (Opus), 2026-11-17. Planning only. The hardware side is DEC-0203; this is the model side.*

## 1. What exists

`core/model_registry.py` reads what's running from Ollama's own API (family, parameters, quantization, context,
loaded or not), each fact with its source. The bench results (`work/eng_bench/`), the golden set (`core/model_bench.py`),
specialist choices (`core/specialist_models.py`) and Claude's verdicts (`work/inspections.json`) hold the evidence.
Nothing joins them.

## 2. The record

```json
{"model": "qwen2.5:32b", "family": "qwen", "params_b": 32, "quant": "Q4_K_M", "size_gb": 19.9,
 "runner": "ollama", "devices": ["pc"], "paths": ["rocm", "vulkan"], "context": 32768,
 "modalities": ["text"], "tools": true, "structured": true, "local": true,
 "classes": {"figures:electrical": {"good": 1.0, "guessed": 0, "tasks": 7, "seconds": 39.9, "source": "work/eng_bench/qwen2.5_32b.json", "at": "2026-11-17"},
             "tools": {"right_tool": null, "source": "not measured"}},
 "inspected": {"electrical": "pass"}, "retired": false}
```

Facts come from the runner; abilities only from measurements; an unmeasured class says "not measured". Claims from a
model card or a provider page go in a `claimed` field, never `classes`.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-INT-025 | Each model shall have one record joining its runner facts, its measured results per task class, and Claude's verdicts, each with its source and date. | Must | R1 | All | Partial (the pieces exist) | T | DEC-0208 → 07 |
| REQ-INT-026 | A capability claimed by a model card or provider shall be kept apart from measured ones and never used for routing. | Must | R1 | All | New | T | DEC-0208 → 07 |
