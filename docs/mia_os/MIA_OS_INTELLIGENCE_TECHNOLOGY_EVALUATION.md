# MIA OS: intelligence technology evaluation and decision records (Prompt 07 §21, §23)

*Claude (Opus), 2026-11-17. Planning only. Sources read 2026-11-17; documentation is kept apart from measurement.
DEC-0206 to 0212 are PROPOSED.*

## 1. Technologies

| Technology | For | Evidence | Fits the hardware | Recommendation |
|---|---|---|---|---|
| Ollama | the PC's runner | in use; measured (PER table, bench); Fedora package with ROCm (PoC 2) | yes (Prompt 06) | **Keep, primary** |
| Ollama flash attention + q8_0 cache | two models in 24 GB | Ollama FAQ as quoted by several guides: q8_0 about half f16's memory, needs flash attention, global | yes | **Adopt after a before/after bench** |
| llama.cpp server | phone, node, Vulkan fallback | in use on the phone | yes | **Keep** |
| vLLM | batching many agents | documentation; ROCm support narrower on consumer cards | uncertain | **Watch** (W1) |
| nomic-embed-text | embeddings now | in use; 23 of 25 on his benchmark | yes | **Keep for now** |
| qwen3-embedding 0.6B | better recall, long inputs | MTEB-v2 reports; less tooling | yes | **Measure on his data (T-15)** |
| bge-m3 | multilingual | reports: weaker on English than nomic | yes | **Not needed** (English) |
| sqlite-vec | the recall index | one file, brute force; low latency at small scale (vendor-run evals) | yes | **Adopt** for UI-5 |
| LanceDB | hybrid search, scale | embedded, columnar | yes | **Fallback** if needed |
| Vosk | speech in, small devices | in use | yes | **Keep** |
| whisper.cpp | speech in, PC | AMD: ROCm 7.2 and Vulkan close; ROCm 6.x builds hung (one benchmark) | yes | **Measure** (Q-70) |
| faster-whisper | speech in | mainly Nvidia | weak on AMD | **No** |
| Kokoro (ONNX) | her voice | in use; CPU fast enough | yes | **Keep** |
| Cloud models (Claude, others) | development; his explicit asks | in use for development | n/a | **Development yes; her turns only on a per-request yes** |

## 2. Rejected

| Option | Why |
|---|---|
| One big model for everything | ties her to a provider; can't run locally at quality; contradicts DEC-0197 |
| A model fine-tuned to be MIA | identity in weights can't be inspected or kept across models (DEC-0206) |
| A vector database server (Milvus, Qdrant) | another service for a single person's scale |
| A cloud memory service | his memory leaves his devices |

## 3. Decision records

### DEC-0206: MIA is the program, not the model
- Context: the prompt asks that her identity be separated from models. Requirements: REQ-INT-012, 013, 035, 036.
- Options: identity in prompts from one place (today); identity fine-tuned; a provider's persona feature.
- Evidence: `personality.py` already feeds every prompt; facts are assembled in code; the stores hold memory.
- Selected: identity, memory, decisions and safety live in her code and stores; any capable model can speak as her.
- Rejected: fine-tuning identity (uninspectable, model-bound); provider personas (cloud-bound).
- Consequences: a model swap changes wording only. Risks: a weak model phrases poorly (routing handles it).
- Reversibility: full. Reconsider: never for identity; a model of her own may phrase, not be her.

### DEC-0207: one provider interface; local first; cloud only on a per-request yes
- Context: provider independence; DEC-0197. Requirements: REQ-INT-001 to 004, 008, 020.
- Options: per-caller clients; one interface (exists); a third-party gateway.
- Selected: widen `LLMBackend` (structured, embed, see); adapters for Ollama, OpenAI-compatible, Hailo later; a cloud
  adapter that refuses without a consent token for exactly the content.
- Rejected: a gateway service (another moving part). Risks: interface churn (kept small).
- Reversibility: full. Reconsider: a runner MIA needs that doesn't fit the interface.

### DEC-0208: routing in code, from measurements
- Context: many models, tasks and devices. Requirements: REQ-INT-005, 007, 009, 025 to 027, 031.
- Options: a model routes (a "router LLM"); rules from measurements; fixed assignment.
- Selected: task class × capability registry (measured) × device state; a fallback chain; claims never used.
- Rejected: an LLM router alone (unmeasurable); fixed (can't adapt). Her own trained router stays in the shadow
  until it beats the rules (model forge).
- Reversibility: full. Reconsider: if her trained router beats the rules on the held-out set.

### DEC-0209: MIA's council runs on local models of different families
- Context: reviews and hard calls. Requirements: REQ-INT-010, 011.
- Selected: independent answers, cross-family critique, code synthesis where possible, disagreement kept; the
  development council unchanged.
- Rejected: a single reviewer of the same family (not independent); cloud council for her own work (DEC-0197).
- Risks: few capable non-Qwen models fit 24 GB (bench gpt-oss-20b and Mistral Small; the node later).

### DEC-0210: memory stays in her stores, with one recall index beside them
- Requirements: REQ-INT-014 to 018. Selected: per-person sqlite-vec index of refs and vectors, hits re-read from stores;
  nomic-embed-text now, qwen3-embedding measured; the journal excluded by default.
- Rejected: a vector store as the memory of record; a server database. Reversibility: full (the index is rebuilt).

### DEC-0211: voice stays local; whisper.cpp measured for the PC
- Requirements: REQ-INT-022 to 024. Selected: Vosk and Kokoro stay; whisper.cpp on the PC if it measures better on his
  phrases; barge-in through the stop and PipeWire's echo cancellation.

### DEC-0212: learning has three kinds with their own gates
- Requirements: REQ-INT-029, 030. Selected: remembering by his words; behaviour from evidence, undoable; weights only
  through the forge, the bench and Claude's inspection; no training on private data without his yes for that dataset.
