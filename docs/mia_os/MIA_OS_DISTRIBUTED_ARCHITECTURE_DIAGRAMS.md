# MIA OS: distributed diagrams (Prompt 12 §24)

*Claude (Opus), 2026-11-18. Mermaid.*

## 1. The whole

```mermaid
flowchart TB
  subgraph Home["home network"]
    PC["PC: the hub (engine, records of truth, big models)"]
    NODE["greenhouse node (its own loop, safety MCU)"]
    PI["Pi 5 node (Core edition)"]
    DISP["household display (endpoint)"]
    SENS["sensors (one series each)"]
  end
  PHONE["phone: full engine, small model"] -->|"device key, LAN or Tailscale"| PC
  GL["glasses (endpoint)"] -->|Bluetooth| PHONE
  ZETA["Zeta Astralis (endpoint)"] --> PHONE
  NODE -->|"read-only exports"| PC
  SENS -->|"one number, its key"| PC
  DISP -->|"household key"| PC
  PI --> PC
```

## 2. Device classes

```mermaid
flowchart LR
  HUB["hub"] --- FULL["full engines"] --- END["endpoints"] --- NODES["nodes"] --- CTRL["controllers"] --- SNS["sensors"]
```

## 3. Pairing

```mermaid
sequenceDiagram
  participant D as New device
  participant H as Hub
  participant Z as Zac
  Z->>D: open MIA, name the hub
  D->>H: pair (his name and password)
  H->>H: check, make a key, keep its hash
  H-->>D: device key
  D->>H: capabilities (signed)
  Z->>H: Sign-ins: see it, unlink it any time
```

## 4. Thinking

```mermaid
flowchart LR
  T["a turn"] --> CODE{"code can answer?"}
  CODE -->|yes| A1["answer, no model"]
  CODE -->|no| HUB{"hub reachable?"}
  HUB -->|yes| GPU["the hub's model"]
  HUB -->|no| OWN["the device's own model"]
```

## 5. Sync

```mermaid
sequenceDiagram
  participant P as Phone
  participant H as Hub
  P->>H: what changed since my base?
  H-->>P: its files and versions
  P->>P: three-way merge by record id
  P->>H: changed files (expect version)
  H-->>P: kept, or "changed meanwhile, try again"
```

## 6. Offline and reconnection

```mermaid
stateDiagram-v2
  Linked --> Alone: hub unreachable
  Alone --> Linked: hub reachable
  Linked --> Syncing: on reconnect
  Syncing --> Linked
```

## 7. Greenhouse

```mermaid
flowchart LR
  S["sensors"] --> L["node's loop and safety"] --> E["exports"] --> M["MIA on the PC"] --> G["gate"] --> U["phone, desktop"]
  M -->|"approved action"| API["node's own interface"] --> L
```

## 8. A lost device

```mermaid
flowchart LR
  LOST["phone lost"] --> UNL["unlink in Sign-ins"] --> KEY["its key refused"]
  KEY --> BACK["if it reconnects: told to erase"]
  NEW["new phone"] --> PAIR["pair"] --> FILL["sync fills it"]
```

The remaining views (agents, sessions, observability, versions) follow diagram 1's paths; each is a table in its
document.
