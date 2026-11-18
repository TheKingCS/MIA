# MIA OS: the architecture document index (Prompt 17; DEC-0275)

*Claude (Opus), 2026-11-18. Version 1.0. Where to look, and which document wins when two disagree. The hierarchy is
approved (DEC-0275, Q-110, 2026-11-18).*

## 1. The hierarchy of authority

| Rank | Document | Changes how |
|---|---|---|
| 1 | `MIA_OS_FINAL_MASTER_IMPLEMENTATION_BLUEPRINT.md` | a new version, dated, when a decision changes what it says |
| 2 | Decision records in `docs/DECISIONS.md` (classified in `MIA_OS_FINAL_ARCHITECTURE_DECISION_LOG.md`; indexed in `MIA_OS_DECISIONS.md`) | **a status changes in the record first**; only Zac approves |
| 3 | The requirement register (`MIA_OS_REQUIREMENTS_TRACEABILITY_MATRIX.md`, generated from the requirement tables) and its release assignment (`MIA_OS_FINAL_REQUIREMENTS_TRACEABILITY.md`) | edit the table that defines a requirement, then regenerate |
| 4 | Domain specifications: the `MIA_OS_FINAL_*` documents, then each prompt's main document and its supporting documents | a note at the top when superseded in part |
| 5 | The roadmap and work packages (`MIA_OS_FINAL_IMPLEMENTATION_ROADMAP.md`) | a package's specification before it starts |
| 6 | Research and evaluations (`*_TECHNOLOGY_EVALUATION.md`, benches) | dated; superseded by newer checks |
| 7 | History: `preliminary/`, answered per-prompt question files, Prompt 16's first roadmap where the final one differs | never edited except to mark them |

**Rules.** A lower-ranked document never overrides a higher one; where they differ, the higher one governs and the
lower one gets a note. Code is evidence of what exists; documents say what's intended. A count in a document is a
dated snapshot: today's comes from code (`python -m core.system_map`). Agents read rank 1, then the records and
requirements their package names, then the package's own documents (governance: the blueprint §33).

## 2. The final documents (Prompt 17)

| Document | What it governs |
|---|---|
| `MIA_OS_FINAL_MASTER_IMPLEMENTATION_BLUEPRINT.md` | everything, in summary |
| `MIA_OS_FINAL_ARCHITECTURE_CONSOLIDATION.md` | each domain's design |
| `MIA_OS_FINAL_TECHNOLOGY_STACK.md` | technology choices and their evidence |
| `MIA_OS_FINAL_REQUIREMENTS_TRACEABILITY.md` | each open Must · MVP requirement's release and package |
| `MIA_OS_FINAL_ARCHITECTURE_DECISION_LOG.md` | each decision's class |
| `MIA_OS_FINAL_CONFLICT_AND_GAP_ANALYSIS.md` | the conflicts found and their resolutions |
| `MIA_OS_FINAL_INDEPENDENT_TECHNICAL_REVIEW.md` | Codex's review and the responses |
| `MIA_OS_FINAL_SECURITY_AND_RELIABILITY_REVIEW.md` | each control's real state |
| `MIA_OS_FINAL_IMPLEMENTATION_ROADMAP.md` | the order and the packages |
| `MIA_OS_FINAL_MVP_AND_RELEASE_DEFINITION.md` | the MVP and the release ladder |
| `MIA_OS_FINAL_MIGRATION_AND_DATA_CONTINUITY_PLAN.md` | the move |
| `MIA_OS_FINAL_RESOURCE_AND_HARDWARE_PLAN.md` | costs, hardware, skills |
| `MIA_OS_FINAL_RISK_REGISTER.md` | open risks |
| `MIA_OS_FINAL_OPEN_QUESTIONS_AND_APPROVALS.md` | what waits on Zac |
| `MIA_OS_FINAL_ARCHITECTURE_DIAGRAMS.md` | the fifteen diagrams |
| `MIA_OS_IMPLEMENTATION_READINESS_ASSESSMENT.md` | whether to begin |
| this index | where everything is |

## 3. The Master Directive's central documents, by their real names

| Prompt 00 asked for | Where it is |
|---|---|
| MIA_OS_MASTER_PLAN | `MIA_OS_MASTER_PLAN.md` (the progress log; rank 4 now, below the blueprint) |
| MIA_OS_ARCHITECTURE | `MIA_OS_CORE_ARCHITECTURE.md`; final: `MIA_OS_FINAL_ARCHITECTURE_CONSOLIDATION.md` |
| MIA_OS_REQUIREMENTS | `MIA_OS_SYSTEM_REQUIREMENTS.md` and the matrix |
| MIA_OS_AI_INFRASTRUCTURE | `MIA_OS_INTELLIGENCE_ARCHITECTURE.md` |
| MIA_OS_AUTONOMY_MODEL | `MIA_OS_AUTONOMY_ARCHITECTURE.md` |
| MIA_OS_SELF_AWARENESS | `MIA_OS_SELF_AWARENESS_ARCHITECTURE.md` |
| MIA_OS_DESIGN_SPECIFICATION | `MIA_OS_DESKTOP_ARCHITECTURE.md` and `MIA_OS_VISUAL_IDENTITY.md` |
| MIA_OS_DEVICE_ECOSYSTEM | `MIA_OS_DISTRIBUTED_ARCHITECTURE.md` |
| MIA_OS_BOOT_AND_RECOVERY | `MIA_OS_BOOT_AND_STARTUP_ARCHITECTURE.md` |
| MIA_OS_IMPLEMENTATION_ROADMAP | `MIA_OS_IMPLEMENTATION_MASTER_ROADMAP.md`; final: `MIA_OS_FINAL_IMPLEMENTATION_ROADMAP.md` |
| MIA_OS_DECISION_LOG (Prompts 06 to 16) | `MIA_OS_DECISIONS.md` and `docs/DECISIONS.md` |
| MIA_OS_IMPLEMENTATION_STATUS | `MIA_OS_STATUS.md` |
| MIA_OS_REQUIREMENTS_TRACEABILITY | `MIA_OS_REQUIREMENTS_TRACEABILITY_MATRIX.md` |

## 4. Each prompt's main document

| Prompt | Main document | Documents | Final governs where it differs |
|---|---|---|---|
| 01 | `MIA_OS_EXISTING_SYSTEM_AUDIT.md` | listed in the master plan §3 | baseline counts (blueprint §4) |
| 02 | `MIA_OS_FEATURE_ECOSYSTEM.md` | listed in the master plan §3b | — |
| 03 | `MIA_OS_APPLICATION_FRAMEWORK.md` | 17 | — |
| 04 | `MIA_OS_SYSTEM_PHILOSOPHY.md`, `MIA_OS_SYSTEM_REQUIREMENTS.md` | 16 | the MVP (final MVP definition) |
| 05 | `MIA_OS_CORE_ARCHITECTURE.md` | 15 | the session and login manager (DEC-0278) |
| 06 | `MIA_OS_HARDWARE_AND_PLATFORM_STRATEGY.md` | 21 | the disk (DEC-0272) |
| 07 | `MIA_OS_INTELLIGENCE_ARCHITECTURE.md` | 21 | — |
| 08 | `MIA_OS_AUTONOMY_ARCHITECTURE.md` | 24 | the tier vocabulary (C-14) |
| 09 | `MIA_OS_SELF_AWARENESS_ARCHITECTURE.md` | 22 | — |
| 10 | `MIA_OS_DESKTOP_ARCHITECTURE.md` | 25 | — |
| 11 | `MIA_OS_VISUAL_IDENTITY.md` | 25 | — |
| 12 | `MIA_OS_DISTRIBUTED_ARCHITECTURE.md` | 26 | lost-device erase (Codex F-08) |
| 13 | `MIA_OS_SECURITY_ARCHITECTURE.md` | 30 | disk unlock (DEC-0277); each control's state |
| 14 | `MIA_OS_BOOT_AND_STARTUP_ARCHITECTURE.md` | 26 | greenboot and readiness (DEC-0278, C-07) |
| 15 | `MIA_OS_DEVELOPMENT_INFRASTRUCTURE.md` | 26 | the build (DEC-0279) |
| 16 | `MIA_OS_IMPLEMENTATION_MASTER_ROADMAP.md` | 22 | the roadmap, packages and MVP (final documents) |
| 17 | this set | 17 | — |

## 5. The prompts after 17

| Prompt | Class |
|---|---|
| 17b (supplemental directive) | in scope: applied in this review |
| 18 World Intelligence, 19 Procurement, 20 the Living System | approved and largely built (DEC-0170, 0172, 0173); engine work beside the OS plan, not on its critical path |
| 21 Living System completeness | scheduled after Prompt 17 (Zac, 2026-11-15), on Fable |
| 22 the application registry | approved and built (DEC-0175, 0178) |
| 23 Universal Intelligence | its steps run beside the prompts; the UAL on any selection is Beta |
| 24 the appearance engine | built to A7 (DEC-0183, 0186, 0187) |
| 25 specialist teams, 26 the Forge | approved (DEC-0197 to 0200); the Forge end to end is after Stable |

## 6. Superseded material

| Document or decision | Superseded by | Marked |
|---|---|---|
| `preliminary/*` | Prompts 01 to 16 | a note on every file |
| DEC-0157's cage session and dual boot; DEC-0168's dual boot | DEC-0191, 0227, 0272, 0278 | notes on the records |
| DEC-0257's "at a restart he allows" | Zac's Q-95 answer | note on the record |
| `MIA_OS_MVP_DEFINITION.md` §3 (dual boot), `MIA_OS_MINIMUM_VIABLE_OS_DEFINITION.md` | the final MVP definition | notes |
| Dual-boot passages in `MIA_OS_LINUX_FOUNDATION.md`, `MIA_OS_MEMORY_AND_STORAGE_REQUIREMENTS.md`, `MIA_OS_STORAGE_AND_FILESYSTEM_RELIABILITY.md`, `MIA_OS_SYSTEM_ACCEPTANCE_CRITERIA.md` | DEC-0272 | notes |
| Prompt 16's milestones, work packages, task breakdown, effort, spikes, gates and baseline | the final roadmap | notes |
| Per-prompt open-question files | `MIA_OS_OPEN_QUESTIONS.md` (the answers) | notes |
| `MIA_OS_APPEARANCE_ENGINE.md` "Stark (default)" | DEC-0183: Aquatic | note |
| `MIA_OS_RISK_REGISTER.md` | the final risk register | note |
