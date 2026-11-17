# MIA OS: autonomy architecture diagrams (Prompt 08 §24)

*Claude (Opus), 2026-11-17. Mermaid.*

## 1. From intent to verified change

```mermaid
flowchart LR
  W["his words / a trigger"] --> I["intent (code first)"] --> G["goal"] --> P["plan: steps + dependencies"]
  P --> R["ready step"] --> T{"tier"}
  T -->|observe/suggest| SHOW["shown"]
  T -->|within grant| EX["execute"]
  T -->|with approval| ASK["card"] -->|yes| EX
  EX --> V["verify: read back"] --> REC["record + undo"] --> P
```

## 2. The execution boundary

```mermaid
flowchart TB
  subgraph Models
    M["understand, plan, choose, phrase"]
  end
  subgraph Code
    D["describe"] --> GR["grants.require"] --> X["execute"] --> VR["verify"] --> RC["record"]
  end
  M -->|proposal: kind + params| D
```

## 3. Agents and the coordinator

```mermaid
flowchart LR
  A1["specialist A (read-only)"] --> WS[("workspace entries")]
  A2["specialist B (read-only)"] --> WS
  WS --> CO["coordinator (code)"] -->|proposals| CON["action contract"]
```

## 4. Autonomy growth

```mermaid
flowchart LR
  AP["repeated approvals, unchanged"] --> OFFER["offer a standing grant, with the evidence"] -->|his yes| GRANT["grant (listed, revocable, lapses unused)"]
  OFFER -->|no| ASKING["keeps asking"]
```

## 5. Proactive path

```mermaid
flowchart LR
  REC["records change / due / reading"] --> CAND["candidate message"] --> GATE["communication gate: pace, merge, quiet hours, stop"] --> HIM["offered"] -->|acts| CON["action contract"]
```

## 6. Failure and rollback

```mermaid
flowchart LR
  STEP["step"] --> CHK{"check passes?"}
  CHK -->|yes| DONE["done"]
  CHK -->|no| FAIL["failed: what was found"] --> HOLD["dependents wait"] --> UNDO["undo / compensate offered"]
```
