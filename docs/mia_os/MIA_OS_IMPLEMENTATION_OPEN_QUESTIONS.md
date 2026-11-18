# MIA OS: implementation open questions and decision records (Prompt 16)

> **Prompt 17 (2026-11-18):** the answers to this document's questions are in `MIA_OS_OPEN_QUESTIONS.md`, which governs; the decisions' statuses are in `docs/DECISIONS.md`.

*Claude (Opus), 2026-11-18. Questions for Zac also appear in `MIA_OS_OPEN_QUESTIONS.md`.*

## 1. For Zac

**Answered 2026-11-18:** "All work on PC is first, then the display and then laptop otherwise yes to all." The Windows drive goes in a USB enclosure; the approved features are built on Windows alongside; R1 is every PC piece first, then the household display, then the laptop. DEC-0269, 0270, 0272 approved.

| Q | Question | Recommended |
|---|---|---|
| **Q-102** | Your board has one M.2 slot. When the 4 TB drive comes, MIA OS goes on it, and your current Windows drive goes untouched into a USB enclosure (about $25) as the fallback for at least a month, bootable if you need Windows. OK? | Yes |
| **Q-103** | Keep building MIA's approved features on Windows (the lockdown, the Light theme, sounds, the restore drill and the rest) while the OS work goes on, since they carry over? | Yes, both at once |
| **Q-104** | R1's order after the MVP: the household display on the TV first, then recall and workspaces on the PC, then the laptop? | Yes |

## 2. Risks

R-81 to R-85 (`MIA_OS_IMPLEMENTATION_RISK_REGISTER.md`).

## 3. Decision records

### DEC-0269: build in stages, each usable and reversible
Requirements: REQ-IMP-001. Windows his everyday system until the MVP passes on his PC.

### DEC-0270: the MVP is DEC-0182 plus the approved MVP-tier requirements
Requirements: REQ-IMP-003.

### DEC-0271: the critical path
The GPU proof, the image in a VM, MIA's session, his data moved, a week of use.

### DEC-0272: MIA OS on the 4 TB drive; Windows kept intact
Requirements: REQ-IMP-002, 005. Amends DEC-0157's dual boot for a one-slot board.

### DEC-0273: workstreams and work packages on the task board
Each package ends with tests, docs and its gate.

### DEC-0274: every milestone has a gate Zac passes
Requirements: REQ-IMP-004, 006.

## 4. Before Prompt 17

Prompt 17 reviews the whole plan (Prompts 00 to 16) independently for gaps, contradictions and risks.
