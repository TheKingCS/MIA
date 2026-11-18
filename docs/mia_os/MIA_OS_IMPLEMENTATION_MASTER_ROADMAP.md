# MIA OS: the implementation roadmap (Prompt 16)

> **Prompt 17 (2026-11-18):** superseded where it differs by `MIA_OS_FINAL_IMPLEMENTATION_ROADMAP.md`, `MIA_OS_FINAL_MVP_AND_RELEASE_DEFINITION.md` and `MIA_OS_FINAL_MIGRATION_AND_DATA_CONTINUITY_PLAN.md`. Corrections: proof of concept 2's headless boot, update and rollback **passed** on 2026-11-16 (GitHub run 43872077107), so "boot to do" is wrong; the login manager is Plasma Login Manager, not SDDM; DEC-0269, 0270 and 0272 are approved (`docs/DECISIONS.md`).

*Claude (Opus), 2026-11-18, on Zac's go ("lets begin 16"). Planning only: nothing was installed or changed. The
prompt is `prompts/16_IMPLEMENTATION_PHASES_MIGRATION_STRATEGY_EXECUTION_ROADMAP.md`. Twenty-one documents sit
beside this one (section 9).*

## 1. The headline

1. **Most of MIA already exists and runs on Linux**: the engine, the web front end, the phone, the runtime as a
   systemd service (tested on GitHub's Linux machines), the image's Containerfile (built on every change), the sealed
   data key on Linux. **MIA OS is mostly packaging, sessions, updates and moving his data**, not a rewrite.
2. **Six stages, each usable and reversible** (DEC-0269): 0 MIA on Windows keeps growing → 1 the proofs → 2 the
   image in a VM → 3 the MVP on his PC → 4 R1, the first daily-use release → 5 more devices and beyond.
3. **Windows stays his everyday computer until the MVP passes its gates on his PC** (DEC-0269), and stays intact as
   a fallback for at least a month after (DEC-0272).
4. **The critical path is short and mostly his hands-on steps** (DEC-0271): a USB stick for the graphics card test →
   the image booting in a VM with MIA ready → MIA's session (the compositor test) → his data moved with nothing lost
   → a week as his main system.
5. **Everything else runs in parallel workstreams**, each work package ending with tests, documentation and a gate
   (DEC-0273, DEC-0274).
6. **The approved build backlog continues on Windows now**: everything approved in Prompts 09 to 15 that isn't
   OS-specific is built in stage 0 and carries over unchanged.

## 2. The stages

| Stage | Goal | Ends when | Needs from Zac |
|---|---|---|---|
| **0. MIA on Windows** (now, ongoing) | the approved backlog built where he uses MIA today | — (continues alongside) | trying things; answers |
| **1. Proofs** | the six proofs of concept settled | PoC 1 on his GPU; PoC 2, 3, 5 in a VM; 4 and 6 pass (they do) | a USB stick (PoC 1) |
| **2. The image** | MIA OS boots in a VM: SDDM, MIA's session, the runtime at core ready, updates and rollback, the helper | M3 below | nothing |
| **3. The MVP on his PC** | DEC-0182's MVP on the 4 TB drive, Windows kept | a week as his main system, nothing lost | the 4 TB drive; a USB enclosure; the phone's signing key; an hour at the PC |
| **4. R1** | the first daily-use release, in Zac's order: every PC piece first (recall, workspaces, the UAL, cross-app plans), then the household display on the TV, then the laptop | R1's Must requirements pass | the Pi on the TV; the laptop |
| **5. Beyond** | Zeta Astralis, a model node, spatial, more homestead | each its own gate | hardware as decided |

## 3. Decisions (records in `MIA_OS_IMPLEMENTATION_OPEN_QUESTIONS.md` §3)

| DEC | Decision | Status |
|---|---|---|
| DEC-0269 | Build in stages, each usable and reversible; Windows his everyday system until the MVP passes on his PC | PROPOSED |
| DEC-0270 | The MVP is DEC-0182 plus the approved MVP-tier requirements; R1 the R1-tier rest | PROPOSED |
| DEC-0271 | The critical path: the GPU proof, the image in a VM, MIA's session, his data moved, a week of use | PROPOSED |
| DEC-0272 | MIA OS on the new 4 TB drive; the Windows drive kept intact as a fallback for a month | PROPOSED |
| DEC-0273 | Workstreams with work packages on the task board, each ending in tests, docs and a gate | PROPOSED |
| DEC-0274 | Every milestone has a gate checked by tests or on his devices; Zac passes each gate | PROPOSED |

## 4. Questions for Zac

`MIA_OS_IMPLEMENTATION_OPEN_QUESTIONS.md`: Q-102 (the old Windows drive kept in a USB enclosure), Q-103 (keep
building on Windows while the OS work goes on), Q-104 (R1's order).

## 5. Sources

Prompts 00 to 15 and their decisions (DEC-0154 to 0268); `MIA_OS_MVP_DEFINITION.md`; `os/poc/README.md`; the
requirements matrix (478 requirements).

## 6. What it means for him

Nothing changes on his PC until he has the 4 TB drive and says go; then MIA OS goes on the new drive and Windows
waits in a drawer, untouched, until he's sure.

## 7. Requirements

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-IMP-001 | No stage shall remove his ability to go back to the one before (Windows until the MVP passes; the previous image after). | Must | MVP | PC | Exists (plan) | D | DEC-0269 → 16 |

## 8. The documents

`MIA_OS_CURRENT_IMPLEMENTATION_BASELINE.md`, `MIA_OS_EXISTING_SYSTEM_MIGRATION_STRATEGY.md`,
`MIA_OS_IMPLEMENTATION_MILESTONES.md`, `MIA_OS_MINIMUM_VIABLE_OS_DEFINITION.md`,
`MIA_OS_IMPLEMENTATION_DEPENDENCY_GRAPH.md`, `MIA_OS_IMPLEMENTATION_CRITICAL_PATH.md`,
`MIA_OS_IMPLEMENTATION_WORKSTREAMS.md`, `MIA_OS_IMPLEMENTATION_WORK_PACKAGES.md`,
`MIA_OS_IMPLEMENTATION_TASK_BREAKDOWN.md`, `MIA_OS_IMPLEMENTATION_EFFORT_AND_RESOURCE_ESTIMATES.md`,
`MIA_OS_HARDWARE_AND_INFRASTRUCTURE_ACQUISITION_ROADMAP.md`, `MIA_OS_AI_AGENT_DEVELOPMENT_WORKFLOW.md`,
`MIA_OS_IMPLEMENTATION_RISK_REGISTER.md`, `MIA_OS_TECHNICAL_SPIKE_AND_PROTOTYPE_PLAN.md`,
`MIA_OS_IMPLEMENTATION_TEST_AND_RELEASE_GATES.md`, `MIA_OS_USER_DATA_AND_MIGRATION_CONTINUITY.md`,
`MIA_OS_STAGED_ADOPTION_STRATEGY.md`, `MIA_OS_MILESTONE_ACCEPTANCE_CRITERIA.md`, `MIA_OS_LONG_TERM_EXPANSION_ROADMAP.md`,
`MIA_OS_IMPLEMENTATION_ROADMAP_DIAGRAMS.md`, `MIA_OS_IMPLEMENTATION_OPEN_QUESTIONS.md`.
