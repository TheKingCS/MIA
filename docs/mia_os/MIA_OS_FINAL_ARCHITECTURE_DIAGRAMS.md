# MIA OS: final architecture diagrams (Prompt 17 §16)

*Claude (Opus), 2026-11-18. Version 1.0. Mermaid. One set of names throughout: **the OS** (Fedora Kinoite with
systemd, KWin, Plasma Login Manager), **the runtime** (MIA's engine as a user service), **the shell** (her front end
in a WebEngine window), **the helper** (fixed system operations), **stores** (his data), **devices** (phone, glasses,
Pi, laptop).*

## 1. The whole system

```mermaid
flowchart TB
  subgraph PC["The PC: MIA OS"]
    subgraph OS["The OS (Fedora Kinoite, unmodified)"]
      K[kernel] --- SD[systemd] --- PLM[Plasma Login Manager] --- KW[KWin / Plasma]
      BC[bootc + greenboot] --- LUKS[LUKS2 + TPM]
      OL[Ollama on ROCm]
    end
    subgraph MIA["MIA (unprivileged, his user)"]
      RT[the runtime] --- ST[(stores, history, links, recall)]
      RT --- SH[the shell]
    end
    HP[the helper] -.polkit.- OS
    RT -->|fixed operations| HP
    RT --> OL
  end
  PH[phone] <-->|paired key, HTTP+SSE| RT
  GL[glasses] <--> PH
  PI[Pi: household display] <-->|household key| RT
  LP[laptop: full engine] <-->|sync| RT
```

## 2. Linux and MIA boundaries

```mermaid
flowchart LR
  subgraph Linux["Owned by Linux"]
    boot[boot, Secure Boot] --> login[login, PAM] --> sessions[sessions, windows] --> settings[System Settings]
    upd[updates, rollback] --- disk[disk, encryption]
  end
  subgraph Ours["Owned by MIA"]
    sess[the MIA session entry] --> shell[the shell] --> rt[the runtime] --> data[(his stores)]
    rt --> helper[the helper's fixed list]
  end
  helper -->|polkit dialog| Linux
  sess --> sessions
```

## 3. The runtime and its services

```mermaid
flowchart TB
  API["local API: /api/state, /api/actions, /api/live"] --> AC[the action contract]
  AC --> GR[grants + tiers] --> EX[deterministic execution] --> HI[history + undo]
  API --> CA[context assembler] --> LLM[model router]
  JOBS[scheduler: jobs, daily checks] --> AC
  GATE[communication gate] --> NOTIF[notifications]
  EV[event bus] --- AC
  REG[app registry: manifests] --- AC
```

## 4. Intelligence and memory

```mermaid
flowchart LR
  Q[his message] --> SORT[message kind, in code] --> CTX[facts assembled in code]
  ST[(stores)] --> CTX
  REC[(recall index)] --> CTX
  CTX --> ROUTE{router}
  ROUTE -->|everyday| M1[qwen2.5:14b]
  ROUTE -->|strong / specialist| M2[other local models]
  ROUTE -.consent token, Alpha.-> CL[cloud, never sensitive]
  M1 --> PH[phrased answer] --> Q
  ROUTE -->|fails| FB[next local model, says so]
```

## 5. Autonomy and authorization

```mermaid
flowchart LR
  I[intent] --> P[plan] --> PR[proposal card] --> T{tier from manifest}
  T -->|observe / suggest| SHOW[shown only]
  T -->|act_within_grant + a grant| RUN
  T -->|act_with_approval| APPROVE[his press: once / from now on] --> RUN[execute in code]
  T -->|never| NO[refused]
  RUN --> VER[read back] --> REC[history + undo]
```

## 6. Application ecosystem

```mermaid
flowchart TB
  MAN[apps/&lt;id&gt;/manifest.json] --> REG[registry] --> CAP[capabilities + tiers]
  CAP --> TOOLS[tools for voice] & SCREENS[screens for touch]
  FP[Flatpak apps] --> LAUNCH[the shell's launcher via .desktop entries]
  EXT[extensions: ours only, sandboxed, later] -.-> CAP
```

## 7. Desktop and graphics

```mermaid
flowchart TB
  PLM[Plasma Login Manager] -->|default| MS[MIA session: kwin_wayland + the shell]
  PLM --> PS[Plasma session]
  MS --> W[ordinary app windows beside her]
  MS -->|runtime not ready in 30 s| RP[recovery page: Plasma, terminal, logs]
  MS -.PoC 3 fails.-> CAGE[cage + the shell]
  MS --- AMB[ambient view on a second monitor]
```

## 8. Devices

```mermaid
flowchart LR
  HUB[PC: the hub] <-->|home network| PH[phone: full engine]
  HUB <-->|Tailscale, away only| PH
  PH <--> GL[glasses]
  HUB <--> PI[Pi on the TV: cage, household key]
  HUB <-->|three-way merge by record id| LP[laptop: full engine]
  HUB --> NODE[greenhouse node: snapshots; actions through the contract, Beta]
```

## 9. Security and trust boundaries

```mermaid
flowchart TB
  OUT[web, email, documents] -->|marked as data| MODEL[model]
  MODEL -->|proposes only| CONTRACT[action contract: tiers, grants, bound approvals]
  CONTRACT -->|unprivileged| STORES[(sealed stores)]
  CONTRACT -->|fixed operations| HELPER[helper] -->|polkit| ROOT[the OS]
  DEV[paired devices] -->|scoped key| CONTRACT
  DISK[LUKS2: TPM PCR 7 + PIN] --- STORES
```

## 10. Boot and recovery

```mermaid
flowchart TB
  FW[firmware, Secure Boot] --> SHIM[shim, GRUB, kernel] --> UNLOCK{TPM + PIN}
  UNLOCK -->|no| RK[recovery key]
  UNLOCK --> SYS[systemd] --> GB{greenboot checks}
  GB -->|fail, retries used| RB[roll back to previous deployment]
  GB --> LOGIN[login] --> MIA[MIA session] & PL[Plasma]
  SHIM -.won't boot.-> USB[USB recovery stick]
```

## 11. Build and release

```mermaid
flowchart LR
  C[commit] --> CI[suite on Linux + Windows] --> IMG[image build: digest base, hash locks]
  IMG --> VM[VM: boot, session, suite inside, update, rollback]
  VM --> SIGN[cosign key pair + syft SBOM] --> GHCR[registry]
  GHCR -->|Zac approves the monthly release| PC[his PC: bootc, signature enforced]
```

## 12. Milestones and dependencies

```mermaid
flowchart LR
  FW01[FW-01 build] --> FW02[FW-02 CI] & FW03[FW-03 session]
  FW03 --> FW04[FW-04 health, updates] --> FW05[FW-05 disk] --> FW07[FW-07 migration rehearsal]
  FW03 --> FW06[FW-06 helper] & FW09[FW-09 USB recovery] & FW10[FW-10 devices] & FW11[FW-11 desktop]
  FW04 --> FW08[FW-08 signed releases]
  HW1[HW-01 GPU, Zac] --> MV1
  HW2[HW-02 Windows from USB, Zac] --> MV1
  FW07 --> MV1[MV-01 install + move] --> MV2[MV-02 a week] --> ALPHA[Alpha] --> BETA[Beta] --> STABLE[Stable]
```

## 13. An interaction end to end

```mermaid
sequenceDiagram
  participant Z as Zac
  participant S as the shell
  participant R as the runtime
  participant M as model
  Z->>S: "Book the oil change reminder for Saturday"
  S->>R: POST /api/actions (propose)
  R->>M: phrase the card from code-built facts
  R-->>S: card (tier act_with_approval)
  Z->>S: Approve
  S->>R: approve (bound to the card's parameters)
  R->>R: execute, read back, record, undo ready
  R-->>S: done, with the record
```

## 14. Data ownership and flow

```mermaid
flowchart LR
  subgraph Personal["his, data/profiles/&lt;id&gt;/ (sealed)"]
    CONV[conversations] & MEM[memories] & JOUR[journal] & ACT[activity]
  end
  subgraph Household["household stores"]
    MAINT[maintenance] & KIT[kitchen] & CAL[calendar] & BUD[budget]
  end
  Personal --> HIST[(history: life_events)]
  Household --> HIST
  HIST --> STATE[/api/state: derived picture/]
  Personal -->|sync, his devices only| PHONE[phone]
  Household -->|marked shared| PI[household display]
  Personal -->|encrypted| BACKUP[nightly backup + off-PC copy]
```

## 15. Control and authorization

```mermaid
flowchart TB
  WHO[who asked: Zac, a job, a device] --> AUTH{authenticated?}
  AUTH -->|no| STOP[refused]
  AUTH --> KIND[action kind's tier]
  KIND --> GRANT{a grant covers it?}
  GRANT -->|yes| DO[execute]
  GRANT -->|no| CARD[approval card] --> PRESS{his press}
  PRESS -->|approve| DO
  PRESS -->|reject / no answer| WAIT[nothing changes]
  DO --> OSOP{system change?}
  OSOP -->|yes| HELPER[helper + polkit dialog]
  OSOP -->|no| STORE[store write, undoable]
```
