# MIA OS: intelligence architecture diagrams (Prompt 07 §20)

*Claude (Opus), 2026-11-17. Mermaid (renders on GitHub).*

## 1. The whole

```mermaid
flowchart TB
  IN["words, selection, photo, voice"] --> CODE["in code first: stop, safety floor, commands"]
  CODE --> CTX["context: Life State, memories, workspace"]
  CTX --> ORCH["orchestration: fact, figure or words?"]
  ORCH -->|fact| COMP["computed in code"]
  ORCH -->|figure| WS["worksheet: model plans, code computes"]
  ORCH -->|words| ROUTE["routing"]
  WS --> ROUTE
  ROUTE --> PROV["provider adapters"]
  PROV --> VAL["validation"]
  COMP --> VOICE["her voice (personality.py)"]
  VAL --> VOICE
  VOICE --> OUT["said, shown, recorded"]
```

## 2. The provider interface

```mermaid
flowchart LR
  CALLERS["turn, worksheet, review, recall, Look"] --> IF["LLMBackend: generate, chat, structured, embed, see"]
  IF --> OL["Ollama (PC)"]
  IF --> OA["OpenAI-compatible: phone, model node"]
  IF -.->|consent token only| CL["cloud"]
```

## 3. Local inference

```mermaid
flowchart LR
  Q["model queue (DEC-0204)"] --> OL["Ollama"]
  OL --> E["everyday 14B (always loaded)"]
  OL --> S["specialist 14B/32B (on demand)"]
  OL --> V["vision 7B"]
  OL --> EM["embeddings"]
```

## 4. Cloud inference

```mermaid
flowchart LR
  ASK["he asks for a stronger model"] --> SHOW["MIA shows exactly what would be sent"]
  SHOW -->|yes| TOK["consent token for that content"] --> CL["cloud adapter"]
  SHOW -->|no| LOCAL["local answer"]
```

## 5. Routing

```mermaid
flowchart TB
  T["task class"] --> EL["eligible: measured for the class"]
  EL --> FIT["fits the device now"]
  FIT --> P{"personal?"}
  P -->|yes| LOC["local only"]
  P -->|no| ANY["local, then node"]
  LOC --> BEST["best by passed, guesses, score, speed"]
  ANY --> BEST
  BEST --> RUN["run and validate"] -->|fail| NEXT["next eligible, then computed answer"]
```

## 6. Council

```mermaid
flowchart LR
  QQ["question, framed"] --> A["member A"] & B["member B (other family)"]
  A --> CR["critique by another family"]
  B --> CR
  CR --> SYN["synthesis cites who said what; disagreements kept"]
```

## 7. Identity and continuity

```mermaid
flowchart TB
  P["personality.py"] --> PROMPT["every prompt"]
  S["stores: memories, records, history"] --> PROMPT
  PROMPT --> M1["model today"]
  PROMPT --> M2["model tomorrow"]
  M1 --> SAME["same MIA"]
  M2 --> SAME
```

## 8. Memory and context assembly

```mermaid
flowchart LR
  ST["stores"] -->|life_events| IDX["recall index: refs + vectors"]
  QUERY["question"] --> IDX --> HITS["refs"] --> REREAD["re-read from stores"] --> PROMPT["prompt, within budget"]
```

## 9. Learning boundaries

```mermaid
flowchart LR
  FB["ratings, corrections, bench"] --> BEH["behaviour: routing, pacing, templates"]
  FB --> FORGE["model forge"] --> BENCH["bench"] --> INSP["Claude's inspection"] --> USE["in use"]
  HIS["his words"] --> MEM["memories (reviewable)"]
```

## 10. Degradation

```mermaid
flowchart LR
  OK{"model ok?"} -->|yes| FULL["full answer"]
  OK -->|no| SMALL{"smaller model?"} -->|yes| PLAIN["plainer answer, said"]
  SMALL -->|no| CODEONLY["commands, plans, facts in code"]
```
