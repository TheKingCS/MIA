# MIA OS: the provider abstraction (Prompt 07 §4; DEC-0207)

*Claude (Opus), 2026-11-17. Planning only.*

## 1. Start from what exists

`core/llm_manager.py` already defines `LLMBackend` (a protocol: `generate(prompt, timeout)` and
`chat(messages, tools, timeout)` returning a `ChatReply`) with `OllamaBackend` and `OpenAIBackend`. Every caller goes
through `LLMManager`. That seam is kept and widened; nothing is rewritten.

## 2. The interface

| Method | Returns | Exists | Used by |
|---|---|---|---|
| `generate(prompt, timeout)` | text | yes | phrasing, summaries |
| `chat(messages, tools, timeout)` | reply text and tool calls | yes | the tool loop |
| `structured(prompt, schema, timeout)` | a JSON object validated against the schema | **new** | the worksheet's plan, the specialists' review, inspection (today each parses JSON by hand) |
| `embed(texts)` | vectors | partial (`core/meaning.py` calls Ollama directly) | meaning, the recall index |
| `see(image, question, timeout)` | text | partial (`core/sight.py` calls Ollama directly) | Look, OCR fallback |
| `transcribe(audio)` / `speak(text)` | text / audio | in `core/voice_manager.py`'s own backends | voice (kept there: different lifecycle) |

Every call carries a **request record**: the task class, the person (for whose context), whether his records are
in it (`personal: bool`), the deadline, and the caller. The adapter returns the reply plus **what happened**: the
model, the device, tokens in and out, seconds, and whether it was cut off.

## 3. Adapters

| Adapter | Talks to | Status |
|---|---|---|
| Ollama | the PC's Ollama (ROCm or Vulkan), its native API | exists |
| OpenAI-compatible | llama.cpp's server (the phone), the model node (DEC-0202), vLLM if ever adopted | exists (phone) |
| Hailo (Pi) | the AI HAT+ 2's runtime | planned (with the Pi, H4) |
| Cloud | a provider's API, on Zac's own account | **not built for MIA's own work**; only the UAL's council action and the development tools use cloud models |

**Cloud rule (DEC-0207, from DEC-0197 and the UAL):** a cloud adapter accepts a request only when it carries a
consent token minted by Zac's yes to *exactly that content*, never for `personal: true` requests unless the yes named
that record, and never for a stored grant. The adapter refuses anything else in code.

## 4. Requirements

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-INT-001 | Every model call shall go through one provider interface; no module calls a model runner's API directly. | Must | R1 | All | Partial (`meaning.py`, `sight.py` call Ollama directly) | T: a sweep finds no direct calls | DEC-0207 → 07 |
| REQ-INT-002 | The interface shall offer structured output validated against a schema, and callers shall use it instead of parsing replies by hand. | Should | R1 | All | New | T | DEC-0207 → 07 |
| REQ-INT-003 | A cloud adapter shall refuse any request without a consent token for exactly that content, and every personal request unless the token names the record. | Must | MVP | All | New | T: requests without tokens refused | DEC-0207, DEC-0197 → 07, 13 |
| REQ-INT-004 | Every reply shall come back with the model, device, tokens, time and whether it was cut off, and these go into the turn trace. | Must | R1 | All | Partial (turn trace has the model) | T | DEC-0207 → 07 |
