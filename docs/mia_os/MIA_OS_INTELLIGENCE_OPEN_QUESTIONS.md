# MIA OS: intelligence open questions, risks and measurements (Prompt 07)

*Claude (Opus), 2026-11-17. Questions for Zac also appear in `MIA_OS_OPEN_QUESTIONS.md`.*

## 1. For Zac

| Q | Question | Recommended |
|---|---|---|
| **Q-68** | MIA's everyday model is `qwen2.5:14b` (the docs still said llama3.2 3B). Should a conversation evaluation from your own past questions decide whether `qwen3:14b` replaces it? (It does better on the engineering bench; conversation isn't measured yet.) | Yes: measure, then switch only if it's better at conversation too |
| **Q-69** | For MIA's own answers (not building her), may she offer a cloud model when a question is beyond the local ones, showing exactly what would be sent and asking each time? | Off by default; per question, on your yes, never with your records unless you name them |
| **Q-70** | Measure whisper.cpp against Vosk on your voice, and switch the PC to it if it's clearly more accurate? | Yes |
| **Q-71** | The recall index (find things by meaning): include every personal store except the private journal and private-mode conversations? | Yes; you can add the journal yourself |
| **Q-72** | May MIA ever train models on your own records (to make her router or a specialist better)? | Not without your yes for each dataset; start with none |

## 2. Risks (also in the central register)

| ID | Risk | Response |
|---|---|---|
| R-45 | The local models can't do something well enough and pressure grows to send his data to the cloud | DEC-0207's consent token; the model node (DEC-0202) before the cloud |
| R-46 | An Ollama or model update changes behaviour silently | REQ-INT-027, 032: re-measure on every update |
| R-47 | The recall index leaks a deleted or private record | refs only, re-read from stores; exclusions by default |
| R-48 | Reviews look independent but share a family | labelled; non-Qwen reviewers benched |
| R-49 | Context grows until answers slow and blur | budgets per part; trace what went in |

## 3. Measurements still to make

| Measurement | Settles |
|---|---|
| The four-model bench (running), then gpt-oss-20b and Mistral Small | reviewers from other families |
| Flash attention and the q8_0 cache, before and after | REQ-INT-006 |
| A conversation set from his questions per candidate model | Q-68 |
| whisper.cpp vs Vosk word accuracy on his phrases | Q-70 |
| Embedding models on his records (T-15) | DEC-0210's model |
| Concurrent agents on the card (W1) | the Workroom, vLLM |

## 4. Intelligence dependencies of the feature ecosystem (for `MIA_OS_FEATURE_ECOSYSTEM.md`)

| Feature family | Needs |
|---|---|
| Conversation, voice, glasses | everyday model, STT/TTS, the turn |
| Specialists and teams | per-specialist models, the worksheet, review, inspection, the council |
| Recall, Memories, search | the recall index, embeddings |
| Look, receipts, documents | vision model, OCR |
| World Intelligence, Procurement | the everyday model for phrasing; scoring in code |
| Forge, the lab | coding models (development tools; `qwen3-coder` locally) |
| Everything else | works with no model at all (REQ-INT-036) |
