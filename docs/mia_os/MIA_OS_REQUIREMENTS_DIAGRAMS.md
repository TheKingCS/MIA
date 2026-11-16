# MIA OS: requirements diagrams (Prompt 04, deliverable 16)

*Claude (Opus), 2026-11-15. Planning only. Mermaid diagrams; the text documents are authoritative where they differ.*

## 1. System context

```mermaid
flowchart LR
  zac([Zac])
  subgraph pc[The PC: MIA OS]
    os[Linux image: boot, login, disk, network, Flatpak, updates, recovery]
    rt[MIA Runtime: stores, history, links, registry, action contract, grants, gate, scheduler]
    ui[MIA's session: her web front end] 
    kde[KDE Plasma: conventional desktop]
    llm[Local models: Ollama on the GPU]
    os --> rt
    rt --> ui
    os --> kde
    rt --> llm
  end
  phone[Phone: MIA app, small model]
  glasses[Glasses: cards, voice]
  node[Homestead node: acts; safety MCU]
  ext[Outside: SearXNG, feeds, Plaid, mail]
  zac --> ui
  zac --> kde
  zac --> phone
  phone --> glasses
  phone <-->|sync, Tailscale| rt
  node -->|snapshots| rt
  rt -->|his words only| ext
```

## 2. Who decides what

```mermaid
flowchart TD
  req[A request: voice, text, a screen, a job] --> match[Code: match capabilities]
  match --> model[Model: choose among offered tools, fill them, phrase]
  model --> tier{Code: tier and initiator}
  tier -->|observe, suggest| run[Run]
  tier -->|change, his own request| run
  tier -->|change, her initiative, inside a grant| run
  tier -->|consequential or no grant| ask[Ask Zac in code-written words]
  ask -->|yes| run
  run --> rec[Record in the history; undo kept]
  rec --> say[Say what happened, from the record]
```

## 3. Interaction modes over one runtime

```mermaid
flowchart LR
  rt[(One runtime, one set of capabilities)]
  rt --- amb[Ambient: orb, glance cards, voice, paced messages]
  rt --- ws[Workspace: windows, files, apps, Talk]
  rt --- imm[Immersive: Living Worlds, the Dungeon, spatial, on request]
```

## 4. Boot and degradation

```mermaid
flowchart TD
  fw[Firmware] --> boot[Bootloader: current or previous deployment, recovery]
  boot --> unlock[Disk unlock: TPM plus PIN]
  unlock --> login[Login: MIA session default, Plasma one choice away]
  login -->|MIA session| start[Start the runtime]
  start -->|answers| home[Home from records; the model warms]
  start -->|no answer in 30 s| recov[Recovery page: restart MIA, open Plasma, see why]
  home -->|model missing| nomodel[Pages, search, actions work; Talk says the model is unavailable]
  login -->|Plasma| kde[Conventional desktop, MIA not needed]
```

## 5. Traceability, in outline

```mermaid
flowchart LR
  vision[Vision, E1 to E5, DEC entries, P1 to P18] --> reqs[REQ rows]
  existing[Existing MIA: core, apps, tests] --> reqs
  reqs --> owners[Owner prompts 05 to 16]
  reqs --> verify[Verification: tests, demos, measurements]
  reqs --> scen[Scenarios S-01 to S-20]
  owners --> arch[Architecture documents]
```
