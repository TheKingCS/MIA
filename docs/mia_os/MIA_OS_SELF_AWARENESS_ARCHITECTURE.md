# MIA OS: self-awareness and controlled self-development (Prompt 09)

> **Prompt 21 (2026-11-18):** DEC-0220 to 0226 are approved (Q-110's batch, 2026-11-18): `docs/DECISIONS.md` governs their status, not the table here.

*Claude (Opus), 2026-11-17, on Zac's go ("lets go"). Planning only: no code, registry, permission or safeguard was
changed. The prompt is kept verbatim in `prompts/09_SELF_AWARENESS_INSPECTION_SELF_DEVELOPMENT.md`. Twenty-one
documents sit beside this one (section 9).*

## 1. The headline

1. **MIA already knows a lot about herself from evidence, in pieces.** What she can do is built from the code
   (`core/capabilities.py`), what she runs on is read live (`core/service_map.py`, `core/model_registry.py`,
   `core/system_health.py`), where she stumbles is logged (`core/failure_log.py`, the Fix-It Log), how she's doing is
   measured (`core/loops.py`, ratings, corrections, the bench), and she audits herself weekly (`core/self_audit.py`).
   Prompt 09 joins these into **one capability truth registry** with explicit states and evidence (DEC-0220).
2. **Every self-statement carries its provenance:** verified (tested or observed), inferred (from what broke),
   documented (written, not checked), planned, or unknown. She never says "I can" from a plan (DEC-0221).
3. **Health and performance come from Linux's own sources and her own counters,** gathered into one observatory,
   not a new monitoring stack (DEC-0222, building on DEC-0195).
4. **Quality is judged by rules in code, his corrections and fixed evaluation sets**, with regressions holding changes
   (DEC-0223, from Prompt 07's evaluation framework).
5. **Investigations end in a test:** a root cause is a hypothesis until a failing test reproduces it (DEC-0224).
6. **Self-development runs only through the lab:** a worktree, a failing test first, the suite before and after,
   Claude's inspection, the merge, and an automatic revert on a new failure. A fixed list of protected files (her
   safeguards, the lab's own rules, the action contract, security) is never changed by her (DEC-0225; DEC-0200).
7. **New capabilities arrive the same way every time:** a gap becomes a proposal; the Forge builds it in the lab; it
   reaches the registry only with its tier, tests and evidence (DEC-0226).

## 2. The audit (verified in the code, 2026-11-17)

| Area | Exists | State |
|---|---|---|
| What she can do | `core/capabilities.py`: every app's status from the code (implemented, partial, planned, unavailable here, malfunctioning), evidence verified or inferred, parity gaps decided in `work/parity.json` | **Exists** |
| What she is | `core/self_knowledge.py`: "what are you?", "what can you do?", "what do you know about me?" answered from records; `core/personality.py` | **Exists** |
| What she runs on | `core/service_map.py` (each service, checked now), `core/model_registry.py` (models, from Ollama's API), `core/system_health.py` (CPU, memory, disk, temperature) | **Exists** |
| Her apps | `core/app_registry.py` (manifests, checked against the code), status per app (M5) | **Exists** |
| Her map | `core/code_atlas.py` (every file and definition documented), `core/system_map.py`, `docs/ATLAS.md`, `docs/MIA_MAP.md` | **Exists** |
| Where she fails | `core/failure_log.py` (the Fix-It Log: his "that's wrong", errors, slow turns, grouped and ranked), `core/capability_gaps.py` (what no tool could do) | **Exists** |
| How she's doing | `core/loops.py` (every process with a measure), ratings, corrections, the turn trace, the golden set, the engineering bench, Claude's inspections | **Exists** |
| Self-audit | `core/self_audit.py` (weekly: her code, connections, practices), `core/self_report.py` (weekly report through the gate) | **Exists** |
| Self-development | `core/dev_lab.py` (worktree, `PROTECTED`, suite before and after, merge, auto-revert), Night School (`core/night_school.py`), `core/mia_coder.py`, the model forge, the Forge's scaffold, Claude's inspection | **Exists** |
| What she's learned building herself | `core/dev_knowledge.py` (knowledge entries, 285 so far) | **Exists** |
| Trust in each agent | `core/dev_ledger.py` (what each member can be trusted with, measured) | **Exists** |

**Gaps:** no single registry joining capability status, its evidence and its last success or failure; capability
states don't include "degraded" or "unverified"; self-statements don't all carry provenance labels; investigations
aren't required to end in a reproducing test; the "protected" list isn't shown to Zac anywhere.

## 3. The architecture

```
 SOURCES (read, never written by the registry)            REGISTRY (derived, rebuilt)       ANSWERS AND ACTIONS
 code (manifests, tools, kinds) ───────────────┐
 tests and benches (results, dates) ────────────┤
 runtime (services, models, health) ───────────┼──▶ capability truth registry ──▶ "what can you do?", the status page,
 the Fix-It Log, gaps, corrections, ratings ───┤     state + evidence + confidence   routing, the Forge's gaps,
 decisions and plans (documented, planned) ────┘                                     Night School's choice of work
                                                                                          │
                       failures ──▶ investigation ──▶ a failing test ──▶ the lab ──▶ Claude's inspection ──▶ merge / revert
```

## 4. Decisions (records in `MIA_OS_SELF_AWARENESS_TECHNOLOGY_EVALUATION.md` §3)

| DEC | Decision | Status |
|---|---|---|
| DEC-0220 | One capability truth registry, derived from code, tests, runtime and the Fix-It Log, with explicit states | PROPOSED |
| DEC-0221 | Every self-statement carries its provenance; never "I can" from a plan | PROPOSED |
| DEC-0222 | Health and performance from Linux's own sources and her counters, in one observatory | PROPOSED |
| DEC-0223 | Quality judged by code checks, his corrections and fixed sets; regressions hold changes | PROPOSED |
| DEC-0224 | An investigation ends in a reproducing test before a fix | PROPOSED |
| DEC-0225 | Self-development only through the lab; the protected list is hers never to change | PROPOSED |
| DEC-0226 | New capabilities only through gap, proposal, lab, registry with tier and tests | PROPOSED |

## 5. Questions for Zac

`MIA_OS_SELF_AWARENESS_OPEN_QUESTIONS.md`: Q-76 (her own fixes merging on Claude's pass), Q-77 (restarting her own
services on her own), Q-78 (showing him the protected list).

## 6. Boundaries

Prompt 10 designs the screens that show this; Prompt 12 keeps it consistent across devices; Prompt 13 designs
security; Prompt 14 recovery and updates. This prompt defines the information and the controls.

## 7. Sources

The repository, read 2026-11-17 (each module named above); decisions DEC-0049, 0058, 0094, 0100, 0104, 0108, 0173,
0195, 0200. Technology sources in the technology evaluation.

## 8. What it means for him

Ask MIA "what can't you do right now?" and the answer comes from evidence with its date ("Look isn't working: the
vision model didn't load at 9:40"), not from a description. When she fixes something in herself, it arrives as a
change he can see, with the test that proves it, Claude's verdict and an automatic undo if anything breaks.

## 9. The documents

`MIA_OS_SYSTEM_IDENTITY_AND_INTROSPECTION.md`, `MIA_OS_CAPABILITY_TRUTH_REGISTRY.md`, `MIA_OS_CAPABILITY_STATE_MODEL.md`,
`MIA_OS_SELF_KNOWLEDGE_PROVENANCE.md`, `MIA_OS_LIVE_SYSTEM_INTROSPECTION.md`, `MIA_OS_HEALTH_MONITORING_AND_DIAGNOSTICS.md`,
`MIA_OS_PERFORMANCE_OBSERVATORY.md`, `MIA_OS_RESPONSE_QUALITY_EVALUATION.md`,
`MIA_OS_SELF_AWARENESS_AND_MEMORY_INTEGRATION.md`, `MIA_OS_SELF_INSPECTION_AND_ROOT_CAUSE_ANALYSIS.md`,
`MIA_OS_CONTROLLED_SELF_DEVELOPMENT.md`, `MIA_OS_SELF_MODIFICATION_AND_CODE_LIFECYCLE.md`,
`MIA_OS_LEARNING_AND_FEEDBACK_ARCHITECTURE.md`, `MIA_OS_CAPABILITY_EVOLUTION_AND_DISCOVERY.md`,
`MIA_OS_USER_FACING_SELF_AWARENESS.md`, `MIA_OS_SELF_AWARENESS_TESTING_AND_EVALUATION.md`,
`MIA_OS_SELF_AWARENESS_SECURITY_AND_INTEGRITY.md`, `MIA_OS_SELF_AWARENESS_TECHNOLOGY_EVALUATION.md`,
`MIA_OS_SELF_AWARENESS_ARCHITECTURE_DIAGRAMS.md`, `MIA_OS_SELF_AWARENESS_ACCEPTANCE_CRITERIA.md`,
`MIA_OS_SELF_AWARENESS_OPEN_QUESTIONS.md`.

## Security (Prompt 13, 2026-11-18)

The protected list is part of the security design (`MIA_OS_SECURITY_TRUST_BOUNDARIES.md`, B8).
