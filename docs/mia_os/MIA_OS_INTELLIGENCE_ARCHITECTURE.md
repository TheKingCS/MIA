# MIA OS: intelligence architecture (Prompt 07)

*Approved by Zac on 2026-11-17 ("Yes to all your recommendations"; DEC-0206 to 0212). Claude (Opus), 2026-11-17, on Zac's go ("we can begin prompt 7"). Planning only: no service, model, provider or
memory was changed. The prompt is kept verbatim in `prompts/07_MIA_INTELLIGENCE_INFRASTRUCTURE.md`. Twenty documents
sit beside this one (section 10). **Exists**, **partial**, **planned** and **proposed** are marked throughout.*

## 1. The headline

1. **MIA is the program, not the model.** Her identity, memory, decisions, safety and facts already live in her own
   code and stores; models are workers she asks for words, plans and judgements. This architecture keeps it that way
   and makes it a rule (DEC-0206).
2. **One provider interface, many adapters.** A small interface (text, chat with tools, structured output, embeddings,
   vision, speech) already exists for Ollama and llama.cpp; it grows adapters, not callers (DEC-0207).
3. **Local first, measured always.** Every model's eligibility for a task comes from measurements (the golden set, the
   engineering bench, Claude's inspection), never from its name. Cloud models serve development and, for MIA's own
   work, only on a per-request yes (DEC-0197, DEC-0207).
4. **Routing is code, not a model's whim:** a task class, the capability registry, the bench and the hardware's state
   pick the model; a fallback chain ends in an answer computed without a model where one exists (DEC-0208).
5. **The council runs on local models of different families** for MIA's own decisions; the cloud council stays
   for building her. Disagreement is kept, never averaged away (DEC-0209).
6. **Memory stays in her stores**, with one recall index by meaning beside them, every memory carrying where it came
   from and whether he confirmed it (DEC-0210).
7. **Learning is bounded:** preferences, notes, routing and templates learn on their own; weights change only through
   the model forge, the bench and Claude's inspection (DEC-0212).

## 2. The audit (prompt §1): what exists, verified in the code on 2026-11-17

| Area | What exists | State | Notes |
|---|---|---|---|
| Provider interface | `core/llm_manager.py`: `LLMBackend` protocol (`generate`, `chat` with tools), `OllamaBackend`, `OpenAIBackend` (llama.cpp's server on the phone) | **Exists** | the right seam; lacks structured output, embeddings and vision as first-class methods |
| Everyday model | `qwen2.5:14b`, 32k context, temperature 0, kept loaded (`config/config.json` `llm.*`) | **Exists** | **CLAUDE.md still says llama3.2:3b**: out of date; corrected in Q-68's context |
| The turn | `core/assistant_turn.py` (one turn for every voice surface), `core/tool_loop.py` (look-ups, then a combined answer), plain-word commands and question plans before the model | **Exists** | facts assembled in code; the model phrases |
| Safety | `core/safety_floor.py` (crisis handling never depends on a model), `core/stop.py` (in code, first) | **Exists** | |
| Identity | `core/personality.py` (IDENTITY, CHARACTER: one place every prompt takes who she is from), `docs/design/MIA_VOICE.md` | **Exists** | |
| Context | `core/context_assembler.py` (the Life State: `assemble_life_state_v2`, sections marked REAL/DERIVED/SIMULATED/STATIC/PLANNED) | **Exists** | |
| Memory | `core/user_memory_manager.py` (facts about him, reviewable), conversations, `core/life_events.py` (history), `core/links.py`, specialists' workbooks (derived/confirmed), `core/dev_knowledge.py`, the Knowledge Vault, the reference library (Kiwix) | **Exists** (several stores) | no recall by meaning across them yet (UI-5, planned) |
| Meaning | `core/meaning.py`: `nomic-embed-text` on Ollama, matches what he said to example questions (23 of 25 on his benchmark, 2026-10-30) | **Exists** (narrow use) | the embedding seam for the recall index |
| Vision | `core/sight.py`: Qwen2.5-VL 7B on the PC; nothing leaves the PC | **Exists** | |
| Voice | `core/voice_manager.py`: `STTBackend`/`TTSBackend`; Vosk (offline STT), Kokoro-82M through kokoro-onnx (offline TTS); `core/voice_loop.py`, glasses voice through the phone | **Exists** | Whisper not used; streaming partial |
| Specialists | `core/specialists.py` (roles), `core/specialist_work.py` (the worksheet: the model plans, code computes, code traces every number), `core/specialist_models.py` (model per specialist from the bench), `core/specialist_review.py` (a second local model), `core/model_inspection.py` (Claude inspects, DEC-0200), `core/eng_bench.py` | **Exists** (built this month) | the pattern for all serious intelligence work |
| Evaluation | `core/model_bench.py` (golden set: right tool, right words), `core/eng_bench.py`, `core/answer_ratings.py`, `core/turn_trace.py` (one line per turn: route, tools, memories, model), `core/loops.py` | **Exists** | |
| Model registry | `core/model_registry.py`: what's really running, from Ollama's own API, each fact sourced | **Exists** (runtime facts) | no capability records yet (`MIA_OS_MODEL_CAPABILITY_REGISTRY.md`) |
| Own models | `core/model_forge.py` (small models of her own; first: a tool router, measured in the shadow) | **Partial** | |
| Councils | `core/council.py`, `council_floor.py` (budgeted, gated, members ask through MIA), `council_session.py` (glasses), on Claude Code, Codex, Copilot and local Ollama roles (`work/agents.json`) | **Exists** for development | not used for MIA's own answers |
| Cloud in her answers | none; the UAL's "council" action is planned behind a yes to exactly what's sent | **Planned** | |

**Competing implementations found:** `core/core_runtime.py` builds a smaller MIA beside `core/runtime.py` (known,
to be folded, Prompt 05); two ways of choosing a model (the global `llm.model` and per-specialist choices) with no
shared registry; the dev council and MIA's own reviewers are separate mechanisms with the same shape.

**Limits to fix before MIA OS:** no capability registry; no structured-output method (callers parse JSON by hand);
one model queue with no priority (DEC-0204); embeddings used only for one matcher; no recall index; CLAUDE.md out of
date on the model.

## 3. The architecture (prompt §3)

```
                     his words, a selection, a photo, a voice
                                     │
            ┌────────── in code, first: stop, safety floor, plain-word commands ──────────┐
            ▼                                                                               │
   CONTEXT ASSEMBLY (Life State, memories by meaning, the workspace, the device)            │
            ▼                                                                               │
   INTENT (examples by meaning, question plans; a model only to choose among tools)         │
            ▼                                                                               │
   ORCHESTRATION ── a fact? computed in code ── a figure? the worksheet ── words? a model    │
            ▼                                                                               │
   ROUTING (task class × capability registry × bench × hardware state) ──▶ PROVIDER ADAPTERS
            ▼                                                     Ollama │ llama.cpp │ model node │ cloud (yes only)
   VALIDATION (numbers traced, tools checked, outside text framed, second model when it matters)
            ▼
   PHRASED IN HER VOICE (personality.py) ──▶ said, shown, recorded (turn trace, ratings, loops)
```

| Component | Owns | Never |
|---|---|---|
| Identity (`personality.py`) | who she is, how she speaks | depends on which model speaks |
| Memory and context | what's true about his life, with sources | lets a model write a confirmed fact |
| Orchestration and routing | which path and which model | trusts a model's claim about itself |
| Providers | turning prompts into tokens | hold memory or decide anything |
| Validation | checking what came back | lets an unchecked number through on figure work |
| Evaluation and learning | measuring and improving | changes weights without the bench and inspection |

## 4. Decisions (records in `MIA_OS_INTELLIGENCE_TECHNOLOGY_EVALUATION.md` §3)

| DEC | Decision | Status |
|---|---|---|
| DEC-0206 | MIA's identity, memory and decisions live in her code and stores; models are interchangeable workers | APPROVED |
| DEC-0207 | One provider interface with adapters; local first; cloud for her own work only on a per-request yes | APPROVED |
| DEC-0208 | Routing in code from the capability registry and measurements, with a fallback chain | APPROVED |
| DEC-0209 | MIA's own council: local models of different families; disagreement kept | APPROVED |
| DEC-0210 | Memory stays in her stores; one recall index by meaning beside them; provenance on every memory | APPROVED |
| DEC-0211 | Voice: Vosk and Kokoro stay; whisper.cpp measured for the PC; barge-in through the stop | APPROVED |
| DEC-0212 | Learning: behaviour learns freely, weights only through the forge, the bench and Claude's inspection | APPROVED |

## 5. The initial provider and local inference strategy

- **Now:** Ollama on the PC (ROCm), the everyday model `qwen2.5:14b` loaded, specialists' models loaded on demand
  (`specialist_models.py`), `nomic-embed-text` for meaning, Qwen2.5-VL 7B for sight; llama.cpp on the phone.
- **Next:** flash attention and an 8-bit attention cache (`OLLAMA_FLASH_ATTENTION=1`, `OLLAMA_KV_CACHE_TYPE=q8_0`,
  which only works with flash attention on, per Ollama's documentation) so the everyday model and a 14B fit together;
  a capability registry; a priority queue (DEC-0204).
- **Later:** the model node (DEC-0202) behind the same OpenAI-compatible adapter; vLLM only if the Workroom needs real
  batching.

## 6. Questions for Zac

In `MIA_OS_INTELLIGENCE_OPEN_QUESTIONS.md`: Q-68 (the everyday model), Q-69 (cloud for her own answers), Q-70
(Whisper for speech on the PC), Q-71 (what the recall index may hold), Q-72 (fine-tuning on his data).

## 7. Boundaries

Prompt 08 designs the agent runtime and autonomy; this sets the intelligence services it calls. Prompt 13 designs
security fully; this sets intelligence's own boundaries. Prompt 12 distributes; this keeps every service reachable
over the provider interface so it can.

## 8. Sources (read 2026-11-17)

Ollama's FAQ as quoted by several guides (flash attention is on automatically where supported; the K/V cache can be
q8_0, about half f16's memory, only with flash attention; `OLLAMA_MAX_LOADED_MODELS` and `OLLAMA_NUM_PARALLEL`; the
official FAQ itself to be read before changing settings); embedding comparisons (nomic-embed-text 137M/768-d; bge-m3
568M/1024-d multilingual; qwen3-embedding 0.6B to 8B, 32k context); sqlite-vec (one file, brute force) and LanceDB
(embedded, hybrid search); whisper.cpp on AMD with ROCm 7.2 and Vulkan close, faster-whisper mainly for Nvidia; the
repository's own measurements. Each document lists what it rests on.

## 9. What this changes in earlier documents

Nothing approved is changed. `MIA_OS_FEATURE_ECOSYSTEM.md` gains a note on which features depend on which
intelligence services (section 11 of this prompt's open questions document lists them).

## 10. The documents

| Document | Settles |
|---|---|
| `MIA_OS_AI_PROVIDER_ABSTRACTION.md` | the interface and its adapters (DEC-0207) |
| `MIA_OS_LOCAL_INFERENCE_ARCHITECTURE.md` | Ollama, llama.cpp, the model node, settings |
| `MIA_OS_MODEL_ROUTING_AND_SELECTION.md` | task classes, eligibility, fallback (DEC-0208) |
| `MIA_OS_MULTI_MODEL_COUNCIL_ARCHITECTURE.md` | her council and the development council (DEC-0209) |
| `MIA_OS_IDENTITY_AND_CONTINUITY_ARCHITECTURE.md` | DEC-0206 in detail |
| `MIA_OS_MEMORY_INFRASTRUCTURE.md` | the stores, the recall index, provenance (DEC-0210) |
| `MIA_OS_CONTEXT_ENGINEERING.md` | what a prompt holds, and how it's assembled |
| `MIA_OS_MULTIMODAL_INTELLIGENCE.md` | images, documents, screens, audio |
| `MIA_OS_VOICE_AND_CONVERSATION_INFRASTRUCTURE.md` | STT, TTS, turns, barge-in (DEC-0211) |
| `MIA_OS_MODEL_CAPABILITY_REGISTRY.md` | what each model can do, measured |
| `MIA_OS_INTELLIGENCE_EVALUATION_FRAMEWORK.md` | how quality is measured |
| `MIA_OS_INTELLIGENCE_LEARNING_AND_FEEDBACK.md` | what learns, and how (DEC-0212) |
| `MIA_OS_MODEL_PROVIDER_LIFECYCLE.md` | adding, updating, retiring models |
| `MIA_OS_INTELLIGENCE_SECURITY_REQUIREMENTS.md` | what may reach which model |
| `MIA_OS_INTELLIGENCE_OBSERVABILITY.md` | traces, metrics, what he can see |
| `MIA_OS_INTELLIGENCE_FAILURE_AND_DEGRADATION.md` | every failure and its fallback |
| `MIA_OS_INTELLIGENCE_ARCHITECTURE_DIAGRAMS.md` | the diagrams the prompt asks for |
| `MIA_OS_INTELLIGENCE_TECHNOLOGY_EVALUATION.md` | each technology, and the decision records |
| `MIA_OS_INTELLIGENCE_ACCEPTANCE_CRITERIA.md` | how each requirement is checked |
| `MIA_OS_INTELLIGENCE_OPEN_QUESTIONS.md` | questions, risks, measurements still to make |

## Later: self-awareness (Prompt 09, 2026-11-17)

Which models and services are working, degraded or unavailable is held in the capability truth registry
(DEC-0220), and every statement she makes about her own abilities carries its provenance (DEC-0221).

## Across devices (Prompt 12, 2026-11-18)

Which machine thinks: the most capable reachable one, the device's own model the floor (DEC-0245, `MIA_OS_DISTRIBUTED_INTELLIGENCE_ARCHITECTURE.md`).

## Security (Prompt 13, 2026-11-18)

The model has no authority; outside content reaches it marked as data; sensitive data never goes to a cloud model (DEC-0249, DEC-0251; `MIA_OS_AI_SECURITY_AND_PROMPT_INJECTION_DEFENSE.md`).

## Reliability (Prompt 14, 2026-11-18)

The model server's failures and recovery: `MIA_OS_AI_SERVICE_RELIABILITY.md`.

## Engineering (Prompt 15, 2026-11-18)

Model changes are gated by the evaluation sets (`MIA_OS_AI_QUALITY_EVALUATION_INFRASTRUCTURE.md`, DEC-0266).
