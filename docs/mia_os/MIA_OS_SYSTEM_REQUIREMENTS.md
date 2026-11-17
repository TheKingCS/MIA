# MIA OS: system requirements specification (Prompt 04, deliverable 3)

*Claude (Opus), 2026-11-15. Planning only. The central specification: how requirements are written, prioritised,
traced and verified, and the architectural constraints every later prompt must satisfy. The requirements themselves
live in the documents listed in section 4; each ID is defined once. The traceability matrix is generated from them
([MIA_OS_REQUIREMENTS_TRACEABILITY_MATRIX.md](MIA_OS_REQUIREMENTS_TRACEABILITY_MATRIX.md), `python -m
tools.requirements_matrix`), and a test keeps it current.*

## 1. How a requirement is written

Every requirement is one row:

`| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |`

| Field (prompt §20) | Where it is |
|---|---|
| Unique ID | `ID`: `REQ-<CAT>-<nnn>`, never reused |
| Statement | `Requirement`: one "shall" sentence, testable; its acceptance condition is in the sentence or in `Verify` |
| Rationale | the principle (P1 to P18, [philosophy](MIA_OS_SYSTEM_PHILOSOPHY.md) §3) or decision in `Trace`, and the section's text |
| Category | the ID's prefix (section 2) |
| Priority | `Pri`: Must, Should, Could, Won't (section 3) |
| Release | `Tier`: MVP, R1, Mature, Later (section 3) |
| Device classes | `Dev`: PC, Ph (phone), Gl (glasses), Pi, All |
| Current status | `Status`: Exists, Partial, Planned, New (section 3) |
| Verification | `Verify`: T test, D demo, I inspection, M measurement, then what |
| Source and owner | `Trace`: sources (E1 to E5, DEC-…, P…, a file) `→` the prompt(s) whose architecture must satisfy it |
| Dependencies, related | other REQ IDs named in the row; the matrix lists them |
| Confidence | a target marked *(provisional)* needs measurement or a prototype first |

## 2. Categories

| Prefix | Category | Defined in |
|---|---|---|
| ARC | Architectural constraints | this document, section 5 |
| FUN | Functional, by subsystem (A to K) | [FUNCTIONAL](MIA_OS_FUNCTIONAL_REQUIREMENTS.md) |
| AI | Intelligence, context, model and provider independence | [FUNCTIONAL](MIA_OS_FUNCTIONAL_REQUIREMENTS.md) |
| UX | User experience: modes, boot, navigation | [USER EXPERIENCE](MIA_OS_USER_EXPERIENCE_REQUIREMENTS.md) |
| ACC | Accessibility | [USER EXPERIENCE](MIA_OS_USER_EXPERIENCE_REQUIREMENTS.md) |
| AUT | Autonomy and approval | [AUTONOMY AND TRUST](MIA_OS_AUTONOMY_AND_TRUST_REQUIREMENTS.md) |
| TRU | Transparency and verification | [AUTONOMY AND TRUST](MIA_OS_AUTONOMY_AND_TRUST_REQUIREMENTS.md) |
| DEV | Devices and multi-device | [DEVICE AND HARDWARE](MIA_OS_DEVICE_AND_HARDWARE_REQUIREMENTS.md) |
| HW | Hardware profiles and resources | [DEVICE AND HARDWARE](MIA_OS_DEVICE_AND_HARDWARE_REQUIREMENTS.md) |
| REL | Reliability and degradation | [RELIABILITY](MIA_OS_RELIABILITY_AND_DEGRADATION_REQUIREMENTS.md) |
| SEC | Security | [NON-FUNCTIONAL](MIA_OS_NON_FUNCTIONAL_REQUIREMENTS.md) |
| PRV | Privacy | [NON-FUNCTIONAL](MIA_OS_NON_FUNCTIONAL_REQUIREMENTS.md) |
| PER | Performance | [NON-FUNCTIONAL](MIA_OS_NON_FUNCTIONAL_REQUIREMENTS.md) |
| MNT | Maintainability | [NON-FUNCTIONAL](MIA_OS_NON_FUNCTIONAL_REQUIREMENTS.md) |
| CMP | Compatibility | [NON-FUNCTIONAL](MIA_OS_NON_FUNCTIONAL_REQUIREMENTS.md) |
| OPS | Operational | [NON-FUNCTIONAL](MIA_OS_NON_FUNCTIONAL_REQUIREMENTS.md) |
| DX | Developer experience | [NON-FUNCTIONAL](MIA_OS_NON_FUNCTIONAL_REQUIREMENTS.md) |

## 3. Priority, release tier and status (recommended framework, DEC-0180)

**Priority is MoSCoW**, judged on what the system needs, not on how exciting it is:

- **Must:** without it MIA OS is unsafe, unusable or not MIA OS.
- **Should:** important; its absence is a real loss with a workaround.
- **Could:** valuable when cheap.
- **Won't (now):** recorded so it isn't re-proposed without a reason.

**Release tier** says *when*, separately from how important (a Must can be R1 when the MVP can stand without it):

| Tier | Means |
|---|---|
| MVP | the smallest coherent MIA-first environment ([MVP_DEFINITION](MIA_OS_MVP_DEFINITION.md)) |
| R1 | the first release Zac can use as his only PC system every day |
| Mature | the system as the vision describes it |
| Later | worth recording; not scheduled |

**Status** is checked against the code on 2026-11-15, never assumed:

| Status | Means |
|---|---|
| Exists | built and tested today (the evidence is named) |
| Partial | part built (what's missing is named) |
| Planned | designed in an approved or proposed document, not built |
| New | first stated here |

A feature is never accepted because its screen exists: acceptance needs the behaviour, its permission enforced, its
failure handled and its result verifiable ([ACCEPTANCE](MIA_OS_SYSTEM_ACCEPTANCE_CRITERIA.md)).

## 4. The specification's documents

| Document | Holds |
|---|---|
| [MIA_OS_FUNCTIONAL_REQUIREMENTS.md](MIA_OS_FUNCTIONAL_REQUIREMENTS.md) | FUN (subsystems A to K, cross-app workflows), AI |
| [MIA_OS_NON_FUNCTIONAL_REQUIREMENTS.md](MIA_OS_NON_FUNCTIONAL_REQUIREMENTS.md) | SEC, PRV, PER, MNT, CMP, OPS, DX |
| [MIA_OS_USER_EXPERIENCE_REQUIREMENTS.md](MIA_OS_USER_EXPERIENCE_REQUIREMENTS.md) | UX, ACC |
| [MIA_OS_AUTONOMY_AND_TRUST_REQUIREMENTS.md](MIA_OS_AUTONOMY_AND_TRUST_REQUIREMENTS.md) | AUT, TRU |
| [MIA_OS_DEVICE_AND_HARDWARE_REQUIREMENTS.md](MIA_OS_DEVICE_AND_HARDWARE_REQUIREMENTS.md) | DEV, HW |
| [MIA_OS_RELIABILITY_AND_DEGRADATION_REQUIREMENTS.md](MIA_OS_RELIABILITY_AND_DEGRADATION_REQUIREMENTS.md) | REL |
| [MIA_OS_USER_SCENARIOS.md](MIA_OS_USER_SCENARIOS.md) | S-01 to S-20, each naming the requirements it exercises |
| [MIA_OS_REQUIREMENTS_TRACEABILITY_MATRIX.md](MIA_OS_REQUIREMENTS_TRACEABILITY_MATRIX.md) | generated: every requirement, its sources, owner and status |
| [MIA_OS_MVP_DEFINITION.md](MIA_OS_MVP_DEFINITION.md), [MIA_OS_SYSTEM_ACCEPTANCE_CRITERIA.md](MIA_OS_SYSTEM_ACCEPTANCE_CRITERIA.md) | what's built first, and how it's accepted |
| [MIA_OS_REQUIREMENTS_OPEN_QUESTIONS.md](MIA_OS_REQUIREMENTS_OPEN_QUESTIONS.md), [MIA_OS_REQUIREMENTS_RISK_REGISTER.md](MIA_OS_REQUIREMENTS_RISK_REGISTER.md), [MIA_OS_REQUIREMENTS_DIAGRAMS.md](MIA_OS_REQUIREMENTS_DIAGRAMS.md) | what's unresolved, what could go wrong, the pictures |

Earlier requirement lists stay valid and are referenced, not copied: Prompt 02's `FR-*`
(`MIA_OS_FUNCTIONAL_ACCEPTANCE_REQUIREMENTS.md`), `MU-*` (multi-user), `WS-*` (workspaces), Prompt 03's `AF-*`
(application framework). Where a requirement here restates one, its `Trace` names it.

## 5. Architectural constraints (ARC)

These bind every architecture prompt (05 to 16). Each comes from an established decision; none is new policy.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-ARC-001 | MIA OS shall be built on an unmodified upstream Linux kernel and a mainstream distribution base; no custom kernel or distribution is maintained. | Must | MVP | PC | Planned | I: the image's build files | E1, DEC-0157 → 05, 06 |
| REQ-ARC-002 | The operating system layer shall not depend on the MIA platform: the machine boots, logs in and runs conventional apps with the MIA Runtime stopped or absent. | Must | MVP | PC | New | T: boot the image with the runtime masked | E2, E5, P13 → 05, 14 |
| REQ-ARC-003 | The MIA platform (engine, stores, capabilities, action contract) shall run unchanged on Windows, Linux, Android and Raspberry Pi OS; OS-specific code sits behind interfaces. | Must | MVP | All | Partial: runs on all four today; OS-level services not yet behind an interface | T: the suite on Windows and Linux; the phone build | DEC-0154, P11 → 05, 12 |
| REQ-ARC-004 | One long-running MIA Runtime per person shall own their stores, schedule their jobs and serve every surface; surfaces hold no business logic. | Must | MVP | PC, Pi | Partial: `core/runtime.py` exists; the desktop app still hosts it on Windows | T: `tests/test_runtime*`; a surface's data only from `/api/*` | DEC-0155, DEC-0013 → 05, 14 |
| REQ-ARC-005 | Every change MIA makes to a record, a device or the system shall go through the action contract: proposed in code-written words, approved by its tier, executed, recorded, undoable or marked irreversible before approval. | Must | MVP | All | Exists for records (`core/actions.py`); system and device changes not yet | T: every action kind registered; `tests/test_grants.py` | DEC-0013, DEC-0156, P9 → 08, 13 |
| REQ-ARC-006 | Every tool and action kind shall belong to exactly one app's manifest and carry a tier; an unclaimed or untiered capability fails the build. | Must | MVP | All | Exists (M1, M4) | T: `tests/test_app_registry.py`, `tests/test_grants.py` | DEC-0156, DEC-0175, DEC-0178 → 08 |
| REQ-ARC-007 | Facts, quantities, prices, permissions and success shall be decided in code; a model's output shall only propose and phrase. | Must | MVP | All | Exists as a rule; enforced per feature | I: review; T: `question_plans.invented_numbers` | DEC-0004, P10 → 07 |
| REQ-ARC-008 | No component shall depend on a single AI provider; every model call goes through the backend interface with a local default. | Must | MVP | All | Exists (`core/llm_manager.py` backends) | T: `tests/test_living_system.py` model switch | E3, P16 → 07 |
| REQ-ARC-009 | Code that isn't MIA's own (extensions, generated apps not yet merged) shall run out of process, sandboxed, reaching MIA only through the capability contract. | Must | R1 | PC | Planned (DEC-0176) | T: an extension can't open a store file | DEC-0176 → 13 |
| REQ-ARC-010 | Privileged system changes (packages, services, firmware, users) shall go only through a narrow helper with fixed operations; the runtime itself runs unprivileged. | Must | MVP | PC, Pi | Planned (DEC-0158) | T: the runtime's process has no root; I: the helper's operation list | DEC-0158, P8 → 05, 13 |
| REQ-ARC-011 | The OS image shall be built from files in the repository, signed, and updated atomically with rollback to the previous deployment. | Must | MVP | PC | Planned (DEC-0157) | D: update, then roll back | DEC-0157, DEC-0104 → 14, 15 |
| REQ-ARC-012 | Layering shall be one-way: the OS knows only how to start MIA; the platform knows nothing of surfaces; apps don't import each other. | Must | MVP | All | Exists for the platform (CLAUDE.md layering) | T: layering checks; I | P12 → 05 |
| REQ-ARC-013 | Conventional Linux applications shall be installed and updated by the OS's own mechanisms (Flatpak, the image), never by MIA's registry; MIA-native apps never depend on Flatpak. | Must | MVP | PC | Planned | I | DEC-0177 → 05, 10 |
| REQ-ARC-014 | Every store shall declare where its facts come from, when, how they're known and when they were last checked; a new store without it fails a test. | Must | MVP | All | Exists for new stores (`tests/test_living_system.py`) | T | DEC-0173 → 07 |
| REQ-ARC-015 | Every file, class and function shall be documented so the system can be rebuilt from the repository; undocumented additions fail a test. | Must | MVP | All | Exists (`tests/test_documentation.py`) | T | DEC-0104, P15 → 15 |

## 6. What these requirements decide, and what they leave

**Settled enough to guide Prompts 05 to 16:** the identity and layering (ARC), the autonomy model (AUT, built on
DEC-0156), local-first and provider independence (ARC-008, AI), conventional desktop and no-AI path (ARC-002, UX,
REL), the MVP's scope, and the measured performance baselines on Zac's PC (PER).

**Left to later prompts on purpose:** the image's technology (05, 06: DEC-0157 stays proposed), the model routing
policy and which models (07), agents (08), the desktop's design (10, 11), the sync protocol (12), the threat model and
encryption design (13), boot and update mechanics (14). Each requirement names its owner.

**Unresolved and needing Zac** were Q-32 to Q-36 ([OPEN_QUESTIONS](MIA_OS_REQUIREMENTS_OPEN_QUESTIONS.md)), all
answered 2026-11-15 and 16. Still his to approve before Prompt 05's architecture rests on them: DEC-0154 (the
intelligence stays OS-independent), DEC-0157 (the PC image) and DEC-0158 (the privileged helper).

## 7. Handoff to Prompt 05 (§35)

1. **Definition:** a personal, AI-native operating environment on a standard Linux image, one node of a distributed
   personal intelligence (DEC-0179, approved).
2. **Philosophy:** eighteen principles as a decision framework, with a conflict order: authority and safety, security
   and privacy, reliability and the no-AI path, local-first, attention, maintainability (DEC-0180, approved).
3. **Experience:** MIA's session by default, Plasma one choice away; every capability by screen and by voice; three
   modes (Ambient, Workspace, Immersive) over one runtime; Home from records with no model needed.
4. **Functional, most important:** two sessions each usable alone (FUN-001); every change through the action contract
   (ARC-005); apps from manifests, isolated failures (FUN-040, REL-003); search across every store (FUN-061); plans
   across apps shown step by step (FUN-220, R1); the greenhouse watched (FUN-100) and its controllers adjustable through capabilities, the node keeping its own
   limits (FUN-103, DEC-0185; corrected in Fable's review, 2026-11-16: this said "never commanded").
5. **Non-functional, most important:** sealed stores and encrypted disk (SEC-001, 002); outside text never steers a
   change (SEC-005); no recording by default (PRV-001); answers within 2 to 3 s on the PC (PER-005, measured 0.3 to
   0.9 s); no MVP function needs the cloud or the internet (AI-011, REL-002).
6. **Autonomy and trust:** five tiers enforced (built); a grant only from what he does; reversibility and reach on every
   action and one stop (DEC-0181, approved; the stop defined in AUTONOMY AND TRUST §4, never touching the greenhouse); one history of what she did, with undo (TRU-001).
7. **Hardware:** the reference PC (Ryzen 7 9800X3D, RX 7900 XTX 24 GB, 32 GB, 1 TB NVMe) runs the 3B and 14B models
   comfortably; GPU compute on the chosen base must be proven first (HW-002).
8. **MVP:** `MIA_OS_MVP_DEFINITION.md` (DEC-0182, approved).
9. **Constraints Prompt 05 must hold to:** REQ-ARC-001 to 015, above all: the OS never depends on MIA (002); the
   platform runs unchanged on four OSes (003); one runtime per person owns the state (004); system changes only
   through the helper (010); the image built from the repository with rollback (011); one-way layering (012).
10. **Unresolved:** T-10 (Ubuntu or Fedora: the GPU decides), T-11 (the 32B's speed), T-12
    (boot targets), T-13 and T-14 (accessibility and the shell in the cage session).
11. **What must guide Prompt 05:** the OS layer is small and conventional; everything MIA-specific is a user service
    and a session on top; the runtime's process model, its IPC (T-02), its adapters for keys, power, audio and
    notifications (DEC-0154), the helper's operation list (DEC-0158), and how a session falls back to Plasma and
    recovery (UX-020 to 023) are Prompt 05's to design against these rows.

Prompt 04 stops here. Zac answered its questions (2026-11-15, 16) and gave Prompt 05 to Fable (DEC-0166).

**Prompt 05 is done (2026-11-16):** the architecture these constraints bind is [MIA_OS_CORE_ARCHITECTURE.md](MIA_OS_CORE_ARCHITECTURE.md); every requirement is mapped to its component in [MIA_OS_CORE_ARCHITECTURE_ACCEPTANCE_CRITERIA.md](MIA_OS_CORE_ARCHITECTURE_ACCEPTANCE_CRITERIA.md) §3.

**Prompt 10 is done (2026-11-17):** the desktop's requirements are REQ-DSK-001 to 032, in the Prompt 10 documents
([MIA_OS_DESKTOP_ARCHITECTURE.md](MIA_OS_DESKTOP_ARCHITECTURE.md)); REQ-FUN-001, 003 and REQ-UX-023 are met by
DEC-0227's sessions and shell.
