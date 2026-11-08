# Living Worlds & The Convergence — DEC-0134, proposed

*claude, 2026-11-08, from Zac's "MIA — Living Worlds" handoff (The Convergence: a multiverse saga, interactive RPG,
world simulation & experiential-learning system). This is the repository assessment, reuse map, architecture and
phased plan the spec itself asks for (its §12 and §16) before any substantial build — and the team norm (Claude
proposes, Zac approves).*

**The honest framing.** This is one of the largest features ever proposed for MIA — eight phases, twenty-odd engines
in the spec. It is **not** a one-session build, and the spec is right that it must not become "a large monolithic game
engine," nor let "narrative generation directly modify authoritative state." The good news from inspecting the repo:
**MIA already has most of the hard foundations**, including the single hardest architectural rule. Living Worlds is
mostly *connect and extend*, with a few genuinely new pieces. This proposal maps which is which and recommends a small,
safe Phase 1.

## 1. The hardest rule is already how MIA works

The spec's critical principle (§9.1, §14.11): *the language model proposes narrative events; authoritative services
validate and commit state.* **This is already MIA's core pattern:**
- `core/actions.py` — Propose → Approve → Execute → Record → Undo. The model never writes a record directly.
- CLAUDE.md: "facts are assembled in code and the model only phrases them." The model phrases; code decides.
- `core/maintenance_manager` compound triggers, `core/build_calcs` (quantities worked out in code, never the model),
  `core/safety_floor` (never depends on the model) — the whole codebase is built on this separation.

So the Rules Engine / Narrative Engine split the spec wants isn't a new architecture to invent — it's MIA's existing
one applied to game state. A **Dungeon Master turn** = the model proposes narrative + intents → a Rules service
validates (dice, mechanics) → game-state stores commit through the actions/undo path → `life_events` records it → the
model narrates the committed result. Nothing the model says can corrupt a character sheet.

## 2. Reuse map — spec engine → what exists

| Spec engine (§11) | Existing MIA service | Verdict |
|---|---|---|
| Character / Entity / Faction engines | `mission_manager`, `party.py` (party & guild, DEC-0028), `core/links.py` (typed relationships), profile/person model | **Extend** |
| Campaign / Session persistence | The store pattern (`PERSONAL_STORES`, `atomic_write_text`, `_load`), sealed at rest (DEC-0126) | **Extend** |
| Timeline / Event-driven design (§11.2) | `core/life_events.py` (append-only history), `core/event_bus.py` | **Reuse** |
| Rules Engine (dice, validation, commit) | `core/actions.py` (propose/validate/execute/undo) | **Reuse the pattern** |
| Learning Engine (§7) | `core/paths.py` (DEC-0112: desire → stages → teach → practice → verify by evidence) | **Reuse — this *is* the learning engine** |
| World map / exploration | `core/world_map.py` (fog of war, DEC-0028) | **Extend** |
| Missions / quests / XP | `mission_manager`, `pathway_manager` (questlines), `discovery_manager` (AI-generated missions) | **Extend** |
| Cross-world intelligence / Convergence links | `core/links.py` (typed `kind:id` links between records) | **Extend** |
| Chronicles / legacy archive | `saga_moments` + the Chronicle Archive (DEC-0084) | **Extend** |
| Asset versioning | `core/creations.py` (every version of what MIA made) | **Reuse** |
| Narrative generation off-thread | `core/generate_worker.py` | **Reuse** |
| Voice / spatial UI | existing voice stack, the web Nexus (DEC-0130), the desktop orb | **Reuse** |
| **Generative Artwork Engine (§8)** | **none** (no image generation in the repo today) | **NEW** |
| World simulation / autonomous NPCs / factions (§3, §5) | partial (missions/factions exist as data, not simulation) | **NEW (the sim loop)** |
| The Convergence meta-narrative orchestration (§2, §4, §5) | none (links exist; the orchestration doesn't) | **NEW** |

**Roughly: ~60% extend/reuse, ~40% new.** The new parts are the generative-artwork engine, the world-simulation loop,
and the Convergence orchestration. Everything else leans on proven infrastructure.

## 3. Data model (new stores, established pattern)

New persistent stores following `PERSONAL_STORES` (per-person, `data_dir` constructor, `_load`, `atomic_write_text`,
sealed at rest, undoable): **Universe, Campaign, Character, CharacterVersion, NPC, Faction, Location, Quest, Item,
Artifact, Event, ConvergenceMission, Theme, ReflectionRecord, ArtworkAsset, LearningObjective/Attempt/MasteryRecord.**
Relationships between them go through `core/links.py` (never copied records). Every significant change records a
`life_events` entry (the spec's event log). Campaign state is in stores, not conversation history — so it survives
context limits by construction (the spec's §3.3 requirement, already how every MIA store works).

## 4. The Convergence (the distinctive part)

Each `CharacterVersion` is an independent record (§4.1) — one universe's events never overwrite another's. A
**Convergence Engine** *consumes* campaign events (via the event bus) without controlling any campaign (§11.2), and
uses `links.py` to surface connections (a skill learned in one world that complements another). The **Convergence
Archive** is one authoritative store (multiverse registry, character registry, shared-knowledge archive, event log),
built like the Chronicle Archive (DEC-0084). The Highest Self stays user-defined and revisable (§2.2, §14.12) — a
`Theme` store, never a hard-coded ideal.

## 5. Generative artwork (the one big new engine) — local-first

No image generation exists today. Proposed as a **provider-agnostic Generative Media Engine** (reusable beyond Living
Worlds: avatars, home design, homestead planning — §8.4), async (generate off-thread like `generate_worker`, narrate
while it runs — §8.2), with **visual continuity** via stored appearance descriptions + reference images + `creations`
versioning (§8.3). Local-first fit: Zac's **RX 7900 XTX (24 GB)** can run SDXL-class local image generation (ComfyUI /
Automatic1111 as a local provider) — no cloud, consistent with DEC-0126/DEC-0127. The provider abstraction allows a
hosted fallback later, but the default stays on his GPU.

## 6. Privacy & safety (§6, §14.10)

Maps onto MIA's existing stance: local-first and user-controlled (DEC-0126 sealing covers these stores too). Real-world
**reflection is opt-in and disableable** (§6); fictional choices are never treated as real-world personality; **MIA
never diagnoses** — the same rule `core/safety_floor.py` already enforces for the model. Sensitive real experiences
never auto-become campaign material. Educational content keeps **real facts distinct from fictional mechanics** (§7.3,
§14.6) — tracked as separate record types (LearningAttempt/MasteryRecord vs. character XP).

## 7. Phased plan (grounded in what exists)

- **Phase 1 — Foundation (small, safe, recommended first):** the core data models as new stores (Universe, Campaign,
  Character, CharacterVersion), save/resume, and basic world/character creation through the actions gate. Almost
  entirely the established store pattern + `links` + `life_events`. Fully testable with no model and no art.
- **Phase 2 — Playable DM:** the narrative-proposes/rules-commit turn loop over Phase 1's stores; dice/rules service;
  inventory/quests/NPCs; session recaps (reuse `saga_moments`).
- **Phase 3 — Living Worlds:** the world-simulation loop (autonomous NPCs/factions, dynamic events) — the first big new
  subsystem.
- **Phase 4 — The Convergence:** multiverse registry, cross-world event consumption, the Convergence Archive, shared
  mysteries, Highest Self framework (extends `links` + Chronicle).
- **Phase 5 — Generative artwork:** the Generative Media Engine + local SDXL provider + continuity.
- **Phase 6 — Experiential learning:** educational world templates over `paths.py`, keeping facts vs. mechanics apart.
- **Phase 7 — Immersive UI:** the spatial Living Worlds screens (the design session's — web Nexus look) + voice-first.
- **Phase 8 — Advanced:** deeper simulation, multiplayer over `party.py`, shared templates.

Each phase ships with tests, docstrings, docs, and its own ADR (DEC) for significant choices; existing MIA functionality
is preserved throughout.

## 8. What I need from Zac

- **Approve the direction and Phase 1 scope**, or adjust priorities (e.g. learning-first if that's the real draw).
- The spec is vast; is the **near-term goal a playable solo DM** (Phases 1–2) first, with the Convergence and art as the
  horizon? I'd recommend exactly that — get one world playable and persistent before the multiverse.
- Image generation: confirm **local SDXL on your GPU** is the intended path (vs. a hosted provider).

## 9. Open questions

- Rules system: a light custom ruleset vs. an SRD/d20-like base?
- How much autonomous world-simulation compute is acceptable on the local model/GPU alongside everything else MIA runs?
- Multiplayer scope (household via `party.py`) — Phase 8, or never for Zac-alone (DEC-0119)?

## Related
DEC-0028 (the game layer), DEC-0084 (Chronicle Archive), DEC-0112 (learning paths), DEC-0091 (creations), DEC-0126
(encryption at rest), DEC-0130 (the Nexus look); `core/actions.py`, `core/links.py`, `core/life_events.py`,
`core/mission_manager.py`, `core/world_map.py`, `core/party.py`, `core/paths.py`, `core/generate_worker.py`.
