# MIA OS: memory infrastructure (Prompt 07 §9; DEC-0210)

*Claude (Opus), 2026-11-17. Planning only. Storage layout: DEC-0193.*

## 1. Kinds of memory, in the stores that already hold them

| Kind | Store (exists) | Written by | Status words |
|---|---|---|---|
| Working | the conversation (per person) | each turn | — |
| Episodic | conversations, `core/life_events.py`, the run record, the change history, photos (Memory Vault) | stores, engines | observed |
| Semantic, about him | `core/user_memory_manager.py` (reviewable, deletable) | his words, kept on "keep it" (`core/life_notes.py`) | said / confirmed |
| Semantic, about the world | specialists' workbooks, the reference library (Kiwix packs), the Forge's packs (planned) | study, research | derived until confirmed |
| Relations | `core/links.py` (kind:id refs) | stores, derivation | stated / derived |
| Procedural | taught skills, workflows, templates | him, teaching | learned / practising |
| About herself | `core/dev_knowledge.py`, `core/self_knowledge.py` | development | confirmed |

Every memory already carries where it came from and how it's known (the Living System's epistemic contract,
DEC-0173). That stays the rule.

## 2. What's missing: recall by meaning (UI-5)

One **recall index** beside the stores, never instead of them:
- **Holds:** for each record that may be recalled, its text chunks, a vector, its `kind:id` ref, its person, its
  privacy class and when it changed. **Never the record itself**: a hit is re-read from its store.
- **Built from:** `life_events.record` notifications (each meaningful change), re-embedded in the background.
- **Engine (proposed):** sqlite-vec in one file per person, sealed at rest like the stores; brute-force search is fine
  at his scale (tens of thousands of chunks). LanceDB if hybrid search or scale demands it.
- **Embedding model (proposed):** `nomic-embed-text` now (it's loaded and measured); measure `qwen3-embedding:0.6b` on
  his data (T-15) and switch if it's clearly better. A switch re-embeds everything; the index records which model
  made each vector.
- **Search:** words (the existing search manager) and meaning together; results say *related* when they match by
  meaning only (the review's acceptance row).
- **Excluded by default:** the private journal and anything in a private mode (Q-71).

## 3. Forgetting

Deleting a record removes its chunks from the index in the same change; "forget that" erases the memory and its
vectors; an erased item can't be recalled from a stale vector (the index is checked against the store on read).

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-INT-014 | Recall by meaning shall search a per-person index that holds references and vectors only, re-reading each hit from its store. | Must | R1 | PC | Partial (core/recall_index.py: memories, notes, notes to self, projects; JSON, not sqlite-vec yet) | T: a deleted record never returned | DEC-0210 → 07 |
| REQ-INT-015 | Every memory shall carry its source, how it's known (said, observed, derived, confirmed) and when. | Must | MVP | All | Exists (DEC-0173) | T: test_living_system | DEC-0210 → 07 |
| REQ-INT-016 | The private journal and private-mode turns shall never enter the recall index unless he includes them. | Must | MVP | All | Exists (core/recall_index.SOURCES) | T | DEC-0210 → 07, 13 |
| REQ-INT-017 | With no embedding model available, recall shall fall back to word search and say so. | Must | R1 | All | Exists in `meaning.py` | T | DEC-0210 → 07 |

## Across devices (Prompt 12, 2026-11-18)

What syncs and what doesn't: records and the history yes; the recall index (derived) and what he's working on (device-only) no (`MIA_OS_DISTRIBUTED_MEMORY_AND_CONTEXT.md`, REQ-DST-011).
