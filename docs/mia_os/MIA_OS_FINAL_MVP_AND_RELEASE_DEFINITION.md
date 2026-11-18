# MIA OS: the final MVP and release ladder (Prompt 17 §10)

*Claude (Opus), 2026-11-18. Version 1.0. Governs over `MIA_OS_MVP_DEFINITION.md` (DEC-0182) and
`MIA_OS_MINIMUM_VIABLE_OS_DEFINITION.md` where they differ (DEC-0276, proposed; Q-105).*

## 1. The challenge

| Test | DEC-0182's MVP | Finding |
|---|---|---|
| Demonstrates the vision | Yes: MIA's session by default over all his records, the OS working without her | Keep |
| Realistically achievable | Its gate was every Must · MVP requirement (254), 97 of them open, most with no work package | **Too large to prove.** Re-tiered |
| Preserves what exists | Yes: the whole engine moves unchanged | Keep, and prove it by running the suite **inside** the image |
| Avoids complexity | Mostly; but it bundled phone, glasses, voice, every capability by voice, encryption, recovery and a migration into one gate | Split into the MVP and Alpha |
| Daily utility | Yes, if his data moves | Keep the migration in the MVP, gated harder |
| A test environment | Partly: the VM test runs headless | FW-02 and FW-03 make the VM the gate |
| Recoverable | In design | FW-04, FW-05 and FW-09 prove it before his PC |
| Migration path | Dual boot (superseded) | DEC-0272's drive swap, rehearsed first (FW-07) |

## 2. The ladder

| Release | What it is | Mandatory | Deferred to later | Exit condition (Zac passes it) |
|---|---|---|---|---|
| **Foundation** (not a release) | The packages that make the MVP provable, in a VM, with no hardware | FW-01 to FW-12's VM gates | — | Every FW gate green in CI on one commit |
| **MVP**: the first install | MIA OS on his PC, his data moved, Windows waiting in the drawer | §3 | §4 | A week as his main system, nothing lost (REQ-IMP-009), the 67 MVP-gate requirements passing on the image |
| **Alpha**: his only system | Signed monthly releases; the 26 Alpha requirements: accessibility, degraded intelligence, Diagnostics, the capability truth registry; the R1 PC work begins (Zac's order) | the Alpha list in the traceability | the household display, the laptop | A month with no fallback to Windows; the first signed release installed by update; a restore drill passed |
| **Beta**: R1 | R1's PC pieces (recall, workspaces, the UAL, cross-app plans), then the household display on the TV, then the laptop (Zac's order, Q-104) | the Beta list and R1's Must requirements | Zeta Astralis, the model node, spatial | R1's Must requirements pass; the display used by both of them for a week; the laptop syncing for a week |
| **Stable** | The same system, proven over time | nothing new | — | Three monthly releases in a row without a rollback; three monthly restore drills passed; no open High risk |
| **After Stable** | Zeta Astralis, a model node if measured, spatial views, more homestead control | each its own plan and gate | — | — |

## 3. The MVP's mandatory capabilities

| # | Capability | Work package | Proven where |
|---|---|---|---|
| 1 | The image builds reproducibly from the repository | FW-01 | CI: two builds match |
| 2 | It boots under Secure Boot to Plasma Login Manager with "MIA" (default) and "Plasma" | FW-03, FW-05 | VM, then his PC |
| 3 | MIA's session shows her front end full screen with ordinary windows beside it; Plasma, a terminal, the file manager and System Settings two steps away | FW-03, FW-11 | VM screenshots, then his PC |
| 4 | If the runtime or the shell fails, a recovery page within 30 s and Plasma still works | FW-03, FW-04 | VM fault injection |
| 5 | The disk is LUKS2, unlocked by the TPM (PCR 7) with a PIN; the recovery key opens it | FW-05 | VM with a software TPM, then his PC |
| 6 | Updates install by themselves at night, a bad one rolls back by itself, the previous deployment one choice away | FW-04 | VM: a deliberately broken image |
| 7 | System changes only through the helper, each confirmed in the OS's dialog | FW-06 | VM |
| 8 | Every existing MIA capability: the full suite passes inside the image | FW-02 | CI in the VM |
| 9 | Local models on the GPU at the measured speed; a model failure falls back and says so | HW-01, FW-12 | his PC |
| 10 | His data moved, every store's count and content hash matched, the phone re-paired | FW-07, MV-01 | rehearsed in the VM, then for real |
| 11 | The phone and glasses work against the Linux PC | FW-10 | VM with a phone emulator, then his phone |
| 12 | Nightly backups with an off-PC copy, and a restore drill passed | WP-09 | VM, then his PC |
| 13 | A USB recovery path reaches a desktop and his data without MIA | FW-09 | VM, then a USB stick |
| 14 | The approved security builds: the lockdown, approval binding, outside content marked, every personal store sealed | WP-01 to WP-04 | the suite |

**Not in the MVP** (each a Must that's kept, at a later gate): accessibility with Orca and full keyboard use (Alpha;
the MVP keeps today's keyboard support), two monitors on two GPUs (Alpha), the capability truth registry (Alpha),
cloud models with consent tokens (Alpha), the UAL, recall beyond the first slice, workspaces and cross-app plans (Beta),
the household display and the laptop (Beta), homestead commands through the action contract (Beta).

## 4. Why this still isn't a chatbot on Linux

The first install is a whole computer whose default is MIA over every record he has, with her history, grants and undo,
voice and the phone, and it stays a working Linux desktop when MIA fails. What moves to Alpha is polish and reach, not
identity.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-IMP-013 | The MVP's gate shall be the 67 requirements assigned to it in `MIA_OS_FINAL_REQUIREMENTS_TRACEABILITY.md`, each verified on the image, plus the full suite passing inside the image. | Must | MVP | PC | New | T | DEC-0276 → 17 |
