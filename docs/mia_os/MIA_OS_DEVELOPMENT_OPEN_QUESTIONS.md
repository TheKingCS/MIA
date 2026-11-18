# MIA OS: development open questions and risks (Prompt 15)

*Claude (Opus), 2026-11-18. Questions for Zac also appear in `MIA_OS_OPEN_QUESTIONS.md`.*

## 1. For Zac

**Answered 2026-11-18: "Yes to all".** The repository stays public for now; her merged changes are pushed with the daily summary; a monthly release he approves. DEC-0262, 0264, 0265 approved.

| Q | Question | Recommended |
|---|---|---|
| **Q-99** | MIA's repository on GitHub is public. Keep it public, or make it private? Public keeps CI free and unlimited; private hides the code but caps CI minutes (the Windows and VM jobs use them fastest), and nothing personal is in it either way. | Keep it public for now; revisit when MIA OS ships |
| **Q-100** | Her own merged changes (Night School's fixes on Claude's pass) stay on your PC today. Push them to GitHub with the daily summary, so CI tests them too and the history has them? | Yes |
| **Q-101** | A monthly MIA OS release you approve (from the tested "next" builds), with fixes allowed sooner? | Yes |

## 2. Risks

| ID | Risk | Response |
|---|---|---|
| R-78 | A dependency changes under a pinned version (a re-published package) | hashes in the lock (REQ-DEV-013) |
| R-79 | CI on Windows and in a VM grows slow or costly | jobs only on their inputs; parallel tests |
| R-80 | Several sessions at once overwrite each other's work | own files only; worktrees; never a broad restore |

## 3. Before Prompt 16

Prompt 16 orders everything Prompts 01 to 15 planned into stages that can be built and verified one at a time.
