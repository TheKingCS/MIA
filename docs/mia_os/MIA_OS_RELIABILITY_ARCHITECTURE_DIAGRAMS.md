# MIA OS: reliability diagrams (Prompt 14)

*Claude (Opus), 2026-11-18. Mermaid.*

## 1. Boot

```mermaid
flowchart LR
  FW["firmware, Secure Boot"] --> BL["boot loader"] --> K["kernel"] --> LUKS["disk unlocked (TPM)"] --> SD["systemd"] --> SDDM["login"]
  SDDM -->|MIA| RT["mia-runtime (user)"] --> SH["mia-shell"]
  SDDM -->|Plasma| PL["Plasma"]
  SD --> OL["ollama"] & TS["tailscaled"]
```

## 2. Readiness

```mermaid
stateDiagram-v2
  Started --> CoreReady: stores open
  CoreReady --> VoiceReady: speech loaded
  VoiceReady --> ModelsWarm: model answers
  ModelsWarm --> AllReady: jobs, devices
```

## 3. An update

```mermaid
flowchart LR
  CHK["check"] --> DL["download (background)"] --> VER["verify signature"] --> STG["stage"] --> SNAP["snapshot his data"] --> RB["restart he allows"] --> HC{"health checks pass?"}
  HC -->|yes| OK["keep"]
  HC -->|no twice| BACK["previous deployment"]
```

## 4. Data protection layers

```mermaid
flowchart TB
  W["atomic write (+ .prev)"] --> S["Btrfs snapshots"] --> B["nightly encrypted backup"] --> O["copy off the PC"] --> P["the phone's synced copy"]
```

## 5. Failure containment

```mermaid
flowchart LR
  J["a job fails"] --> SC["scheduler: back off"]
  ST["a store damaged"] --> DR["start empty, keep aside, tell"]
  RT["runtime crashes"] --> SYS["systemd restarts (3 max)"]
  SH["shell crashes"] --> SYS
```

## 6. Disaster recovery

```mermaid
flowchart LR
  NEW["new PC or disk"] --> INST["install MIA OS"] --> REST["restore off-PC backup"] --> KEY["recovery key"] --> PAIR["re-pair the phone"] --> SYNC["sync"]
```
