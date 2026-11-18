# MIA OS: development, builds and releases (Prompt 15)

*Claude (Opus), 2026-11-18, on Zac's go ("lets continue"). Planning only: no workflow, build, key or release was
changed. The prompt is `prompts/15_DEVELOPMENT_ENVIRONMENT_BUILD_INFRASTRUCTURE_RELEASE_ENGINEE.md`. Twenty-five
documents sit beside this one (section 9). New requirements start at REQ-DEV-010.*

## 1. The headline

1. **MIA already has a serious engineering platform**: one repository; about 6,800 tests run before every commit;
   every file and definition documented and checked (`core/code_atlas.py`, DEC-0104/0110); generated maps (the
   atlas, MIA's map, loops, parity, events, the requirements matrix) checked by tests; seven GitHub workflows
   (Windows install and suite, the phone build, the OS proofs of concept and VM, the model check, Pages); the lab and
   Night School; knowledge entries; a task board for the team (Claude, ChatGPT, Muse, Zac). **The plan keeps it and
   closes the gaps.**
2. **One repository, its layers enforced** (DEC-0262): core, apps, web, server, gui, homestead, android-phone, os,
   tools, tests, docs, work, each with its rules checked by tests.
3. **A development setup anyone (or any session) can rebuild** (DEC-0263): pinned dependencies with hashes, the
   setup scripts that exist, a Fedora toolbox for MIA OS work.
4. **CI is the gate** (DEC-0264): the suite on Linux and Windows, the phone build, the OS image build, on every push;
   a red build blocks a merge, her own changes included.
5. **Releases are built, signed and recorded** (DEC-0265): the OS image signed with cosign and published; the phone
   app signed with the key from GitHub's secrets (DEC-0160); a software bill of materials with each; versions by
   date.
6. **Tests in layers, AI quality included** (DEC-0266): unit, contract (93 JSON schemas and examples), integration,
   the conversation corpus, the Intelligence Benchmark, the engineering bench, Claude's inspections, VM tests.
7. **Store formats change additively; anything else is a versioned migration with a backup first** (DEC-0267).
8. **Several models build MIA, none alone** (DEC-0268): the engine by Claude, cross-review between Opus and Fable,
   an independent review of every large batch, her own Night School, Zac approving decisions.

## 2. The audit (2026-11-18)

| Part | Built | Where |
|---|---|---|
| Repository | one repo, GitHub (public), `master` | `TheKingCS/MIA` |
| Python setup | `requirements.txt` (116 lines), venv; Windows `install.ps1`, `setup_home_pc.ps1`; Linux `deploy/install_runtime.sh` | root, `deploy/` |
| Tests | pytest, ~6,800; `tools.cloud_tests` for sessions without the PC's libraries | `tests/` |
| Generated docs checked by tests | ATLAS, MIA_MAP, LOOPS, PARITY, EVENTS, the requirements matrix, doc baseline | `core/code_atlas.py` and others |
| CI | Windows install + suite; the phone APK; the OS PoCs and the suite on Ubuntu; the VM; the model check; Pages | `.github/workflows/` |
| The OS image | a bootc Containerfile | `os/Containerfile` |
| The phone build | Gradle, Chaquopy, llama.cpp's server built | `android-phone/` |
| Contracts | JSON schemas and examples for screens and the Life State | `docs/schema/` (93 files) |
| AI quality | the conversation corpus, the Intelligence Benchmark, the engineering bench, model inspections | `tools/`, `work/eng_bench/` |
| Development platform | tasks, agents, reviews, the council, Night School, the lab, knowledge, the ledger | `work/`, `core/work_*`, `core/dev_*` |
| Dependency checks | weekly OSV for Python | `core/dependency_audit.py` |
| Rebuild guide | how to rebuild MIA from nothing | `docs/REBUILD.md` |

**Gaps (general):** dependencies pinned by version but not by hash; no Linux suite job of its own on every push
(the suite runs on Windows and inside the PoC job); the OS image isn't yet built and signed on every push; no SBOM;
no release process or version numbers; the phone's signing key still waits on Zac's step (DEC-0160).

## 3. Decisions (records in `MIA_OS_DEVELOPMENT_TECHNOLOGY_EVALUATION.md` §2)

| DEC | Decision | Status |
|---|---|---|
| DEC-0262 | One repository, its layers enforced by tests | PROPOSED |
| DEC-0263 | A reproducible setup: hashes, the setup scripts, a toolbox | PROPOSED |
| DEC-0264 | CI on every push is the gate, her own changes included | PROPOSED |
| DEC-0265 | Releases built, signed, recorded with an SBOM; versions by date | PROPOSED |
| DEC-0266 | Tests in layers, AI quality included, gating model changes | PROPOSED |
| DEC-0267 | Store formats change additively; otherwise a versioned migration after a backup | PROPOSED |
| DEC-0268 | Several models build MIA; independent review; Zac approves decisions | PROPOSED |

## 4. Questions for Zac

`MIA_OS_DEVELOPMENT_OPEN_QUESTIONS.md`: Q-99 (the repository public or private), Q-100 (her merged changes pushed to
GitHub with the daily summary), Q-101 (a monthly release you approve).

## 5. Boundaries

Prompt 16 orders the building; Prompt 17 reviews everything.

## 6. Sources

The repository, read 2026-11-18; DEC-0058, 0067, 0069, 0094, 0100, 0104, 0110, 0160, 0174, 0189, 0200, 0225;
Prompts 13 and 14. Technology sources in the technology evaluation.

## 7. What it means for him

Every change to MIA, by any model or by MIA herself, is tested on Windows and Linux before it reaches him; every
release is signed so his machines install only the real thing; and if this PC vanished, MIA could be rebuilt from
the repository and his backup.

## 8. Requirements

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DEV-010 | The repository's layering rules (core imports no gui or modules; modules talk through the event bus) shall be checked by a test. | Should | R1 | All | Partial (by convention) | T | DEC-0262 → 15 |

## 9. The documents

`MIA_OS_REPOSITORY_AND_SOURCE_ARCHITECTURE.md`, `MIA_OS_DEVELOPER_ENVIRONMENT.md`, `MIA_OS_REPRODUCIBLE_DEVELOPMENT_SETUP.md`,
`MIA_OS_BUILD_SYSTEM_ARCHITECTURE.md`, `MIA_OS_LINUX_IMAGE_BUILD_INFRASTRUCTURE.md`, `MIA_OS_CI_CD_ARCHITECTURE.md`,
`MIA_OS_TESTING_AND_VALIDATION_ARCHITECTURE.md`, `MIA_OS_AI_QUALITY_EVALUATION_INFRASTRUCTURE.md`,
`MIA_OS_API_CONTRACT_AND_INTEGRATION_TESTING.md`, `MIA_OS_DATABASE_SCHEMA_AND_MIGRATION_STRATEGY.md`,
`MIA_OS_PACKAGE_AND_ARTIFACT_DISTRIBUTION.md`, `MIA_OS_RELEASE_ENGINEERING_AND_VERSIONING.md`,
`MIA_OS_SOFTWARE_SUPPLY_CHAIN_SECURITY.md`, `MIA_OS_MULTI_MODEL_DEVELOPMENT_AND_CODE_REVIEW.md`,
`MIA_OS_GIT_WORKFLOW_AND_CHANGE_MANAGEMENT.md`, `MIA_OS_DOCUMENTATION_AND_ARCHITECTURE_MAINTENANCE.md`,
`MIA_OS_DEVELOPMENT_AND_TEST_ENVIRONMENTS.md`, `MIA_OS_BUILD_PERFORMANCE_AND_RESOURCE_MANAGEMENT.md`,
`MIA_OS_ENGINEERING_OBSERVABILITY.md`, `MIA_OS_LONG_TERM_MAINTENANCE_STRATEGY.md`,
`MIA_OS_ENGINEERING_ARCHITECTURE_DIAGRAMS.md`, `MIA_OS_ENGINEERING_END_TO_END_SCENARIOS.md`,
`MIA_OS_DEVELOPMENT_TECHNOLOGY_EVALUATION.md`, `MIA_OS_DEVELOPMENT_ACCEPTANCE_CRITERIA.md`,
`MIA_OS_DEVELOPMENT_OPEN_QUESTIONS.md`.

## Implementation (Prompt 16, 2026-11-18)

How the agents work the packages: `MIA_OS_AI_AGENT_DEVELOPMENT_WORKFLOW.md`; gates: `MIA_OS_IMPLEMENTATION_TEST_AND_RELEASE_GATES.md`.
