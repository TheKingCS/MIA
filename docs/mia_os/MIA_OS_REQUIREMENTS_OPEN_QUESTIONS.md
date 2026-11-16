# MIA OS: requirements open questions (Prompt 04, deliverable 14, with §29)

*Claude (Opus), 2026-11-15. Planning only. Questions for Zac are also in the central register
(`MIA_OS_OPEN_QUESTIONS.md`), each with its decision stated in plain words.*

## 1. For Zac

| # | Question (the decision in plain words) | Recommendation | Decision |
|---|---|---|---|
| Q-32 | **What MIA OS is (DEC-0179):** "a personal, AI-native operating environment on a standard Linux image, which is one node of a distributed personal intelligence": not a new kernel or a distribution for others, not an assistant bolted on. | Yes | DEC-0179 |
| Q-33 | **How requirements are judged (DEC-0180):** MoSCoW priority plus a release tier (MVP, R1, Mature, Later); and when principles conflict, this order wins: human authority and safety, then security and privacy, then reliability and the no-AI path, then local-first, then respect for attention, then maintainability. | Yes | DEC-0180 |
| Q-34 | **The autonomy model (DEC-0181):** keep the five tiers already built (instead of the prompt's seven levels), add to every action whether it can be undone and what it reaches (your records, a device, the system, outside), and add one "MIA, stop" that halts everything she's running. | Yes | DEC-0181 |
| Q-35 | **The first MIA OS (DEC-0182):** the scope in `MIA_OS_MVP_DEFINITION.md` §2: the signed image, her session by default with Plasma beside it, everything she does today, local models only, the phone and glasses working as now, backups, rollback and recovery. The Universal Action Layer, meaning search, workspaces and cross-app plans come in the first daily-use release after it. | Yes | DEC-0182 |
| Q-36 | **Other people's requirements:** Prompt 02's multi-user list (speaker identification for two people, a couples' profile, a household display) predates "MIA is for Zac alone" (DEC-0119). Mark those as not planned (kept on file), leaving only "each account's data stays its own"? | Yes | — |

## 2. For later prompts (technical)

| # | Uncertainty | How to settle it | Owner |
|---|---|---|---|
| T-10 | The Linux base: `docs/HARDWARE.md` recommends Ubuntu LTS because ROCm's own matrix lists Ubuntu; DEC-0157 (proposed) chooses Fedora Atomic (bootc) for atomic updates. Both may be fine; the GPU decides. | A 14B model on the RX 7900 XTX on each, timed against the Windows numbers (REQ-HW-002) | 06 |
| T-11 | The 32B model writes at 14 tokens a second on Windows, well under what this GPU should give (it may be partly on the CPU). | Measure again on Linux with ROCm; check how much is on the GPU | 06, 07 |
| T-12 | Boot targets (REQ-PER-001, 002) are set without the image. | Measure on the prototype VM, then the PC | 14 |
| T-13 | Orca and keyboard access inside a cage (single-app) session, not only Plasma. | Try Orca in the cage session on the prototype | 10 |
| T-14 | Whether her web surfaces stay in a browser engine in the cage session (as on Windows) or need a native shell. | Prompt 10's prototype | 10 |
| T-15 | Meaning search: which embedding model, kept where, and how fast on the person's data. | A labelled recall test on his records | 07 |
| T-16 | Reversibility for each of the 474 action kinds (REQ-AUT-006) needs reading each; most are undoable through the undo log. | Generate from the undo log's coverage, then hand-check | 08 |

## 3. Contradictions found (§29), with which source should win

| Conflict | Sources | Recommendation |
|---|---|---|
| Multi-user requirements (MU-2 to MU-10, Q-09) design for Zac's wife and a couples' profile | `MIA_OS_MULTI_USER_REQUIREMENTS.md` vs DEC-0119 (2026-11-07: for Zac alone) | DEC-0119 is later and Zac's: Q-36 |
| The PC's Linux base | `docs/HARDWARE.md` (Ubuntu LTS, ROCm) vs DEC-0157 (Fedora Atomic, proposed) | Neither is settled; T-10 decides on evidence |
| The PC "being built" | `docs/HARDWARE.md` | It's built and in use (measured 2026-11-15); the hardware doc needs its update (done in this commit's notes) |
| DEC-0173 shown as proposed | `MIA_OS_VISION.md`, `MIA_OS_MASTER_PLAN.md` | It's approved; corrected in this prompt's updates |
| "Household experiences, shared projects" in Prompt 04 §7 J | the prompt vs DEC-0119 | Existing household sharing stays (REQ-FUN-180); nothing new is designed for others |

## 4. Requirements that can't be evaluated yet

REQ-PER-001, REQ-PER-002 (no image), REQ-PER-004 and REQ-FUN-062 (no meaning search), REQ-FUN-027 and REQ-SEC-010
(no speaker identification), REQ-HW-002 (no Linux GPU test), REQ-ACC-001 to 003 (no audit yet).
