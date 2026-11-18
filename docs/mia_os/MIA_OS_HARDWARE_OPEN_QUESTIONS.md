# MIA OS: hardware open questions, gaps and tests to run (Prompt 06)

> **Prompt 17 (2026-11-18):** the answers to this document's questions are in `MIA_OS_OPEN_QUESTIONS.md`, which governs; the decisions' statuses are in `docs/DECISIONS.md`.

*Claude (Opus), 2026-11-17. Questions for Zac also appear in `MIA_OS_OPEN_QUESTIONS.md`.*

## 1. For Zac

| Q | Question | Why it matters | Recommended |
|---|---|---|---|
| **Q-63** | What case and power supply does the PC have, and how many M.2 slots on the board are free? (A look inside, or the parts list.) | Software can't read them; any card or drive advice depends on them | — |
| **Q-64** | Approve "grow by nodes" (DEC-0202): the next AI hardware is a second machine for models, bought only when the bench or the Workroom shows the need? | It's the largest hardware choice in the plan | Yes |
| **Q-65** | Add a 2 to 4 TB NVMe drive for Fedora (Windows keeps its drive)? | 1 TB fills within months with models, packs and snapshots, and dual boot halves it | Yes, before installing Fedora on the PC |
| **Q-66** | Is a laptop, tablet or smart display in your plans? | Nothing assumes one; if one is coming, Prompt 12 should plan for it | Tell me if so |
| **Q-67** | Turn simultaneous multithreading on in the BIOS? Windows sees 8 of the 9800X3D's 16 threads. | Builds and tests would run faster; no cost | Yes, and measure the suite before and after |

## 2. Gaps (not answerable from software)

- Drive encryption state (needs an administrator prompt; `docs/WAITING_ON.md` already asks).
- Whether AMD-V (virtualization) is on in the BIOS.
- The 7900 XTX's exact model (length, power connectors).

## 3. Tests still to run

| Test | Needs | Settles |
|---|---|---|
| PoC 1: the 7900 XTX under Fedora at Windows speed | a USB stick | DEC-0189's condition, REQ-HW-002 |
| PoC 3: KWin vs cage, with two monitors on two GPUs | a VM, then the PC | DEC-0191, REQ-HW-020 |
| W1: how many Workroom agents the card serves | the PC | DEC-0199, DEC-0202's trigger |
| Bench gpt-oss-20b and Mistral Small 24B | the PC (pulled 2026-11-17) | an independent reviewer (DEC-0200) |
| SMT on vs off, the suite's time | the BIOS switch | Q-67 |
