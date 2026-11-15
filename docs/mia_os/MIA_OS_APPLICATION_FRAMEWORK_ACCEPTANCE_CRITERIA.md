# MIA OS: application framework, acceptance (Prompt 03 §22, and Prompt 02's AF-1 to AF-12)

*Claude (Opus), 2026-11-15. Each criterion with the evidence that it's met, or the test to write.*

## Prompt 03's criteria (the investigation)

| Criterion | Met by |
|---|---|
| Application model defined | MIA_OS_APPLICATION_MODEL.md §1–§3 |
| Kinds have distinct responsibilities | MIA_OS_APPLICATION_MODEL.md §1 table; MIA_OS_APPLICATION_EXTENSION_ARCHITECTURE.md §1 |
| Recommended architecture | MIA_OS_APPLICATION_FRAMEWORK.md §2, DEC-0175 to DEC-0177 |
| Full lifecycle | MIA_OS_APPLICATION_LIFECYCLE.md §1 |
| Discovery and launching | MIA_OS_APPLICATION_LIFECYCLE.md §5 |
| Platform APIs and service boundaries | MIA_OS_APPLICATION_API_ARCHITECTURE.md |
| App-to-app communication | MIA_OS_APPLICATION_INTEROPERABILITY.md |
| AI integration and capability discovery | MIA_OS_AI_APPLICATION_INTEGRATION.md |
| Data ownership and persistence | MIA_OS_APPLICATION_DATA_AND_PERSISTENCE.md |
| Security and sandboxing | MIA_OS_APPLICATION_SECURITY_REQUIREMENTS.md |
| Packaging, signing, updates, rollback | MIA_OS_APPLICATION_DISTRIBUTION_AND_UPDATES.md |
| Developer framework | MIA_OS_APPLICATION_DEVELOPER_FRAMEWORK.md |
| Extensions and plugins | MIA_OS_APPLICATION_EXTENSION_ARCHITECTURE.md |
| Background apps | MIA_OS_APPLICATION_LIFECYCLE.md §6 |
| Multi-device | MIA_OS_MULTI_DEVICE_APPLICATION_MODEL.md |
| Technologies researched | MIA_OS_APPLICATION_TECHNOLOGY_EVALUATION.md (with sources) |
| Diagrams | MIA_OS_APPLICATION_ARCHITECTURE_DIAGRAMS.md (ten) |
| Existing infrastructure mapped | MIA_OS_APPLICATION_FRAMEWORK.md §4 |
| Gaps, dependencies, risks, questions | MIA_OS_APPLICATION_FRAMEWORK.md §1, §6, §7; MIA_OS_APPLICATION_FRAMEWORK_OPEN_QUESTIONS.md; the risk register |

## Prompt 02's requirements, met or not (for the build)

| Req | Status | Evidence today | Test to write when built |
|---|---|---|---|
| AF-1 registration from code | partly | APPS, tools, ACTION_TYPES, stores agree by tests | every tool domain and action family belongs to a manifest |
| AF-2 lifecycle and honest status | partly | capabilities LIMITS, runtime health, Fix-It Log | an app whose store failed to load reports `degraded` |
| AF-3 shared services only | met | CLAUDE.md layering; no app imports another | (exists: layering by convention; add an import-graph test) |
| AF-4 actions declared, tool + control | met for parity; partly for fields | `tests/test_parity.py` | every capability has a tier |
| AF-5 permissions declared and shown | missing | — | DEC-0156's grant tests (Fable) |
| AF-6 background declared | met | `JOBS`, `DAILY_CHECKS`, homeostasis | each job named in a manifest |
| AF-7 devices declared | partly | parity per device | manifest device fields match parity |
| AF-8 data has an owner; removal never deletes | met | stores in `data/`, hiding only | an extension's removal keeps its data unless approved |
| AF-9 third-party sandboxed | missing | — | the extension proof of concept's checks |
| AF-10 apps reach apps through actions and events | met | the rule, enforced by review | the import-graph test |
| AF-11 works without the model | met | `tests/test_living_system.py` (continuity across models), facts in code | — |
| AF-12 outside apps via Send to MIA | met (U1–U3) | `core/ual.py`, the phone's selection menu | the MIA portal, later |
