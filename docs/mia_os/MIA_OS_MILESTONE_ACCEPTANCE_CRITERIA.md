# MIA OS: milestone acceptance criteria (Prompt 16)

*Claude (Opus), 2026-11-18.*

| Milestone | Passes when |
|---|---|
| M0 | each backlog package's tests pass and its requirements show Exists in the matrix |
| M1 | the 14B model writes at 65 tokens/s or more under Fedora on his GPU |
| M2 | the image boots in the VM to SDDM; the runtime reaches core ready; the suite passes inside |
| M3 | MIA's session shows her front end full screen with a Linux app beside it; Plasma and safe mode work |
| M4 | an update is applied and a bad one rolls back by itself; the helper changes one setting through polkit; the disk unlocks by the TPM |
| M5 | an image and the APK are signed and verified; an SBOM beside each |
| M6 | MIA OS on the 4 TB drive; the migration report matches; the phone re-paired and synced |
| M7 | a week as his main system; the MVP's scenarios (S-01, 03, 04, 09, 12, 13, 14, 16, 17, 18) and Prompt 12's A, C, F, G, J; nothing lost; every Must · MVP requirement passing |
| M8 | R1's Must requirements passing; the household display on the TV; the laptop syncing |

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-IMP-006 | Each milestone's criteria shall be checked and recorded with the commit and evidence that met them. | Should | MVP | All | New | R | DEC-0274 → 16 |
