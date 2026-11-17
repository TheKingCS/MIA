# MIA OS: hardware acceptance criteria (Prompt 06 §24, and how each requirement is checked)

*Claude (Opus), 2026-11-17. Planning only.*

## 1. The prompt's own criteria

| Criterion | Met by |
|---|---|
| The baseline verified | strategy §2: read from the PC on 2026-11-17; gaps listed (Q-63) |
| Requirements grounded in the ecosystem | every REQ-HW traces to a workload, a decision or a measurement |
| Workstation configurations evaluated | desktop requirements §1 |
| CPU options compared | CPU evaluation §2 |
| GPU and AI strategies evaluated | GPU strategy |
| Memory and storage established | memory and storage |
| Android, glasses, embedded documented | their three documents |
| Networking established | network and distributed hardware |
| Discovery and registry defined | DEC-0203 |
| Coordination split between Linux and MIA | DEC-0204 |
| Matrices complete | compatibility matrix |
| Staged roadmap | roadmap H0 to H6 |
| Failure behaviour | failure document |
| Evidence for recommendations | each document's sources |
| Decisions traceable | DEC-0201 to 0205, the traceability matrix |
| Consistent with 00 to 05 | strategy §6 |
| Questions and risks explicit | open questions; R-40 to R-44 |

## 2. Requirements added (REQ-HW-007 to 031)

| ID | Verify | When |
|---|---|---|
| 007 | the PER table on the image | PoC 1, then Prompt 14 |
| 008 | a GPU-less VM served by the PC | after Prompt 12 |
| 009 | a one-slot record gets no "add a card" advice | with the registry |
| 010 | the suite on x86-64 CI and the ARM64 phone build | exists |
| 011, 012 | placement tests with fake records; a VM with the driver unloaded | Prompt 07 |
| 013, 014 | disk accounting tests | with the image |
| 015 | the phone's record reaching the PC | Prompt 12 |
| 016 | parity tests | exists |
| 017, 018 | homestead scenarios | exists |
| 019, 020 | a udev event in a VM; PoC 3 with two monitors on two GPUs | PoC 3 |
| 021, 022 | pairing and node-loss tests | Prompt 12 |
| 023 | a local VM boots the image | Prompt 15 |
| 024 to 026 | simulated hwmon, NUT test mode, SMART fixtures | Prompt 14 |
| 027, 028 | records built from fixture outputs | with the registry |
| 029, 030 | a bench running while he asks; the queue listed | Prompt 07 |
| 031 | one simulation per failure row | Prompt 14 |
