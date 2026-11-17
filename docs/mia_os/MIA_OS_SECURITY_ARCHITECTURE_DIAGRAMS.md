# MIA OS: security diagrams (Prompt 13 §27)

*Claude (Opus), 2026-11-18. Mermaid. Each diagram names the controls at its boundaries.*

## 1. The whole, with boundaries

```mermaid
flowchart LR
  OUT["outside content: web, email, documents"] -->|"B1: marked as data"| MODEL["model"]
  MODEL -->|"B2: proposals only"| CONTRACT["action contract: tier, grant, card, stop"]
  ZAC["Zac (session, two-step)"] -->|"B3: approves"| CONTRACT
  CONTRACT --> STORES["his stores (sealed)"]
  CONTRACT -->|"B6: helper + polkit"| OS["the OS"]
  CONTRACT -->|"B7: its own interface"| DEV["controllers (own safety)"]
  DEVS["his devices (keys)"] -->|"B5"| CONTRACT
  MODEL -.->|"B10: his yes, never sensitive"| CLOUD["cloud model"]
```

## 2. An action from proposal to record

```mermaid
sequenceDiagram
  participant M as Model or app
  participant C as Contract
  participant Z as Zac
  participant S as Store
  M->>C: propose(kind, params)
  C->>C: schema, tier, grants, stop, effect
  C-->>Z: card (summary, hash of params)
  Z->>C: approve (bound: id, hash, person, once)
  C->>S: execute
  C->>C: record, undo kept, history
```

## 3. Prompt injection

```mermaid
flowchart LR
  PAGE["a page says: send the files"] --> MARK["marked as data"] --> MODEL["model"] --> PROP["a proposal at most"] --> CARD["a card he sees"] -->|"he declines"| NONE["nothing happens"]
```

## 4. Encryption layers

```mermaid
flowchart TB
  DRIVE["drive: LUKS2 (TPM)"] --> STORE["each store: AES-256-GCM (data key in TPM/DPAPI/Keystore)"] --> VAULT["vaults: own keys (his passwords)"]
  REC["recovery key: his, offline"] -.-> STORE
```

## 5. Data classes and where they may go

```mermaid
flowchart LR
  PUB["public"] --> CL["cloud model"]
  PER["personal"] -->|"his yes, minimised"| CL
  SEN["sensitive"] -.never.-> CL
  SEC["secret"] -.never.-> CL
  SEC -.never.-> VOICE["speech, glasses"]
```

## 6. A lost phone

```mermaid
flowchart LR
  L["lost"] --> U["unlink (any trusted device)"] --> K["key refused"] --> E["erases on reconnect"]
```

## 7. Physical command

```mermaid
flowchart LR
  P["proposal: setpoint"] --> A["action's range check"] --> N["node's limits"] --> MCU["safety MCU"] --> HW["hardware interlocks"]
  A -->|"out of range"| R["refused, recorded"]
```

## 8. Lockdown

```mermaid
flowchart LR
  PH["the phrase"] --> SO["sign out every device"] & ST["stop everything"] & LV["lock vaults"] & PO["pause outreach, lab"]
```

The remaining views (agents, Linux privilege, sandboxing, household, supply chain, backups, monitoring) follow
diagram 1 and are tables in their documents.
