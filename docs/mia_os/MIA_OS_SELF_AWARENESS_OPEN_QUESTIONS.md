# MIA OS: self-awareness open questions and risks (Prompt 09)

> **Prompt 17 (2026-11-18):** the answers to this document's questions are in `MIA_OS_OPEN_QUESTIONS.md`, which governs; the decisions' statuses are in `docs/DECISIONS.md`.

*Claude (Opus), 2026-11-17. Questions for Zac also appear in `MIA_OS_OPEN_QUESTIONS.md`.*

## 1. For Zac

**Answered 2026-11-17: "yes to all".** A daily summary of her merged changes with an Undo each (Q-76); she
restarts her own services, reloads models and re-runs failed jobs on a failed check, telling him after (Q-77); the
protected list is shown to him and extended (Q-78). DEC-0222 and DEC-0225 approved.

| Q | Question | Recommended |
|---|---|---|
| **Q-76** | MIA's own fixes and improvements (Night School, findings) merge on Claude's pass when the suite passes (you said Claude's pass covers code). Should you get a daily summary of what merged, each with its reason and an Undo, rather than approving each? Protected files still never change. | Yes, a daily summary |
| **Q-77** | May MIA restart her own services, reload a model or re-run a failed job on her own when a check fails (no code or settings change), telling you after? | Yes |
| **Q-78** | Show you the list of what she can never change about herself (her safeguards, the lab's rules, permissions, the stop), and add grants, the stop, browser safety and her inspection to it? | Yes |

## 2. Risks

| ID | Risk | Response |
|---|---|---|
| R-54 | She reports herself healthier than she is (stale evidence) | the unverified state; a test on the registry's honesty |
| R-55 | Self-made changes accumulate small harms that tests don't catch | loops watched after merges; daily summary; revert |
| R-56 | The protected list falls behind new safeguards | review it with each prompt; a test that named safeguards are on it |

## 3. Before Prompt 10

Prompt 10 designs the desktop. It should show: the capability registry's states, what's running and pending,
self-changes, and the protected list (`MIA_OS_USER_FACING_SELF_AWARENESS.md`).
