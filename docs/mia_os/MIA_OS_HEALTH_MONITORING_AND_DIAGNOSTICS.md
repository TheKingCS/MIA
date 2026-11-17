# MIA OS: health monitoring and diagnostics (Prompt 09 §8; DEC-0222)

*Claude (Opus), 2026-11-17. Planning only.*

| Layer | Watched by | Response | Exists |
|---|---|---|---|
| Hardware | system health readings; hwmon, SMART, UPower on MIA OS | ease off, warn (REQ-HW-024 to 026) | partial |
| Services | service map; systemd's restart policy and journal (DEC-0195) | restart (Linux's), report | partial |
| Jobs | scheduler and homeostasis (backoff after 3 failures) | back off, notice | yes |
| Stores | load checks; a corrupt store reset and reported (`data_recovery`) | reset with a backup, tell him | yes |
| Models | registry; the bench; inspections | route around, re-bench | yes |
| Turns | the Fix-It Log (errors, slow turns, his corrections) | ranked for fixing | yes |
| The whole | the weekly self-audit and self-report | a report through the gate | yes |

**Diagnostics are read-only** unless he asks: "what's wrong with Look?" runs the checks for that capability (the
service, the model, the last failures) and says what it found. Repair beyond a restart is a proposal (Q-77 asks about
restarts on her own).

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-SLF-008 | Asked what's wrong with a capability, MIA shall run its read-only checks and report each finding with its evidence. | Should | R1 | All | Partial | T | DEC-0222 → 09 |
