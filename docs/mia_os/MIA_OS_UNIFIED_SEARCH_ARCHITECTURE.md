# MIA OS: unified search (Prompt 10 §7; DEC-0229)

*Claude (Opus), 2026-11-17. Planning only.*

## 1. Sources

| Source | Provider | Exists |
|---|---|---|
| MIA's records (apps, notes, projects, missions, settings, people) | `core/search_manager.py` providers | yes |
| Conversations and memory | the recall index (DEC-0210) | planned |
| Files and documents | KDE's Baloo index, read through its D-Bus interface | planned (MIA OS) |
| Linux apps and settings | desktop entries; KDE settings modules | planned |
| Capabilities | the capability registry | yes |
| Devices | linked devices, the homestead link | partial |

## 2. Result types

| Type | Does on Enter | Example |
|---|---|---|
| **Open** | opens an app, a screen, a window | "open display settings" |
| **Find** | shows a record or file | "the document I edited yesterday" |
| **Ask** | sends to Talk | "what can control my smart devices?" |
| **Start** | starts a plan or workflow, as a proposal | "start the greenhouse checklist" |
| **Do** | proposes an action: the approval card | "add milk to the list" |

**Search never executes a change** (DEC-0229): a Do result opens the same card as any change, with its tier and
grants. Opening and finding are free.

## 3. Rules

- **Permissions:** each provider searches only the signed-in person's stores and their household's; private journal
  and private-mode conversations never (DEC-0210, Q-71).
- **Freshness:** MIA's providers read the stores live; Baloo's index says when it last ran.
- **Offline:** every provider is local; web results only on request.
- **Relevance:** exact name, then recency, then meaning (embeddings when the model is up; words when it isn't).

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DSK-009 | Every search result shall be typed open, find, ask, start or do, and a do or start result shall only ever open an approval card. | Must | MVP | All | Partial (action types) | T | DEC-0229 → 10 |
| REQ-DSK-010 | Search shall reach files through the system's own index and never index the private journal or private-mode conversations. | Must | R1 | PC | Planned | T | DEC-0229, DEC-0210 → 10, 13 |
