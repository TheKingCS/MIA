# MIA OS: application architecture diagrams (Prompt 03 §19)

*Claude (Opus), 2026-11-15. Mermaid source. **Bold** labels are proposed; the rest exists.*

## 1. Application ecosystem overview

```mermaid
flowchart TB
  OS[MIA OS: Fedora Atomic / Raspberry Pi OS] --> RT[MIA Runtime]
  RT --> SVC[Platform services]
  RT --> REG[Capability registry: tools, action kinds, UAL]
  REG --> APP[Apps = manifests over capabilities]
  APP --> SURF[Surfaces: web, Qt, phone, glasses, voice]
  AG[Agents] --> REG
  SK[Taught skills] --> REG
  CON[Connectors] --> SVC
  EXT["**Extensions (sandboxed)**"] --> API["**Local API v1**"] --> REG
  FP[Flatpak GUI apps] -->|Send to MIA, portals| RT
```

## 2. One application's internal structure

```mermaid
flowchart LR
  M["**Manifest (from code)**"] --> C[Capabilities: tools + action kinds]
  M --> S[Surfaces: page, Qt module, glasses card]
  M --> D[Stores: personal / household]
  M --> J[Background jobs]
  M --> L[Loops]
  C --> D
  J --> C
```

## 3. Lifecycle

```mermaid
stateDiagram-v2
  [*] --> Developed: lab worktree
  Developed --> Validated: suite, review (Fable)
  Validated --> Installed: Zac approves the merge / image
  Installed --> Available: services and stores load
  Available --> Running: surface open or job ran
  Running --> Degraded: a part missing
  Degraded --> Running: recovered
  Running --> Failed: error on last use
  Failed --> Available: fixed or reconnected
  Available --> Disabled: hidden by the person
  Disabled --> Available
  Installed --> RolledBack: previous image
```

## 4. App to platform

```mermaid
sequenceDiagram
  participant Page as Web page
  participant API as /api/*
  participant Core as core/ services
  Page->>API: GET /api/<screen>
  API->>Core: assemble (person's own view)
  Core-->>Page: data
  Page->>API: POST /api/actions (propose)
  API->>Core: describe (checks)
  Page->>API: approve
  API->>Core: execute, record, undo entry
  Core-->>Page: /api/live bump: re-read
```

## 5. App to app

```mermaid
flowchart LR
  A[App A] -->|propose capability| AC[Action contract]
  AC --> B[App B's capability]
  B -->|event| EB[Event bus]
  EB --> A
  B -->|kind:id| LK[Links]
  B -->|record| LE[History]
  A -.never.-x BS[(App B's store)]
```

## 6. MIA's intelligence invoking a capability

```mermaid
flowchart LR
  W[Person's words] --> R[Tool router: phrases, subjects, picks]
  R --> CAP[Capability]
  CAP --> D[describe: preconditions in code]
  D --> T{Tier}
  T -->|read| RUN[Run]
  T -->|reversible within grant| RUN
  T -->|consequential / irreversible| AP[Person approves] --> RUN
  RUN --> REC[Record + undo]
```

## 7. Security boundaries

```mermaid
flowchart TB
  subgraph Trusted[First-party: in the runtime]
    RTc[Runtime + services + stores sealed]
  end
  subgraph Sandbox["**Extension sandbox: own process, no network unless granted**"]
    E1[Extension]
  end
  subgraph Ext[External: Flatpak / Android]
    X1[App]
  end
  E1 -->|token, grants checked| API2["**Local API**"] --> RTc
  X1 -->|portal / Send to MIA| RTc
```

## 8. Distribution

```mermaid
flowchart LR
  LAB[Lab branch] -->|Fable review, Zac merge| GIT[(MIA repo)]
  GIT --> IMG[bootc image build] -->|cosign| PC[PC]
  GIT --> PI[Pi runtime service]
  FH[Flathub, GPG] --> PC
  ZK["**Zac-signed extension bundle**"] --> HOST["**Extension host**"]
```

## 9. Multi-device

```mermaid
flowchart LR
  PC[PC: runtime, model, full screens] <-->|sync| PH[Phone: engine, small model, app]
  PH --> GL[Glasses: cards, voice]
  PC --> PIx[Pi: runtime service, sensors]
  TR["**Truck: phone or Pi, OBD-II**"] --> PH
```

## 10. Developer workflow

```mermaid
flowchart LR
  I[Idea or capability gap] --> SC["**Scaffold**"] --> B[Build in the lab] --> T[Suite: docs, parity, loops, invariants]
  T --> RV[Review: Fable] --> AP[Zac approves] --> IM[Next image] --> LP[Its loop watches it]
```
